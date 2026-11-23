"""Ledger service: numbering, derived totals, deletion and dashboard input."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finpulse_ai.schemas import ExpenseIn, InvoiceIn, LineItemIn
from finpulse_ai.services import ledger

D = Decimal


def invoice_payload(when: date | None = None, status: str = "pending") -> InvoiceIn:
    issued = when or date.today()
    return InvoiceIn(
        vendor="Northstar Studio",
        client="Acme Corp",
        issued_at=issued,
        due_at=issued + timedelta(days=7),
        currency="INR",
        tax=D("18.00"),
        status=status,
        items=[
            LineItemIn(description="Design work", quantity=D("2"), unit_price=D("100.00")),
            LineItemIn(description="Consulting", quantity=D("1"), unit_price=D("50.00")),
        ],
    )


def test_create_invoice_computes_totals_and_number(session: Session) -> None:
    created = ledger.create_invoice(session, invoice_payload())
    assert created.number == f"INV-{date.today().year}-0001"
    assert created.subtotal == D("250.00")
    assert created.tax == D("18.00")
    assert created.total == D("268.00")
    assert [item.amount for item in created.items] == [D("200.00"), D("50.00")]


def test_invoice_numbers_increment_per_year(session: Session) -> None:
    first = ledger.create_invoice(session, invoice_payload())
    second = ledger.create_invoice(session, invoice_payload())
    assert first.number.endswith("0001")
    assert second.number.endswith("0002")
    other_year = ledger.create_invoice(session, invoice_payload(date(2020, 5, 4)))
    assert other_year.number == "INV-2020-0001"


def test_due_date_never_precedes_issue_date(session: Session) -> None:
    issued = date(2026, 1, 10)
    payload = invoice_payload(issued)
    payload.due_at = issued - timedelta(days=5)
    created = ledger.create_invoice(session, payload)
    assert created.due_at == issued + timedelta(days=1)


def test_list_invoices_newest_first(session: Session) -> None:
    ledger.create_invoice(session, invoice_payload(date(2026, 1, 1)))
    ledger.create_invoice(session, invoice_payload(date(2026, 9, 1)))
    rows = ledger.list_invoices(session)
    assert len(rows) == 2
    assert rows[0].issued_at == date(2026, 9, 1)
    assert len(rows[0].items) == 2


def test_expense_crud(session: Session) -> None:
    payload = ExpenseIn(
        merchant="Uber", category="Travel", spent_at=date(2026, 11, 2), amount=D("450.50"), tax=D("30.00")
    )
    created = ledger.create_expense(session, payload)
    assert created.id == 1
    assert ledger.list_expenses(session)[0].merchant == "Uber"
    assert ledger.delete_record(session, "expense", created.id) is True
    assert ledger.list_expenses(session) == []


def test_delete_record_reports_missing(session: Session) -> None:
    assert ledger.delete_record(session, "invoice", 999) is False
    assert ledger.delete_record(session, "expense", 999) is False


def test_delete_invoice_removes_line_items(session: Session) -> None:
    created = ledger.create_invoice(session, invoice_payload())
    assert ledger.delete_record(session, "invoice", created.id) is True
    assert ledger.list_invoices(session) == []


def test_dashboard_uses_persisted_records(session: Session) -> None:
    ledger.create_invoice(session, invoice_payload(status="paid"))
    ledger.create_expense(session, ExpenseIn(merchant="Figma", spent_at=date.today(), amount=D("10")))
    data = ledger.dashboard(session)
    assert data["invoice_count"] == 1
    assert data["expense_count"] == 1
    assert data["total_invoiced"] == D("268.00")
    assert data["net"] == D("258.00")


def test_invoice_requires_items_metadata() -> None:
    with pytest.raises(ValueError):
        InvoiceIn(vendor="", client="Acme", issued_at=date.today(), due_at=date.today())
