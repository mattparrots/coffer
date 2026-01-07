"""Venmo transaction history CSV parser."""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .base import BaseParser, ParsedTransaction, ParseResult


class VenmoParser(BaseParser):
    """Parser for Venmo transaction history CSV files."""

    REQUIRED_HEADERS = ["Datetime", "Type", "Status", "Amount (total)"]

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a Venmo CSV."""
        if not file_path.suffix.lower() == ".csv":
            return False

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                # Venmo CSVs have metadata rows at the top, skip them
                lines = []
                for _ in range(10):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)

                # Look for header row
                for i, line in enumerate(lines):
                    if "Datetime" in line and "Amount (total)" in line:
                        # Found the header, check if it's Venmo format
                        reader = csv.DictReader(lines[i:])
                        headers = reader.fieldnames or []
                        return all(h in headers for h in self.REQUIRED_HEADERS)

        except Exception:
            return False

        return False

    def parse(self, file_path: Path) -> ParseResult:
        """Parse Venmo CSV file."""
        with open(file_path, "r", encoding="utf-8-sig") as f:
            # Skip metadata rows until we find the header
            lines = f.readlines()
            header_idx = 0

            for i, line in enumerate(lines):
                if "Datetime" in line and "Amount (total)" in line:
                    header_idx = i
                    break

            if header_idx == 0 and "Datetime" not in lines[0]:
                raise ValueError("Could not find Venmo CSV header row")

            # Parse from header onwards
            reader = csv.DictReader(lines[header_idx:])
            transactions = []
            warnings = []

            for row_num, row in enumerate(reader, start=header_idx + 2):
                try:
                    # Skip incomplete transactions
                    if row.get("Status") != "Complete":
                        continue

                    # Skip bank transfers
                    txn_type = row.get("Type", "")
                    if txn_type == "Standard Transfer":
                        continue

                    txn = self._parse_row(row)
                    transactions.append(txn)
                except Exception as e:
                    warnings.append(f"Row {row_num}: {str(e)}")

            return ParseResult(
                transactions=transactions,
                account_name="Venmo",
                institution="Venmo",
                warnings=warnings,
            )

    def _parse_row(self, row: dict) -> ParsedTransaction:
        """Parse a Venmo CSV row."""
        # Parse datetime (format: 2024-12-15T14:30:00)
        datetime_str = row["Datetime"]
        date_obj = datetime.fromisoformat(datetime_str).date()

        # Parse amount: "+ $25.00" or "- $25.00"
        amount_str = row["Amount (total)"].strip()
        amount_str = amount_str.replace("$", "").replace(",", "").strip()

        # Handle +/- prefix
        if amount_str.startswith("+"):
            amount = Decimal(amount_str[1:].strip())
        elif amount_str.startswith("-"):
            amount = -Decimal(amount_str[1:].strip())
        else:
            amount = Decimal(amount_str)

        # Determine direction from Type and From/To
        txn_type = row.get("Type", "")
        from_user = row.get("From", "")
        to_user = row.get("To", "")

        # Payment to you = positive, from you = negative
        # Charge inverts this
        if txn_type == "Charge":
            amount = -amount

        # Get description from Note field
        description = row.get("Note", "").strip()
        if not description:
            # Fallback to constructing from From/To
            if amount > 0:
                description = f"Payment from {from_user}"
            else:
                description = f"Payment to {to_user}"

        # Use From/To as merchant
        merchant = to_user if amount < 0 else from_user
        merchant = merchant.strip() if merchant else None

        return ParsedTransaction(
            date=date_obj,
            amount=amount,
            description=description,
            merchant=merchant,
            original_category=txn_type,
        )
