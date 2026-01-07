"""Apple Card CSV parser."""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .base import BaseParser, ParsedTransaction, ParseResult


class AppleCardParser(BaseParser):
    """Parser for Apple Card CSV files."""

    REQUIRED_HEADERS = [
        "Transaction Date",
        "Clearing Date",
        "Description",
        "Merchant",
        "Category",
        "Type",
        "Amount (USD)",
    ]

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is an Apple Card CSV."""
        if not file_path.suffix.lower() == ".csv":
            return False

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                return all(h in headers for h in self.REQUIRED_HEADERS)
        except Exception:
            return False

        return False

    def parse(self, file_path: Path) -> ParseResult:
        """Parse Apple Card CSV file."""
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            transactions = []
            warnings = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    txn = self._parse_row(row)
                    transactions.append(txn)
                except Exception as e:
                    warnings.append(f"Row {row_num}: {str(e)}")

            return ParseResult(
                transactions=transactions,
                account_name="Apple Card",
                institution="Apple",
                warnings=warnings,
            )

    def _parse_row(self, row: dict) -> ParsedTransaction:
        """Parse an Apple Card CSV row."""
        # Parse transaction date
        date_str = row["Transaction Date"]
        date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()

        # Parse amount - Apple Card shows positive for purchases, convert to negative
        amount_str = row["Amount (USD)"].replace(",", "")
        amount = Decimal(amount_str)

        # Purchases are shown as positive, but should be negative (money out)
        txn_type = row.get("Type", "")
        if txn_type == "Purchase":
            amount = -amount
        # Refunds/credits stay positive

        description = row["Description"]
        merchant = row.get("Merchant", "").strip() or None
        category = row.get("Category", "").strip() or None

        return ParsedTransaction(
            date=date_obj,
            amount=amount,
            description=description,
            merchant=merchant,
            original_category=category,
        )
