"""Routes for Plaid integration."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..database import get_db
from ..services.plaid_service import get_plaid_service
from ..services.sync_service import (
    create_accounts_for_plaid_item,
    sync_all_active_items,
    sync_plaid_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaid", tags=["plaid"])
templates = Jinja2Templates(directory=settings.templates_dir)


@router.post("/link/token")
async def create_link_token() -> JSONResponse:
    """
    Create a Plaid Link token for initializing the Link flow.

    Returns:
        JSON with link_token and expiration
    """
    try:
        plaid_service = get_plaid_service()
        token_data = await plaid_service.create_link_token()
        return JSONResponse(content=token_data)
    except Exception as e:
        logger.error(f"Error creating link token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link/exchange")
async def exchange_public_token(request: Request) -> JSONResponse:
    """
    Exchange a public token for an access token after Link success.

    Expected JSON body:
        {
            "public_token": "public-sandbox-xxx..."
        }

    Returns:
        JSON with success status and item_id
    """
    try:
        data = await request.json()
        public_token = data.get("public_token")

        if not public_token:
            raise HTTPException(status_code=400, detail="public_token is required")

        plaid_service = get_plaid_service()

        # Exchange token
        token_data = await plaid_service.exchange_public_token(public_token)
        access_token = token_data["access_token"]
        item_id = token_data["item_id"]

        # Get accounts
        accounts = await plaid_service.get_accounts(access_token)

        # Get institution info (from first account if available)
        institution_id = None
        institution_name = "Unknown Bank"

        if accounts:
            # The institution_id is in the Item, not accounts - we'll fetch it
            async with get_db() as db:
                # Store the item first
                cursor = await db.execute(
                    "SELECT id FROM plaid_items WHERE item_id = ?",
                    (item_id,),
                )
                existing = await cursor.fetchone()

                if existing:
                    plaid_item_id = existing[0]
                else:
                    # Try to get institution info from Plaid
                    # For sandbox, we may not have institution_id readily available
                    # We'll use a placeholder and update later if needed
                    plaid_item_id = await plaid_service.store_item(
                        db, item_id, access_token, institution_id or "", institution_name
                    )

                # Create accounts for this item
                await create_accounts_for_plaid_item(db, plaid_item_id, item_id, access_token)

                # Initial sync of transactions
                sync_result = await sync_plaid_item(db, plaid_item_id)

        return JSONResponse(
            content={
                "success": True,
                "item_id": item_id,
                "accounts_created": len(accounts),
                "transactions_synced": sync_result.added_count if 'sync_result' in locals() else 0,
            }
        )

    except Exception as e:
        logger.error(f"Error exchanging public token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections", response_class=HTMLResponse)
async def connections_page(request: Request) -> HTMLResponse:
    """
    Display page for managing Plaid connections.

    Shows:
        - List of connected banks
        - Connection status
        - Last sync time
        - Connect new bank button
    """
    try:
        async with get_db() as db:
            # Get all Plaid items with their accounts
            cursor = await db.execute(
                """
                SELECT
                    pi.id,
                    pi.item_id,
                    pi.institution_name,
                    pi.status,
                    pi.last_sync_at,
                    pi.error_code,
                    COUNT(pa.id) as account_count
                FROM plaid_items pi
                LEFT JOIN plaid_accounts pa ON pa.plaid_item_id = pi.id
                GROUP BY pi.id
                ORDER BY pi.created_at DESC
                """
            )
            items = await cursor.fetchall()

            connections = [
                {
                    "id": row[0],
                    "item_id": row[1],
                    "institution_name": row[2] or "Unknown Bank",
                    "status": row[3],
                    "last_sync_at": row[4],
                    "error_code": row[5],
                    "account_count": row[6],
                }
                for row in items
            ]

        return templates.TemplateResponse(
            "plaid/connections.html",
            {
                "request": request,
                "connections": connections,
            },
        )

    except Exception as e:
        logger.error(f"Error loading connections page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def manual_sync() -> JSONResponse:
    """
    Manually trigger sync for all active Plaid items.

    Returns:
        JSON with sync results
    """
    try:
        async with get_db() as db:
            results = await sync_all_active_items(db)

        return JSONResponse(content={"success": True, "results": results})

    except Exception as e:
        logger.error(f"Error during manual sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/{item_id}")
async def sync_single_item(item_id: int) -> JSONResponse:
    """
    Manually trigger sync for a specific Plaid item.

    Args:
        item_id: Database ID of the Plaid item

    Returns:
        JSON with sync results
    """
    try:
        async with get_db() as db:
            result = await sync_plaid_item(db, item_id)

        return JSONResponse(
            content={
                "success": True,
                "added": result.added_count,
                "updated": result.updated_count,
                "removed": result.removed_count,
                "errors": result.errors,
            }
        )

    except Exception as e:
        logger.error(f"Error syncing item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}")
async def disconnect_item(item_id: int) -> JSONResponse:
    """
    Disconnect a Plaid item (remove bank connection).

    Args:
        item_id: Database ID of the Plaid item

    Returns:
        JSON with success status
    """
    try:
        plaid_service = get_plaid_service()

        async with get_db() as db:
            # Get the item
            cursor = await db.execute(
                "SELECT item_id, access_token FROM plaid_items WHERE id = ?",
                (item_id,),
            )
            row = await cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Plaid item not found")

            plaid_item_id, encrypted_access_token = row

            # Decrypt access token
            from ..encryption import decrypt_token
            access_token = decrypt_token(encrypted_access_token)

            # Remove from Plaid
            await plaid_service.remove_item(access_token)

            # Update status in database (keep for historical records)
            await db.execute(
                "UPDATE plaid_items SET status = 'disconnected' WHERE id = ?",
                (item_id,),
            )
            await db.commit()

        return JSONResponse(content={"success": True})

    except Exception as e:
        logger.error(f"Error disconnecting item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def plaid_webhook(request: Request) -> JSONResponse:
    """
    Handle webhooks from Plaid.

    Plaid sends webhooks for various events:
    - ITEM_LOGIN_REQUIRED: User needs to re-authenticate
    - TRANSACTIONS: New transactions available
    - ERROR: Item error occurred

    Returns:
        JSON acknowledging receipt
    """
    try:
        webhook_data = await request.json()
        webhook_type = webhook_data.get("webhook_type")
        webhook_code = webhook_data.get("webhook_code")
        item_id = webhook_data.get("item_id")

        logger.info(f"Received webhook: {webhook_type}.{webhook_code} for item {item_id}")

        # Handle different webhook types
        if webhook_type == "TRANSACTIONS":
            if webhook_code in ["SYNC_UPDATES_AVAILABLE", "DEFAULT_UPDATE"]:
                # New transactions available - trigger sync
                async with get_db() as db:
                    cursor = await db.execute(
                        "SELECT id FROM plaid_items WHERE item_id = ?",
                        (item_id,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        # Trigger async sync (in production, you'd queue this as a background job)
                        await sync_plaid_item(db, row[0])

        elif webhook_type == "ITEM":
            if webhook_code == "ERROR":
                # Item error occurred
                error = webhook_data.get("error", {})
                error_code = error.get("error_code")

                async with get_db() as db:
                    plaid_service = get_plaid_service()
                    await plaid_service.update_item_status(db, item_id, "error", error_code)

        return JSONResponse(content={"success": True})

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Return 200 anyway to prevent Plaid from retrying
        return JSONResponse(content={"success": False, "error": str(e)})


@router.get("/accounts")
async def list_plaid_accounts() -> JSONResponse:
    """
    List all Plaid accounts with their details.

    Returns:
        JSON with list of accounts
    """
    try:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT
                    pa.id,
                    pa.plaid_account_id,
                    pa.account_name,
                    pa.account_type,
                    pa.account_subtype,
                    pa.current_balance,
                    pa.available_balance,
                    pa.is_active,
                    a.name as local_account_name,
                    pi.institution_name
                FROM plaid_accounts pa
                JOIN accounts a ON a.id = pa.account_id
                JOIN plaid_items pi ON pi.id = pa.plaid_item_id
                ORDER BY pi.institution_name, pa.account_name
                """
            )
            rows = await cursor.fetchall()

            accounts = [
                {
                    "id": row[0],
                    "plaid_account_id": row[1],
                    "account_name": row[2],
                    "account_type": row[3],
                    "account_subtype": row[4],
                    "current_balance": float(row[5]) if row[5] else None,
                    "available_balance": float(row[6]) if row[6] else None,
                    "is_active": bool(row[7]),
                    "local_account_name": row[8],
                    "institution_name": row[9],
                }
                for row in rows
            ]

        return JSONResponse(content={"accounts": accounts})

    except Exception as e:
        logger.error(f"Error listing Plaid accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/accounts/{account_id}/toggle")
async def toggle_account_sync(account_id: int) -> JSONResponse:
    """
    Enable or disable syncing for a specific Plaid account.

    Args:
        account_id: Database ID of the plaid_accounts record

    Returns:
        JSON with new status
    """
    try:
        async with get_db() as db:
            # Toggle is_active
            await db.execute(
                """
                UPDATE plaid_accounts
                SET is_active = NOT is_active
                WHERE id = ?
                """,
                (account_id,),
            )
            await db.commit()

            # Get new status
            cursor = await db.execute(
                "SELECT is_active FROM plaid_accounts WHERE id = ?",
                (account_id,),
            )
            row = await cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Account not found")

        return JSONResponse(content={"success": True, "is_active": bool(row[0])})

    except Exception as e:
        logger.error(f"Error toggling account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
