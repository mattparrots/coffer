"""Chase bank CSV parser for credit card and checking accounts."""

import csv
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .base import BaseParser, ParsedTransaction, ParseResult


class ChaseParser(BaseParser):
    """Parser for Chase credit card and checking account CSV files."""

    CREDIT_HEADERS = ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount"]
    CHECKING_HEADERS = ["Details", "Posting Date", "Description", "Amount", "Type", "Balance"]

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a Chase CSV."""
        if not file_path.suffix.lower() == ".csv":
            return False

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                # Check for credit card format
                if all(h in headers for h in self.CREDIT_HEADERS[:3]):
                    return True

                # Check for checking format
                if all(h in headers for h in self.CHECKING_HEADERS[:3]):
                    return True

        except Exception:
            return False

        return False

    def parse(self, file_path: Path) -> ParseResult:
        """Parse Chase CSV file."""
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Determine format
            is_credit = all(h in headers for h in self.CREDIT_HEADERS[:3])
            is_checking = all(h in headers for h in self.CHECKING_HEADERS[:3])

            if not (is_credit or is_checking):
                raise ValueError("Unrecognized Chase CSV format")

            transactions = []
            warnings = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    if is_credit:
                        txn = self._parse_credit_row(row)
                        account_type = "credit"
                    else:
                        txn = self._parse_checking_row(row)
                        account_type = "checking"

                    transactions.append(txn)
                except Exception as e:
                    warnings.append(f"Row {row_num}: {str(e)}")

            # Determine account name from filename
            filename = file_path.stem
            account_name = f"Chase {account_type.title()}"
            if "checking" in filename.lower():
                account_name = "Chase Checking"
            elif "credit" in filename.lower() or "card" in filename.lower():
                account_name = "Chase Credit Card"

            return ParseResult(
                transactions=transactions,
                account_name=account_name,
                institution="Chase",
                warnings=warnings,
            )

    def _parse_credit_row(self, row: dict) -> ParsedTransaction:
        """Parse a credit card CSV row."""
        date_str = row["Transaction Date"]
        date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()

        # Amount is already signed correctly (negative = charge)
        amount = Decimal(row["Amount"])

        description = row["Description"]
        merchant = self._extract_merchant(description)
        category = row.get("Category", "").strip() or None

        return ParsedTransaction(
            date=date_obj,
            amount=amount,
            description=description,
            merchant=merchant,
            original_category=category,
        )

    def _parse_checking_row(self, row: dict) -> ParsedTransaction:
        """Parse a checking account CSV row."""
        date_str = row["Posting Date"]
        date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()

        # Parse amount (may have commas)
        amount_str = row["Amount"].replace(",", "")
        amount = Decimal(amount_str)

        description = row["Description"]
        merchant = self._extract_merchant(description)
        txn_type = row.get("Type", "").strip() or None

        return ParsedTransaction(
            date=date_obj,
            amount=amount,
            description=description,
            merchant=merchant,
            original_category=txn_type,
        )

    def _extract_merchant(self, description: str) -> str | None:
        """Extract merchant name from transaction description."""
        # Remove common patterns
        cleaned = description

        # Remove transaction IDs (sequences of 10+ digits)
        cleaned = re.sub(r"\b\d{10,}\b", "", cleaned)

        # Remove common prefixes
        cleaned = re.sub(r"^(DEBIT CARD|CREDIT CARD|ACH|CHECKCARD|POS)\s+", "", cleaned, flags=re.I)

        # Remove dates in various formats
        cleaned = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", cleaned)

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned if cleaned and cleaned != description else None
