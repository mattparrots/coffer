"""Analytics and aggregation services."""

from datetime import date, datetime
from decimal import Decimal

import aiosqlite


async def get_monthly_summary(db: aiosqlite.Connection, year: int, month: int) -> dict:
    """
    Get income/expense summary for a specific month.

    Args:
        db: Database connection
        year: Year
        month: Month (1-12)

    Returns:
        Dictionary with income, expenses, net, and change percentages
    """
    # Get current month stats
    cursor = await db.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as income,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses
        FROM transactions
        WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
        """,
        (str(year), f"{month:02d}"),
    )
    row = await cursor.fetchone()
    income = Decimal(str(row[0])) if row else Decimal("0")
    expenses = Decimal(str(row[1])) if row else Decimal("0")
    net = income - expenses

    # Get previous month stats for comparison
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    cursor = await db.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as income,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses
        FROM transactions
        WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
        """,
        (str(prev_year), f"{prev_month:02d}"),
    )
    prev_row = await cursor.fetchone()
    prev_income = Decimal(str(prev_row[0])) if prev_row else Decimal("0")
    prev_expenses = Decimal(str(prev_row[1])) if prev_row else Decimal("0")

    # Calculate percentage changes
    income_change = None
    if prev_income > 0:
        income_change = ((income - prev_income) / prev_income * 100).quantize(Decimal("0.01"))

    expenses_change = None
    if prev_expenses > 0:
        expenses_change = ((expenses - prev_expenses) / prev_expenses * 100).quantize(Decimal("0.01"))

    return {
        "income": float(income),
        "expenses": float(expenses),
        "net": float(net),
        "income_change_pct": float(income_change) if income_change is not None else None,
        "expenses_change_pct": float(expenses_change) if expenses_change is not None else None,
    }


async def get_spending_by_category(
    db: aiosqlite.Connection, year: int, month: int, top_n: int = 8
) -> list[dict]:
    """
    Get spending breakdown by category for a month.

    Args:
        db: Database connection
        year: Year
        month: Month (1-12)
        top_n: Number of top categories to return separately

    Returns:
        List of categories with spending amounts and percentages
    """
    cursor = await db.execute(
        """
        SELECT
            COALESCE(parent.id, c.id) as category_id,
            COALESCE(parent.name, c.name) as category_name,
            COALESCE(parent.color, c.color) as color,
            SUM(ABS(t.amount)) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories parent ON c.parent_id = parent.id
        WHERE t.amount < 0
          AND strftime('%Y', t.date) = ?
          AND strftime('%m', t.date) = ?
        GROUP BY COALESCE(parent.id, c.id), COALESCE(parent.name, c.name), COALESCE(parent.color, c.color)
        ORDER BY total DESC
        """,
        (str(year), f"{month:02d}"),
    )
    rows = await cursor.fetchall()

    if not rows:
        return []

    # Calculate total for percentages
    total_spending = sum(Decimal(str(row[3])) for row in rows)

    # Get top N categories
    results = []
    other_total = Decimal("0")

    for i, row in enumerate(rows):
        amount = Decimal(str(row[3]))
        percentage = (amount / total_spending * 100).quantize(Decimal("0.01"))

        if i < top_n:
            results.append({
                "category_id": row[0],
                "category_name": row[1],
                "color": row[2],
                "amount": float(amount),
                "percentage": float(percentage),
            })
        else:
            other_total += amount

    # Add "Other" category if there are more than top_n
    if other_total > 0:
        other_pct = (other_total / total_spending * 100).quantize(Decimal("0.01"))
        results.append({
            "category_id": None,
            "category_name": "Other",
            "color": "#9ca3af",
            "amount": float(other_total),
            "percentage": float(other_pct),
        })

    return results


async def get_monthly_cash_flow(db: aiosqlite.Connection, months: int = 6) -> list[dict]:
    """
    Get monthly income/expense totals for the last N months.

    Args:
        db: Database connection
        months: Number of months to retrieve

    Returns:
        List of monthly flow data
    """
    cursor = await db.execute(
        f"""
        SELECT
            strftime('%Y-%m', date) as month,
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as income,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses
        FROM transactions
        WHERE date >= date('now', '-{months} months')
        GROUP BY month
        ORDER BY month
        """
    )
    rows = await cursor.fetchall()

    results = []
    for row in rows:
        income = Decimal(str(row[1]))
        expenses = Decimal(str(row[2]))
        results.append({
            "month": row[0],
            "income": float(income),
            "expenses": float(expenses),
            "net": float(income - expenses),
        })

    return results


async def get_recent_transactions(
    db: aiosqlite.Connection, limit: int = 10
) -> list[dict]:
    """
    Get the most recent transactions with account and category details.

    Args:
        db: Database connection
        limit: Number of transactions to return

    Returns:
        List of transaction dictionaries
    """
    cursor = await db.execute(
        """
        SELECT
            t.id,
            t.date,
            t.amount,
            t.description,
            t.merchant,
            a.name as account_name,
            c.name as category_name,
            c.color as category_color
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.date DESC, t.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "date": row[1],
            "amount": float(row[2]),
            "description": row[3],
            "merchant": row[4],
            "account_name": row[5],
            "category_name": row[6],
            "category_color": row[7],
        }
        for row in rows
    ]
