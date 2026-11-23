"""Aggregation tests that do not need a database."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from finpulse_ai.models import Expense, Invoice
from finpulse_ai.schemas import Point, Slice
from finpulse_ai.services.analytics import build_dashboard

NOW = datetime(2026, 11, 23, 10, 0, tzinfo=UTC)
D = Decimal


def invoice(total: str, when: date, status: str = "paid") -> Invoice:
    return Invoice(
        id=1,
        number=f"INV-{total}",
        vendor="V",
        client="C",
        issued_at=when,
        due_at=when,
        currency="INR",
        subtotal=D(total),
        tax=D("0"),
        total=D(total),
        status=status,
        source="manual",
        items=[],
    )


def expense(amount: str, category: str, when: date) -> Expense:
    return Expense(
        id=1,
        merchant="M",
        category=category,
        spent_at=when,
        amount=D(amount),
        tax=D("0"),
        currency="INR",
        source="manual",
        note=None,
    )


def test_totals_and_outstanding() -> None:
    rows_in = [invoice("100.00", date(2026, 11, 1)), invoice("50.00", date(2026, 10, 1), "pending")]
    rows_ex = [expense("30.00", "Software", date(2026, 11, 2))]
    data = build_dashboard(rows_in, rows_ex, generated_at=NOW)
    assert data["total_invoiced"] == D("150.00")
    assert data["total_expenses"] == D("30.00")
    assert data["net"] == D("120.00")
    assert data["outstanding"] == D("50.00")
    assert data["invoice_count"] == 2
    assert data["expense_count"] == 1


def test_monthly_series_has_six_buckets_and_ignores_old_rows() -> None:
    rows = [
        invoice("100", date(2026, 11, 5)),
        invoice("40", date(2026, 8, 5)),
        invoice("999", date(2024, 1, 5)),
    ]
    data = build_dashboard(rows, [], generated_at=NOW)
    monthly = data["monthly"]
    assert len(monthly) == 6
    assert isinstance(monthly[0], Point)
    assert monthly[-1].label == "Nov 2026"
    assert monthly[-1].invoiced == D("100")
    assert sum(point.invoiced for point in monthly) == D("140")


def test_categories_are_sorted_by_value_and_limited() -> None:
    rows = [expense("10", "Travel", date(2026, 11, i + 1)) for i in range(2)]
    rows += [expense("50", "Software", date(2026, 11, 3)), expense("30", "Meals", date(2026, 11, 4))]
    data = build_dashboard([], rows, generated_at=NOW)
    assert data["categories"] == [
        Slice(label="Software", value=D("50")),
        Slice(label="Meals", value=D("30")),
        Slice(label="Travel", value=D("20")),
    ]


def test_recent_records_are_limited_to_five() -> None:
    rows = [invoice(str(i), date(2026, 1, 1).replace(day=1 + i)) for i in range(1, 8)]
    data = build_dashboard(rows, [], generated_at=NOW)
    assert len(data["recent_invoices"]) == 5
    assert data["recent_invoices"][0].number == "INV-7"


def test_empty_input_still_returns_a_complete_shape() -> None:
    data = build_dashboard([], [], generated_at=NOW)
    assert data["total_invoiced"] == 0
    assert data["categories"] == []
    assert len(data["monthly"]) == 6
    assert data["generated_at"] == NOW
