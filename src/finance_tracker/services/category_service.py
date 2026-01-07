"""Category and categorization services."""

import aiosqlite


async def get_category_rules(db: aiosqlite.Connection) -> list[dict]:
    """
    Get all category rules sorted by priority.

    Returns:
        List of rules with id, pattern, category_id, priority
    """
    cursor = await db.execute(
        "SELECT id, pattern, category_id, priority FROM category_rules ORDER BY priority DESC"
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": row[0],
            "pattern": row[1],
            "category_id": row[2],
            "priority": row[3],
        }
        for row in rows
    ]


async def categorize_transaction(
    db: aiosqlite.Connection, description: str
) -> int | None:
    """
    Apply category rules to a transaction description.

    Args:
        db: Database connection
        description: Transaction description to categorize

    Returns:
        Category ID if a rule matches, None otherwise
    """
    rules = await get_category_rules(db)
    description_upper = description.upper()

    for rule in rules:
        if rule["pattern"].upper() in description_upper:
            return rule["category_id"]

    return None


async def get_uncategorized_category_id(db: aiosqlite.Connection) -> int:
    """
    Get the ID of the Uncategorized category.

    Returns:
        Category ID for Uncategorized
    """
    cursor = await db.execute(
        "SELECT id FROM categories WHERE name = 'Uncategorized' LIMIT 1"
    )
    row = await cursor.fetchone()
    if not row:
        raise ValueError("Uncategorized category not found in database")
    return row[0]


async def get_categories_tree(db: aiosqlite.Connection) -> list[dict]:
    """
    Get all categories organized in a tree structure.

    Returns:
        List of parent categories with nested children
    """
    cursor = await db.execute(
        "SELECT id, name, parent_id, color FROM categories ORDER BY name"
    )
    rows = await cursor.fetchall()

    categories_dict = {}
    parents = []

    for row in rows:
        cat = {
            "id": row[0],
            "name": row[1],
            "parent_id": row[2],
            "color": row[3],
            "children": [],
        }
        categories_dict[cat["id"]] = cat

        if cat["parent_id"] is None:
            parents.append(cat)

    # Attach children to parents
    for cat in categories_dict.values():
        if cat["parent_id"] is not None:
            parent = categories_dict.get(cat["parent_id"])
            if parent:
                parent["children"].append(cat)

    return parents


async def get_all_categories_flat(db: aiosqlite.Connection) -> list[dict]:
    """
    Get all categories as a flat list.

    Returns:
        List of all categories with id, name, parent_id, color
    """
    cursor = await db.execute(
        "SELECT id, name, parent_id, color FROM categories ORDER BY name"
    )
    rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "parent_id": row[2],
            "color": row[3],
        }
        for row in rows
    ]
