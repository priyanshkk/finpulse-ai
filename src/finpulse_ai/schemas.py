"""Pydantic request and response models for the API layer."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base model that can be built from an ORM object."""

    model_config = ConfigDict(from_attributes=True)


class LineItemIn(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)


class LineItemOut(ORMModel):
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class InvoiceIn(BaseModel):
    vendor: str = Field(min_length=1, max_length=160)
    client: str = Field(min_length=1, max_length=160)
    issued_at: date
    due_at: date
    currency: str = Field(default="INR", max_length=8)
    tax: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = Field(default="pending", pattern="^(paid|pending|overdue)$")
    items: list[LineItemIn] = Field(default_factory=list)
    source: str = "manual"


class InvoiceOut(ORMModel):
    id: int
    number: str
    vendor: str
    client: str
    issued_at: date
    due_at: date
    currency: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    status: str
    source: str
    items: list[LineItemOut]


class ExpenseIn(BaseModel):
    merchant: str = Field(min_length=1, max_length=160)
    category: str = Field(default="Other", max_length=48)
    spent_at: date
    amount: Decimal = Field(gt=0)
    tax: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", max_length=8)
    source: str = "manual"
    note: str | None = None


class ExpenseOut(ORMModel):
    id: int
    merchant: str
    category: str
    spent_at: date
    amount: Decimal
    tax: Decimal
    currency: str
    source: str
    note: str | None


class ScannedItem(BaseModel):
    description: str
    quantity: Decimal
    amount: Decimal


class ScanResult(BaseModel):
    """Structured data extracted from a receipt."""

    merchant: str
    purchase_date: date | None = None
    total: Decimal | None = None
    tax: Decimal | None = None
    currency: str = "INR"
    items: list[ScannedItem] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    engine: str = "heuristic"
    note: str = ""


class Point(BaseModel):
    label: str
    invoiced: Decimal
    spent: Decimal


class Slice(BaseModel):
    label: str
    value: Decimal


class DashboardOut(BaseModel):
    total_invoiced: Decimal
    total_expenses: Decimal
    net: Decimal
    outstanding: Decimal
    invoice_count: int
    expense_count: int
    monthly: list[Point]
    categories: list[Slice]
    recent_invoices: list[InvoiceOut]
    recent_expenses: list[ExpenseOut]
    generated_at: datetime
