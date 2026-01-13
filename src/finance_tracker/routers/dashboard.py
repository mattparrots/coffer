"""Dashboard routes."""

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..database import get_db
from ..services.analytics_service import (
    get_monthly_cash_flow,
    get_monthly_summary,
    get_recent_transactions,
    get_spending_by_category,
)

router = APIRouter()
templates = Jinja2Templates(directory=settings.templates_dir)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    async with get_db() as db:
        # Get summary stats
        summary = await get_monthly_summary(db, current_year, current_month)

        # Get spending breakdown
        spending = await get_spending_by_category(db, current_year, current_month)

        # Get cash flow
        cash_flow = await get_monthly_cash_flow(db, months=6)

        # Get recent transactions
        recent = await get_recent_transactions(db, limit=10)

        # Get Plaid connections status
        cursor = await db.execute(
            """
            SELECT
                pi.id,
                pi.institution_name,
                pi.status,
                pi.last_sync_at,
                COUNT(pa.id) as account_count
            FROM plaid_items pi
            LEFT JOIN plaid_accounts pa ON pa.plaid_item_id = pi.id
            WHERE pi.status != 'disconnected'
            GROUP BY pi.id
            ORDER BY pi.created_at DESC
            LIMIT 5
            """
        )
        plaid_rows = await cursor.fetchall()
        plaid_connections = [
            {
                "id": row[0],
                "institution_name": row[1] or "Unknown Bank",
                "status": row[2],
                "last_sync_at": row[3],
                "account_count": row[4],
            }
            for row in plaid_rows
        ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "summary": summary,
            "spending": spending,
            "cash_flow": cash_flow,
            "recent_transactions": recent,
            "current_month": now.strftime("%B %Y"),
            "plaid_connections": plaid_connections,
        },
    )
