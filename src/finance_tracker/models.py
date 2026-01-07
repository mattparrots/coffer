"""Pydantic models for API validation and data transfer."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    """Model for creating an account."""

    name: str
    institution: str | None = None
    account_type: str | None = None


class Account(BaseModel):
    """Account model."""

    id: int
    name: str
    institution: str | None
    account_type: str | None
    created_at: datetime


class CategoryCreate(BaseModel):
    """Model for creating a category."""

    name: str
    parent_id: int | None = None
    color: str | None = None


class Category(BaseModel):
    """Category model."""

    id: int
    name: str
    parent_id: int | None
    color: str | None


class CategoryWithChildren(Category):
    """Category model with nested children."""

    children: list["Category"] = []


class TransactionCreate(BaseModel):
    """Model for creating a transaction."""

    account_id: int
    date: date
    amount: Decimal
    description: str
    merchant: str | None = None
    category_id: int | None = None
    original_category: str | None = None
    notes: str | None = None


class TransactionUpdate(BaseModel):
    """Model for updating a transaction."""

    category_id: int | None = None
    notes: str | None = None
    merchant: str | None = None


class Transaction(BaseModel):
    """Transaction model."""

    id: int
    account_id: int
    date: date
    amount: Decimal
    description: str
    merchant: str | None
    category_id: int | None
    original_category: str | None
    notes: str | None
    import_hash: str | None
    created_at: datetime


class TransactionWithDetails(Transaction):
    """Transaction with related account and category information."""

    account_name: str | None = None
    category_name: str | None = None
    category_color: str | None = None


class CategoryRuleCreate(BaseModel):
    """Model for creating a category rule."""

    pattern: str
    category_id: int
    priority: int = 0


class CategoryRule(BaseModel):
    """Category rule model."""

    id: int
    pattern: str
    category_id: int
    priority: int


class ImportCreate(BaseModel):
    """Model for creating an import record."""

    filename: str
    institution: str | None = None
    transaction_count: int = 0
    status: str = "pending"


class Import(BaseModel):
    """Import model."""

    id: int
    filename: str
    institution: str | None
    imported_at: datetime
    transaction_count: int
    status: str


class MonthlySummary(BaseModel):
    """Monthly summary statistics."""

    income: Decimal
    expenses: Decimal
    net: Decimal
    income_change_pct: Decimal | None = None
    expenses_change_pct: Decimal | None = None


class CategorySpending(BaseModel):
    """Spending by category."""

    category_id: int
    category_name: str
    color: str | None
    amount: Decimal
    percentage: Decimal


class MonthlyFlow(BaseModel):
    """Monthly cash flow data."""

    month: str
    income: Decimal
    expenses: Decimal
    net: Decimal
