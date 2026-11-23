"""Database-agnostic aggregation used by the dashboard and API."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from ..models import Expense, Invoice
from ..schemas import ExpenseOut, InvoiceOut, Point, Slice


def _month_label(value: date) -> str:
    return value.strftime("%b %Y")


def build_dashboard(
    invoices: Sequence[Invoice],
    expenses: Sequence[Expense],
    *,
    generated_at: datetime | None = None,
    months: int = 6,
) -> dict[str, Any]:
    """Aggregate records into totals, a monthly cashflow and category slices."""
    today = (generated_at or datetime.now(UTC)).date()
    first = today.replace(day=1)
    for _ in range(months - 1):
        first = (first - timedelta(days=1)).replace(day=1)
    buckets = [
        date(first.year + (first.month - 1 + index) // 12, (first.month - 1 + index) % 12 + 1, 1)
        for index in range(months)
    ]

    series: dict[str, dict[str, Decimal]] = {
        _month_label(bucket): {"invoiced": Decimal("0"), "spent": Decimal("0")} for bucket in buckets
    }
    categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    total_invoiced = sum((invoice.total for invoice in invoices), Decimal("0"))
    total_expenses = sum((expense.amount for expense in expenses), Decimal("0"))
    outstanding = sum((invoice.total for invoice in invoices if invoice.status != "paid"), Decimal("0"))

    for invoice in invoices:
        key = _month_label(invoice.issued_at)
        if key in series:
            series[key]["invoiced"] += invoice.total
    for expense in expenses:
        key = _month_label(expense.spent_at)
        if key in series:
            series[key]["spent"] += expense.amount
        categories[expense.category] += expense.amount

    ordered_invoices = sorted(invoices, key=lambda row: (row.issued_at, row.id), reverse=True)[:5]
    ordered_expenses = sorted(expenses, key=lambda row: (row.spent_at, row.id), reverse=True)[:5]

    return {
        "total_invoiced": total_invoiced,
        "total_expenses": total_expenses,
        "net": total_invoiced - total_expenses,
        "outstanding": outstanding,
        "invoice_count": len(invoices),
        "expense_count": len(expenses),
        "monthly": [
            Point(label=label, invoiced=values["invoiced"], spent=values["spent"])
            for label, values in series.items()
        ],
        "categories": [
            Slice(label=label, value=value)
            for label, value in sorted(categories.items(), key=lambda pair: pair[1], reverse=True)[:6]
        ],
        "recent_invoices": [InvoiceOut.model_validate(row) for row in ordered_invoices],
        "recent_expenses": [ExpenseOut.model_validate(row) for row in ordered_expenses],
        "generated_at": generated_at or datetime.now(UTC),
    }
