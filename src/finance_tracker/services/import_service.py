"""Import orchestration service."""

from datetime import datetime
from pathlib import Path

import aiosqlite

from ..database import generate_import_hash
from ..parsers.apple import AppleCardParser
from ..parsers.base import BaseParser, ParsedTransaction
from ..parsers.chase import ChaseParser
from ..parsers.venmo import VenmoParser
from .category_service import categorize_transaction, get_uncategorized_category_id

# Registry of available parsers
PARSERS: list[BaseParser] = [
    ChaseParser(),
    VenmoParser(),
    AppleCardParser(),
]


async def detect_parser(file_path: Path) -> BaseParser | None:
    """
    Detect which parser can handle a given file.

    Args:
        file_path: Path to the file to parse

    Returns:
        Parser instance if one can handle the file, None otherwise
    """
    for parser in PARSERS:
        if parser.can_parse(file_path):
            return parser
    return None


async def get_or_create_account(
    db: aiosqlite.Connection, account_name: str, institution: str, account_type: str | None = None
) -> int:
    """
    Get existing account ID or create a new account.

    Args:
        db: Database connection
        account_name: Name of the account
        institution: Institution name
        account_type: Type of account (checking, savings, credit, etc.)

    Returns:
        Account ID
    """
    # Try to find existing account
    cursor = await db.execute(
        "SELECT id FROM accounts WHERE name = ? AND institution = ?",
        (account_name, institution),
    )
    row = await cursor.fetchone()

    if row:
        return row[0]

    # Create new account
    cursor = await db.execute(
        "INSERT INTO accounts (name, institution, account_type) VALUES (?, ?, ?)",
        (account_name, institution, account_type),
    )
    await db.commit()
    return cursor.lastrowid


async def import_transaction(
    db: aiosqlite.Connection,
    account_id: int,
    txn: ParsedTransaction,
    source: str,
) -> tuple[int | None, bool]:
    """
    Import a single transaction into the database.

    Args:
        db: Database connection
        account_id: Account ID to associate with transaction
        txn: Parsed transaction
        source: Source identifier for deduplication

    Returns:
        Tuple of (transaction_id, is_duplicate)
    """
    # Generate import hash for deduplication
    import_hash = generate_import_hash(
        str(txn.date),
        str(txn.amount),
        txn.description,
        source,
    )

    # Check if transaction already exists
    cursor = await db.execute(
        "SELECT id FROM transactions WHERE import_hash = ?",
        (import_hash,),
    )
    existing = await cursor.fetchone()

    if existing:
        return existing[0], True

    # Auto-categorize
    category_id = await categorize_transaction(db, txn.description)
    if category_id is None:
        category_id = await get_uncategorized_category_id(db)

    # Insert transaction
    cursor = await db.execute(
        """
        INSERT INTO transactions
        (account_id, date, amount, description, merchant, category_id,
         original_category, import_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            str(txn.date),
            float(txn.amount),
            txn.description,
            txn.merchant,
            category_id,
            txn.original_category,
            import_hash,
        ),
    )

    return cursor.lastrowid, False


async def import_file(
    db: aiosqlite.Connection,
    file_path: Path,
    account_id: int | None = None,
) -> dict:
    """
    Import transactions from a file.

    Args:
        db: Database connection
        file_path: Path to the file to import
        account_id: Optional account ID to use; if None, will be created

    Returns:
        Dictionary with import results
    """
    # Detect parser
    parser = await detect_parser(file_path)
    if not parser:
        raise ValueError(f"No parser found for file: {file_path}")

    # Parse file
    result = parser.parse(file_path)

    # Get or create account
    if account_id is None:
        account_id = await get_or_create_account(
            db,
            result.account_name,
            result.institution,
        )

    # Import transactions
    imported = 0
    duplicates = 0
    errors = []

    for idx, txn in enumerate(result.transactions, start=1):
        try:
            _, is_duplicate = await import_transaction(
                db, account_id, txn, result.institution.lower()
            )
            if is_duplicate:
                duplicates += 1
            else:
                imported += 1
        except Exception as e:
            errors.append(f"Transaction {idx} ({txn.date} ${txn.amount}): {str(e)}")

    await db.commit()

    # Record import
    status = "success" if not errors else "partial" if imported > 0 else "failed"
    await db.execute(
        """
        INSERT INTO imports (filename, institution, transaction_count, status)
        VALUES (?, ?, ?, ?)
        """,
        (file_path.name, result.institution, imported, status),
    )
    await db.commit()

    return {
        "filename": file_path.name,
        "institution": result.institution,
        "account_name": result.account_name,
        "total_transactions": len(result.transactions),
        "imported": imported,
        "duplicates": duplicates,
        "errors": errors + result.warnings,
        "status": status,
    }
