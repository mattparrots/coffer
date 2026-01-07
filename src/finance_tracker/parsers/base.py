"""Base parser interface for transaction file imports."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass
class ParsedTransaction:
    """A single parsed transaction."""

    date: date
    amount: Decimal
    description: str
    merchant: str | None = None
    original_category: str | None = None


@dataclass
class ParseResult:
    """Result of parsing a transaction file."""

    transactions: list[ParsedTransaction]
    account_name: str
    institution: str
    warnings: list[str]


class BaseParser(ABC):
    """Abstract base class for transaction file parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this parser can parse the file
        """
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """
        Parse file and return normalized transactions.

        Args:
            file_path: Path to the file to parse

        Returns:
            ParseResult containing transactions and metadata

        Raises:
            ValueError: If file cannot be parsed
        """
        pass
