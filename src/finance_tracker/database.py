"""Database connection, schema initialization, and seed data."""

import argparse
import asyncio
import hashlib
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from .config import settings

SCHEMA_SQL = """
-- Accounts: where money lives
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    institution TEXT,
    account_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories: hierarchical spending categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    color TEXT
);

-- Transactions: the core data
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    merchant TEXT,
    category_id INTEGER REFERENCES categories(id),
    original_category TEXT,
    notes TEXT,
    import_hash TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Import tracking: what files have been processed
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    institution TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_count INTEGER,
    status TEXT
);

-- Category rules: pattern matching for auto-categorization
CREATE TABLE IF NOT EXISTS category_rules (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    priority INTEGER DEFAULT 0
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_import_hash ON transactions(import_hash);
CREATE INDEX IF NOT EXISTS idx_category_rules_priority ON category_rules(priority DESC);
"""


SEED_CATEGORIES = [
    # Top-level categories with colors
    {"name": "Income", "parent_id": None, "color": "#22c55e"},
    {"name": "Housing", "parent_id": None, "color": "#3b82f6"},
    {"name": "Transportation", "parent_id": None, "color": "#f59e0b"},
    {"name": "Food", "parent_id": None, "color": "#ef4444"},
    {"name": "Shopping", "parent_id": None, "color": "#8b5cf6"},
    {"name": "Entertainment", "parent_id": None, "color": "#ec4899"},
    {"name": "Health", "parent_id": None, "color": "#14b8a6"},
    {"name": "Financial", "parent_id": None, "color": "#64748b"},
    {"name": "Transfers", "parent_id": None, "color": "#94a3b8"},
    {"name": "Uncategorized", "parent_id": None, "color": "#d1d5db"},
]

SEED_SUBCATEGORIES = {
    "Income": ["Salary", "Freelance", "Refunds", "Interest"],
    "Housing": ["Rent/Mortgage", "Utilities", "Home Insurance", "Maintenance"],
    "Transportation": ["Gas", "Public Transit", "Rideshare", "Car Insurance", "Parking"],
    "Food": ["Groceries", "Dining Out", "Coffee", "Alcohol"],
    "Shopping": ["Clothing", "Electronics", "Home Goods", "Gifts"],
    "Entertainment": ["Subscriptions", "Events", "Hobbies", "Travel"],
    "Health": ["Medical", "Pharmacy", "Fitness", "Personal Care"],
    "Financial": ["Investments", "Fees", "Taxes"],
}

SEED_RULES = [
    # Groceries
    ("WHOLE FOODS", "Groceries", 10),
    ("TRADER JOE", "Groceries", 10),
    ("KROGER", "Groceries", 10),
    ("SAFEWAY", "Groceries", 10),
    ("TARGET", "Shopping", 5),
    ("COSTCO", "Groceries", 10),
    ("ALDI", "Groceries", 10),
    # Dining
    ("DOORDASH", "Dining Out", 10),
    ("UBER EATS", "Dining Out", 10),
    ("GRUBHUB", "Dining Out", 10),
    ("MCDONALD", "Dining Out", 10),
    ("STARBUCKS", "Coffee", 10),
    ("DUNKIN", "Coffee", 10),
    # Transportation
    ("UBER TRIP", "Rideshare", 10),
    ("LYFT", "Rideshare", 10),
    ("SHELL", "Gas", 10),
    ("CHEVRON", "Gas", 10),
    ("EXXON", "Gas", 10),
    ("BP ", "Gas", 10),
    # Subscriptions
    ("SPOTIFY", "Subscriptions", 10),
    ("NETFLIX", "Subscriptions", 10),
    ("APPLE.COM/BILL", "Subscriptions", 10),
    ("AMAZON PRIME", "Subscriptions", 10),
    ("HBO MAX", "Subscriptions", 10),
    ("HULU", "Subscriptions", 10),
    # Financial
    ("VANGUARD", "Investments", 10),
    ("TRANSFER TO", "Transfers", 10),
    ("TRANSFER FROM", "Transfers", 10),
    ("ZELLE", "Transfers", 10),
]


def generate_import_hash(date: str, amount: str, description: str, source: str) -> str:
    """Generate a unique hash for transaction deduplication."""
    data = f"{date}|{amount}|{description}|{source}"
    return hashlib.sha256(data.encode()).hexdigest()


@asynccontextmanager
async def get_db():
    """Get async database connection."""
    settings.ensure_directories()
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_database() -> None:
    """Initialize database schema and seed data."""
    settings.ensure_directories()

    async with aiosqlite.connect(settings.database_path) as db:
        # Create schema
        await db.executescript(SCHEMA_SQL)

        # Check if we need to seed
        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        count = (await cursor.fetchone())[0]

        if count == 0:
            print("Seeding categories...")
            # Insert parent categories
            category_ids = {}
            for cat in SEED_CATEGORIES:
                cursor = await db.execute(
                    "INSERT INTO categories (name, parent_id, color) VALUES (?, ?, ?)",
                    (cat["name"], cat["parent_id"], cat["color"]),
                )
                category_ids[cat["name"]] = cursor.lastrowid

            # Insert subcategories
            for parent_name, subcats in SEED_SUBCATEGORIES.items():
                parent_id = category_ids[parent_name]
                for subcat_name in subcats:
                    await db.execute(
                        "INSERT INTO categories (name, parent_id, color) VALUES (?, ?, ?)",
                        (subcat_name, parent_id, None),
                    )

            await db.commit()

            # Get all category IDs for rules
            cursor = await db.execute("SELECT id, name FROM categories")
            all_categories = {row[1]: row[0] for row in await cursor.fetchall()}

            # Insert category rules
            print("Seeding category rules...")
            for pattern, category_name, priority in SEED_RULES:
                if category_name in all_categories:
                    await db.execute(
                        "INSERT INTO category_rules (pattern, category_id, priority) "
                        "VALUES (?, ?, ?)",
                        (pattern, all_categories[category_name], priority),
                    )

            await db.commit()
            print("Database initialized with seed data!")
        else:
            print("Database already initialized.")


def init_database_sync() -> None:
    """Synchronous version for CLI usage."""
    settings.ensure_directories()

    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA_SQL)

    # Check if we need to seed
    cursor.execute("SELECT COUNT(*) FROM categories")
    count = cursor.fetchone()[0]

    if count == 0:
        print("Seeding categories...")
        # Insert parent categories
        category_ids = {}
        for cat in SEED_CATEGORIES:
            cursor.execute(
                "INSERT INTO categories (name, parent_id, color) VALUES (?, ?, ?)",
                (cat["name"], cat["parent_id"], cat["color"]),
            )
            category_ids[cat["name"]] = cursor.lastrowid

        # Insert subcategories
        for parent_name, subcats in SEED_SUBCATEGORIES.items():
            parent_id = category_ids[parent_name]
            for subcat_name in subcats:
                cursor.execute(
                    "INSERT INTO categories (name, parent_id, color) VALUES (?, ?, ?)",
                    (subcat_name, parent_id, None),
                )

        conn.commit()

        # Get all category IDs for rules
        cursor.execute("SELECT id, name FROM categories")
        all_categories = {row[1]: row[0] for row in cursor.fetchall()}

        # Insert category rules
        print("Seeding category rules...")
        for pattern, category_name, priority in SEED_RULES:
            if category_name in all_categories:
                cursor.execute(
                    "INSERT INTO category_rules (pattern, category_id, priority) VALUES (?, ?, ?)",
                    (pattern, all_categories[category_name], priority),
                )

        conn.commit()
        print(f"Database initialized with seed data at {settings.database_path}")
    else:
        print(f"Database already initialized at {settings.database_path}")

    conn.close()


def main() -> None:
    """CLI entry point for database management."""
    parser = argparse.ArgumentParser(description="Manage Finance Tracker database")
    parser.add_argument("--init", action="store_true", help="Initialize database with schema and seed data")
    args = parser.parse_args()

    if args.init:
        init_database_sync()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
