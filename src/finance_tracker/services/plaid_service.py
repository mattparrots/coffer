"""Service for interacting with Plaid API."""

import logging
from datetime import datetime
from typing import Any

import aiosqlite
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.api_client import ApiClient
from plaid.configuration import Configuration

from ..config import settings
from ..encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)


class PlaidService:
    """Service for interacting with Plaid API."""

    def __init__(self):
        """Initialize Plaid API client."""
        # Configure Plaid API client
        configuration = Configuration(
            host=self._get_plaid_host(),
            api_key={
                "clientId": settings.plaid_client_id,
                "secret": settings.plaid_secret,
            },
        )
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    def _get_plaid_host(self) -> str:
        """Get the appropriate Plaid API host based on environment."""
        hosts = {
            "sandbox": "https://sandbox.plaid.com",
            "development": "https://development.plaid.com",
            "production": "https://production.plaid.com",
        }
        return hosts.get(settings.plaid_env, hosts["sandbox"])

    async def create_link_token(self, user_id: str = "user") -> dict[str, Any]:
        """
        Create a Link token for initializing Plaid Link.

        Args:
            user_id: Unique identifier for the user (can be any string for single-user app)

        Returns:
            Dictionary containing link_token and expiration
        """
        try:
            request = LinkTokenCreateRequest(
                products=[Products(p) for p in settings.plaid_products],
                client_name=settings.app_name,
                country_codes=[CountryCode(c) for c in settings.plaid_country_codes],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                redirect_uri=settings.plaid_redirect_uri if settings.plaid_redirect_uri else None,
            )
            response = self.client.link_token_create(request)
            return {
                "link_token": response["link_token"],
                "expiration": response["expiration"],
            }
        except Exception as e:
            logger.error(f"Error creating link token: {e}")
            raise

    async def exchange_public_token(self, public_token: str) -> dict[str, str]:
        """
        Exchange a public token for an access token.

        Args:
            public_token: Public token from Plaid Link

        Returns:
            Dictionary containing access_token and item_id
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            return {
                "access_token": response["access_token"],
                "item_id": response["item_id"],
            }
        except Exception as e:
            logger.error(f"Error exchanging public token: {e}")
            raise

    async def get_accounts(self, access_token: str) -> list[dict[str, Any]]:
        """
        Get accounts associated with an access token.

        Args:
            access_token: Plaid access token (decrypted)

        Returns:
            List of account dictionaries
        """
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)

            accounts = []
            for account in response["accounts"]:
                accounts.append({
                    "account_id": account["account_id"],
                    "name": account["name"],
                    "official_name": account.get("official_name"),
                    "type": account["type"],
                    "subtype": account["subtype"],
                    "balances": {
                        "available": account["balances"].get("available"),
                        "current": account["balances"]["current"],
                    },
                })

            return accounts
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            raise

    async def get_institution_info(self, institution_id: str) -> dict[str, str]:
        """
        Get institution information by ID.

        Args:
            institution_id: Plaid institution ID

        Returns:
            Dictionary with institution name and id
        """
        try:
            request = InstitutionsGetByIdRequest(
                institution_id=institution_id,
                country_codes=[CountryCode(c) for c in settings.plaid_country_codes],
            )
            response = self.client.institutions_get_by_id(request)
            return {
                "institution_id": response["institution"]["institution_id"],
                "name": response["institution"]["name"],
            }
        except Exception as e:
            logger.error(f"Error fetching institution info: {e}")
            return {"institution_id": institution_id, "name": "Unknown Institution"}

    async def sync_transactions(
        self, access_token: str, cursor: str | None = None
    ) -> dict[str, Any]:
        """
        Sync transactions using Plaid Transactions Sync API.

        Args:
            access_token: Plaid access token (decrypted)
            cursor: Cursor for incremental sync (None for initial sync)

        Returns:
            Dictionary containing added, modified, removed transactions and next cursor
        """
        try:
            added = []
            modified = []
            removed = []
            has_more = True

            while has_more:
                request = TransactionsSyncRequest(
                    access_token=access_token,
                    cursor=cursor,
                )
                response = self.client.transactions_sync(request)

                # Add new transactions
                added.extend([self._format_transaction(txn) for txn in response["added"]])

                # Modified transactions
                modified.extend([self._format_transaction(txn) for txn in response["modified"]])

                # Removed transaction IDs
                removed.extend([txn["transaction_id"] for txn in response["removed"]])

                has_more = response["has_more"]
                cursor = response["next_cursor"]

            return {
                "added": added,
                "modified": modified,
                "removed": removed,
                "cursor": cursor,
            }
        except Exception as e:
            logger.error(f"Error syncing transactions: {e}")
            raise

    def _format_transaction(self, txn: dict[str, Any]) -> dict[str, Any]:
        """
        Format a Plaid transaction into a standardized format.

        Args:
            txn: Raw Plaid transaction

        Returns:
            Formatted transaction dictionary
        """
        return {
            "transaction_id": txn["transaction_id"],
            "account_id": txn["account_id"],
            "date": txn["date"],
            "amount": txn["amount"],  # Positive = money out, Negative = money in
            "name": txn["name"],
            "merchant_name": txn.get("merchant_name"),
            "pending": txn["pending"],
            "category": txn.get("personal_finance_category", {}).get("primary") if txn.get("personal_finance_category") else None,
            "category_detailed": txn.get("personal_finance_category", {}).get("detailed") if txn.get("personal_finance_category") else None,
        }

    async def remove_item(self, access_token: str) -> bool:
        """
        Remove a Plaid Item (disconnect bank connection).

        Args:
            access_token: Plaid access token (decrypted)

        Returns:
            True if successful
        """
        try:
            request = ItemRemoveRequest(access_token=access_token)
            self.client.item_remove(request)
            return True
        except Exception as e:
            logger.error(f"Error removing item: {e}")
            raise

    async def store_item(
        self,
        db: aiosqlite.Connection,
        item_id: str,
        access_token: str,
        institution_id: str,
        institution_name: str,
    ) -> int:
        """
        Store a Plaid Item in the database.

        Args:
            db: Database connection
            item_id: Plaid Item ID
            access_token: Plaid access token (will be encrypted)
            institution_id: Plaid institution ID
            institution_name: Institution name

        Returns:
            Database row ID of stored item
        """
        encrypted_token = encrypt_token(access_token)

        cursor = await db.execute(
            """
            INSERT INTO plaid_items (item_id, access_token, institution_id, institution_name, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (item_id, encrypted_token, institution_id, institution_name),
        )
        await db.commit()
        return cursor.lastrowid

    async def get_item_by_id(self, db: aiosqlite.Connection, item_id: str) -> dict[str, Any] | None:
        """
        Get a Plaid Item from the database.

        Args:
            db: Database connection
            item_id: Plaid Item ID

        Returns:
            Dictionary with item data or None if not found
        """
        cursor = await db.execute(
            "SELECT * FROM plaid_items WHERE item_id = ?",
            (item_id,),
        )
        row = await cursor.fetchone()

        if row:
            return {
                "id": row["id"],
                "item_id": row["item_id"],
                "access_token": decrypt_token(row["access_token"]),
                "institution_id": row["institution_id"],
                "institution_name": row["institution_name"],
                "cursor": row["cursor"],
                "last_sync_at": row["last_sync_at"],
                "status": row["status"],
                "error_code": row["error_code"],
                "created_at": row["created_at"],
            }
        return None

    async def update_sync_cursor(
        self, db: aiosqlite.Connection, item_id: str, cursor: str
    ) -> None:
        """
        Update the sync cursor for a Plaid Item.

        Args:
            db: Database connection
            item_id: Plaid Item ID
            cursor: New cursor value
        """
        await db.execute(
            """
            UPDATE plaid_items
            SET cursor = ?, last_sync_at = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (cursor, datetime.now(), datetime.now(), item_id),
        )
        await db.commit()

    async def update_item_status(
        self, db: aiosqlite.Connection, item_id: str, status: str, error_code: str | None = None
    ) -> None:
        """
        Update the status of a Plaid Item.

        Args:
            db: Database connection
            item_id: Plaid Item ID
            status: New status (active, error, disconnected)
            error_code: Optional error code
        """
        await db.execute(
            """
            UPDATE plaid_items
            SET status = ?, error_code = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (status, error_code, datetime.now(), item_id),
        )
        await db.commit()


# Singleton instance
_plaid_service: PlaidService | None = None


def get_plaid_service() -> PlaidService:
    """Get the singleton Plaid service instance."""
    global _plaid_service
    if _plaid_service is None:
        _plaid_service = PlaidService()
    return _plaid_service
