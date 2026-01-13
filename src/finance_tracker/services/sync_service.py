"""Service for synchronizing Plaid transactions with local database."""

import logging
from datetime import datetime
from decimal import Decimal

import aiosqlite

from .category_service import categorize_transaction, get_uncategorized_category_id
from .plaid_service import get_plaid_service

logger = logging.getLogger(__name__)


class SyncResult:
    """Result of a sync operation."""

    def __init__(self):
        self.added_count = 0
        self.updated_count = 0
        self.removed_count = 0
        self.errors: list[str] = []
        self.skipped_pending = 0

    @property
    def total_processed(self) -> int:
        """Total number of transactions processed."""
        return self.added_count + self.updated_count + self.removed_count

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "added": self.added_count,
            "updated": self.updated_count,
            "removed": self.removed_count,
            "skipped_pending": self.skipped_pending,
            "total": self.total_processed,
            "errors": self.errors,
        }


async def sync_plaid_item(db: aiosqlite.Connection, plaid_item_id: int) -> SyncResult:
    """
    Sync transactions for a single Plaid Item.

    Args:
        db: Database connection
        plaid_item_id: Database ID of the Plaid Item

    Returns:
        SyncResult with counts and any errors
    """
    result = SyncResult()
    plaid_service = get_plaid_service()

    try:
        # Get the Plaid Item from database
        cursor = await db.execute(
            "SELECT id, item_id, access_token, cursor, institution_name FROM plaid_items WHERE id = ?",
            (plaid_item_id,),
        )
        row = await cursor.fetchone()

        if not row:
            result.errors.append(f"Plaid Item {plaid_item_id} not found")
            return result

        db_id, item_id, encrypted_access_token, sync_cursor, institution_name = row

        # Decrypt access token
        from ..encryption import decrypt_token
        access_token = decrypt_token(encrypted_access_token)

        # Sync transactions from Plaid
        logger.info(f"Syncing transactions for item {item_id}...")
        sync_data = await plaid_service.sync_transactions(access_token, sync_cursor)

        # Process added transactions
        for txn in sync_data["added"]:
            try:
                await _process_transaction(db, txn, plaid_item_id, "add")
                result.added_count += 1
            except Exception as e:
                logger.error(f"Error adding transaction {txn['transaction_id']}: {e}")
                result.errors.append(f"Failed to add transaction: {str(e)}")

        # Process modified transactions
        for txn in sync_data["modified"]:
            try:
                await _process_transaction(db, txn, plaid_item_id, "update")
                result.updated_count += 1
            except Exception as e:
                logger.error(f"Error updating transaction {txn['transaction_id']}: {e}")
                result.errors.append(f"Failed to update transaction: {str(e)}")

        # Process removed transactions
        for txn_id in sync_data["removed"]:
            try:
                await _remove_transaction(db, txn_id)
                result.removed_count += 1
            except Exception as e:
                logger.error(f"Error removing transaction {txn_id}: {e}")
                result.errors.append(f"Failed to remove transaction: {str(e)}")

        # Update cursor and last sync time
        await plaid_service.update_sync_cursor(db, item_id, sync_data["cursor"])

        # Update item status to active
        await plaid_service.update_item_status(db, item_id, "active")

        logger.info(
            f"Sync complete for {item_id}: "
            f"+{result.added_count} ~{result.updated_count} -{result.removed_count}"
        )

    except Exception as e:
        logger.error(f"Error syncing Plaid Item {plaid_item_id}: {e}")
        result.errors.append(str(e))

        # Try to update item status to error
        try:
            cursor = await db.execute(
                "SELECT item_id FROM plaid_items WHERE id = ?",
                (plaid_item_id,),
            )
            row = await cursor.fetchone()
            if row:
                await plaid_service.update_item_status(db, row[0], "error", str(e))
        except:
            pass

    return result


async def _process_transaction(
    db: aiosqlite.Connection,
    txn: dict,
    plaid_item_id: int,
    operation: str,
) -> None:
    """
    Process a single transaction (add or update).

    Args:
        db: Database connection
        txn: Transaction data from Plaid
        plaid_item_id: Database ID of the Plaid Item
        operation: 'add' or 'update'
    """
    # Skip pending transactions (you can change this behavior)
    if txn["pending"]:
        logger.debug(f"Skipping pending transaction {txn['transaction_id']}")
        return

    # Find the corresponding account_id in our database
    cursor = await db.execute(
        """
        SELECT pa.account_id
        FROM plaid_accounts pa
        WHERE pa.plaid_account_id = ? AND pa.plaid_item_id = ?
        """,
        (txn["account_id"], plaid_item_id),
    )
    row = await cursor.fetchone()

    if not row:
        # Account not found - this shouldn't happen if accounts were properly created
        logger.warning(f"Account {txn['account_id']} not found for transaction {txn['transaction_id']}")
        return

    account_id = row[0]

    # Convert Plaid amount (positive = money out) to our format (negative = expense)
    # Plaid: positive = debit/expense, negative = credit/income
    # Our DB: negative = expense, positive = income
    amount = Decimal(str(-txn["amount"]))

    # Use merchant name if available, otherwise use transaction name
    merchant = txn.get("merchant_name") or ""
    description = txn["name"]

    # Auto-categorize based on description and merchant
    category_id = await categorize_transaction(db, f"{description} {merchant}")
    if not category_id:
        category_id = await get_uncategorized_category_id(db)

    # Store the Plaid category as original_category
    original_category = txn.get("category_detailed") or txn.get("category")

    if operation == "add":
        # Insert new transaction
        await db.execute(
            """
            INSERT INTO transactions (
                account_id, date, amount, description, merchant,
                category_id, original_category, plaid_transaction_id, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                txn["date"],
                amount,
                description,
                merchant,
                category_id,
                original_category,
                txn["transaction_id"],
                txn["pending"],
            ),
        )
    elif operation == "update":
        # Update existing transaction
        await db.execute(
            """
            UPDATE transactions
            SET date = ?, amount = ?, description = ?, merchant = ?,
                original_category = ?, is_pending = ?
            WHERE plaid_transaction_id = ?
            """,
            (
                txn["date"],
                amount,
                description,
                merchant,
                original_category,
                txn["pending"],
                txn["transaction_id"],
            ),
        )

    await db.commit()


async def _remove_transaction(db: aiosqlite.Connection, transaction_id: str) -> None:
    """
    Remove a transaction that was deleted in Plaid.

    Args:
        db: Database connection
        transaction_id: Plaid transaction ID to remove
    """
    # Soft delete: we'll actually hard delete for now, but you could add a 'deleted' flag
    await db.execute(
        "DELETE FROM transactions WHERE plaid_transaction_id = ?",
        (transaction_id,),
    )
    await db.commit()


async def sync_all_active_items(db: aiosqlite.Connection) -> dict[str, Any]:
    """
    Sync all active Plaid Items.

    Args:
        db: Database connection

    Returns:
        Summary of sync results
    """
    cursor = await db.execute(
        "SELECT id, institution_name FROM plaid_items WHERE status = 'active'"
    )
    items = await cursor.fetchall()

    results = []
    total_added = 0
    total_updated = 0
    total_removed = 0
    total_errors = []

    for item_id, institution_name in items:
        result = await sync_plaid_item(db, item_id)
        results.append({
            "item_id": item_id,
            "institution": institution_name,
            "result": result.to_dict(),
        })

        total_added += result.added_count
        total_updated += result.updated_count
        total_removed += result.removed_count
        total_errors.extend(result.errors)

    return {
        "items_synced": len(items),
        "total_added": total_added,
        "total_updated": total_updated,
        "total_removed": total_removed,
        "errors": total_errors,
        "details": results,
    }


async def create_accounts_for_plaid_item(
    db: aiosqlite.Connection,
    plaid_item_id: int,
    item_id: str,
    access_token: str,
) -> list[int]:
    """
    Create account records for all accounts in a Plaid Item.

    Args:
        db: Database connection
        plaid_item_id: Database ID of the Plaid Item
        item_id: Plaid Item ID
        access_token: Plaid access token (decrypted)

    Returns:
        List of created account IDs
    """
    plaid_service = get_plaid_service()

    # Get institution info
    cursor = await db.execute(
        "SELECT institution_id, institution_name FROM plaid_items WHERE id = ?",
        (plaid_item_id,),
    )
    row = await cursor.fetchone()
    institution_id, institution_name = row if row else (None, "Unknown")

    # Fetch accounts from Plaid
    plaid_accounts = await plaid_service.get_accounts(access_token)

    created_account_ids = []

    for plaid_account in plaid_accounts:
        # Create account in accounts table
        account_name = plaid_account["official_name"] or plaid_account["name"]
        account_type = plaid_account["subtype"] or plaid_account["type"]

        cursor = await db.execute(
            """
            INSERT INTO accounts (name, institution, account_type, source, plaid_item_id)
            VALUES (?, ?, ?, 'plaid', ?)
            """,
            (account_name, institution_name, account_type, plaid_item_id),
        )
        account_id = cursor.lastrowid
        created_account_ids.append(account_id)

        # Create record in plaid_accounts table
        await db.execute(
            """
            INSERT INTO plaid_accounts (
                plaid_item_id, account_id, plaid_account_id, account_name,
                account_type, account_subtype, available_balance, current_balance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plaid_item_id,
                account_id,
                plaid_account["account_id"],
                account_name,
                plaid_account["type"],
                plaid_account["subtype"],
                plaid_account["balances"]["available"],
                plaid_account["balances"]["current"],
            ),
        )

    await db.commit()
    logger.info(f"Created {len(created_account_ids)} accounts for Plaid Item {item_id}")

    return created_account_ids


from typing import Any
