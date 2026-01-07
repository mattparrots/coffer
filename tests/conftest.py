"""Pytest configuration and fixtures."""

import asyncio
from pathlib import Path

import pytest
import aiosqlite

from finance_tracker.config import settings
from finance_tracker.database import SCHEMA_SQL


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"

    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
        yield db
