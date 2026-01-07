"""Tests for Chase parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile

import pytest

from finance_tracker.parsers.chase import ChaseParser


def test_chase_credit_card_detection():
    """Test Chase credit card CSV detection."""
    parser = ChaseParser()

    # Create a sample Chase credit card CSV
    content = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
12/15/2024,12/16/2024,WHOLE FOODS MARKET,Food & Drink,Sale,-45.23,
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        f.flush()
        file_path = Path(f.name)

    try:
        assert parser.can_parse(file_path)
    finally:
        file_path.unlink()


def test_chase_credit_card_parsing():
    """Test Chase credit card CSV parsing."""
    parser = ChaseParser()

    content = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
12/15/2024,12/16/2024,WHOLE FOODS MARKET,Food & Drink,Sale,-45.23,
12/14/2024,12/15/2024,STARBUCKS,Dining,Sale,-5.50,
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        f.flush()
        file_path = Path(f.name)

    try:
        result = parser.parse(file_path)

        assert result.institution == "Chase"
        assert len(result.transactions) == 2

        # Check first transaction
        txn = result.transactions[0]
        assert txn.date == date(2024, 12, 15)
        assert txn.amount == Decimal("-45.23")
        assert "WHOLE FOODS" in txn.description
        assert txn.original_category == "Food & Drink"

        # Check second transaction
        txn = result.transactions[1]
        assert txn.date == date(2024, 12, 14)
        assert txn.amount == Decimal("-5.50")
        assert "STARBUCKS" in txn.description

    finally:
        file_path.unlink()


def test_chase_checking_parsing():
    """Test Chase checking CSV parsing."""
    parser = ChaseParser()

    content = """Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
DEBIT,12/15/2024,ZELLE TO JOHN DOE,-100.00,ACH_DEBIT,1234.56,
CREDIT,12/16/2024,PAYCHECK,2000.00,ACH_CREDIT,3234.56,
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        f.flush()
        file_path = Path(f.name)

    try:
        result = parser.parse(file_path)

        assert result.institution == "Chase"
        assert len(result.transactions) == 2

        # Check debit transaction
        txn = result.transactions[0]
        assert txn.date == date(2024, 12, 15)
        assert txn.amount == Decimal("-100.00")

        # Check credit transaction
        txn = result.transactions[1]
        assert txn.date == date(2024, 12, 16)
        assert txn.amount == Decimal("2000.00")

    finally:
        file_path.unlink()
