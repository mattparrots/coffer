"""Transaction routes."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..database import get_db
from ..services.category_service import get_all_categories_flat

router = APIRouter(prefix="/transactions")
templates = Jinja2Templates(directory=settings.templates_dir)


@router.get("", response_class=HTMLResponse)
async def transactions_list(
    request: Request,
    search: str | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """Transaction list page with filters."""
    async with get_db() as db:
        # Build query
        query = """
            SELECT
                t.id,
                t.date,
                t.amount,
                t.description,
                t.merchant,
                t.notes,
                a.name as account_name,
                c.name as category_name,
                c.color as category_color,
                c.id as category_id
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (t.description LIKE ? OR t.merchant LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)

        if account_id:
            query += " AND t.account_id = ?"
            params.append(account_id)

        if date_from:
            query += " AND t.date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND t.date <= ?"
            params.append(date_to)

        query += " ORDER BY t.date DESC, t.created_at DESC LIMIT 100"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        transactions = [
            {
                "id": row[0],
                "date": row[1],
                "amount": Decimal(str(row[2])),
                "description": row[3],
                "merchant": row[4],
                "notes": row[5],
                "account_name": row[6],
                "category_name": row[7],
                "category_color": row[8],
                "category_id": row[9],
            }
            for row in rows
        ]

        # Get categories for filter dropdown
        categories = await get_all_categories_flat(db)

        # Get accounts
        cursor = await db.execute("SELECT id, name FROM accounts ORDER BY name")
        accounts = [{"id": row[0], "name": row[1]} for row in await cursor.fetchall()]

    return templates.TemplateResponse(
        "transactions/list.html",
        {
            "request": request,
            "active_page": "transactions",
            "transactions": transactions,
            "categories": categories,
            "accounts": accounts,
            "filters": {
                "search": search or "",
                "category_id": category_id,
                "account_id": account_id,
                "date_from": date_from or "",
                "date_to": date_to or "",
            },
        },
    )


@router.put("/{transaction_id}/category", response_class=HTMLResponse)
async def update_transaction_category(
    request: Request,
    transaction_id: int,
    category_id: int = Form(),
):
    """Update transaction category (htmx endpoint)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE transactions SET category_id = ? WHERE id = ?",
            (category_id, transaction_id),
        )
        await db.commit()

        # Get updated transaction
        cursor = await db.execute(
            """
            SELECT c.name, c.color
            FROM categories c
            WHERE c.id = ?
            """,
            (category_id,),
        )
        row = await cursor.fetchone()

    category_name = row[0] if row else "Unknown"
    category_color = row[1] if row else "#d1d5db"

    return f"""
    <span class="category-badge" style="background-color: {category_color}33; color: {category_color}">
        {category_name}
    </span>
    """
