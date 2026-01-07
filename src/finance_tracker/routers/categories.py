"""Category management routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..database import get_db
from ..services.category_service import get_all_categories_flat, get_categories_tree

router = APIRouter(prefix="/categories")
templates = Jinja2Templates(directory=settings.templates_dir)


@router.get("", response_class=HTMLResponse)
async def categories_page(request: Request):
    """Category and rules management page."""
    async with get_db() as db:
        # Get categories tree
        categories = await get_categories_tree(db)

        # Get all categories flat for rules dropdown
        all_categories = await get_all_categories_flat(db)

        # Get category rules
        cursor = await db.execute(
            """
            SELECT r.id, r.pattern, r.priority, c.name as category_name
            FROM category_rules r
            JOIN categories c ON r.category_id = c.id
            ORDER BY r.priority DESC, r.pattern
            """
        )
        rows = await cursor.fetchall()

        rules = [
            {
                "id": row[0],
                "pattern": row[1],
                "priority": row[2],
                "category_name": row[3],
            }
            for row in rows
        ]

    return templates.TemplateResponse(
        "categories/list.html",
        {
            "request": request,
            "active_page": "categories",
            "categories": categories,
            "all_categories": all_categories,
            "rules": rules,
        },
    )


@router.post("/rules", response_class=HTMLResponse)
async def create_rule(
    request: Request,
    pattern: str = Form(),
    category_id: int = Form(),
    priority: int = Form(default=10),
):
    """Create a new category rule."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO category_rules (pattern, category_id, priority) VALUES (?, ?, ?)",
            (pattern.upper(), category_id, priority),
        )
        await db.commit()

    return """
    <div style="padding: 1rem; background-color: #dcfce7; color: #166534; border-radius: 4px; margin-bottom: 1rem;">
        Rule created! <a href="/categories">Refresh to see it.</a>
    </div>
    """


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int):
    """Delete a category rule."""
    async with get_db() as db:
        await db.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))
        await db.commit()

    return {"success": True}
