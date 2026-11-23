"""Deterministic demo data and idempotent seeding."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finpulse_ai.models import Expense, Invoice, LineItem
from finpulse_ai.schemas import ExpenseIn, InvoiceIn, LineItemIn
from finpulse_ai.services import ledger, seed


def test_seed_inserts_expected_counts(session: Session) -> None:
    counts = seed.seed_database(session)
    assert counts == {"invoices": 14, "expenses": 18}
    assert session.scalar(select(func.count()).select_from(Invoice)) == 14
    assert session.scalar(select(func.count()).select_from(Expense)) == 18
    assert session.scalar(select(func.count()).select_from(LineItem)) == 14


def test_seed_is_idempotent(session: Session) -> None:
    seed.seed_database(session)
    assert seed.seed_database(session) == {"invoices": 0, "expenses": 0}
    assert seed.is_seeded(session) is True
    assert session.scalar(select(func.count()).select_from(Invoice)) == 14


def test_seed_is_deterministic(session: Session) -> None:
    seed.seed_database(session)
    first = [(row.vendor, row.total) for row in session.scalars(select(Invoice)).all()]
    seed.clear_seed(session)
    seed.seed_database(session)
    second = [(row.vendor, row.total) for row in session.scalars(select(Invoice)).all()]
    assert first == second


def test_clear_seed_keeps_user_records(session: Session) -> None:
    today = date.today()
    user_invoice = ledger.create_invoice(
        session,
        InvoiceIn(
            vendor="Mine",
            client="Client",
            issued_at=today,
            due_at=today + timedelta(days=2),
            items=[LineItemIn(description="Work", quantity=Decimal("1"), unit_price=Decimal("100"))],
        ),
    )
    user_expense = ledger.create_expense(
        session,
        ExpenseIn(
            merchant="Mine",
            spent_at=today,
            amount=Decimal("25"),
        ),
    )
    seed.seed_database(session)
    seed.clear_seed(session)
    assert seed.is_seeded(session) is False
    assert session.get(Invoice, user_invoice.id) is not None
    assert session.get(Expense, user_expense.id) is not None
    assert session.scalar(select(func.count()).select_from(Invoice)) == 1


def test_seeded_data_spans_months_and_categories(session: Session) -> None:
    seed.seed_database(session)
    data = ledger.dashboard(session)
    assert len({point.label for point in data["monthly"]}) >= 4
    assert len(data["categories"]) >= 4
    assert sum(point.invoiced for point in data["monthly"]) > 0
