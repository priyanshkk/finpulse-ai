"""Deterministic demo data so a fresh install never shows an empty dashboard."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Expense, Invoice
from ..schemas import ExpenseIn, InvoiceIn, LineItemIn
from .ledger import create_expense, create_invoice

VENDORS = ("Northstar Studio", "Bluefin Labs", "Vertex Design Co", "Cedar & Co", "Lumen Works")
CLIENTS = ("Acme Corp", "Globex", "Initech", "Umbrella Ltd", "Soylent Inc")
CATEGORIES = ("Travel", "Software", "Meals", "Office", "Marketing", "Utilities")
MERCHANTS = ("Uber", "Figma", "Blue Tokai", "Amazon", "Google Ads", "Airbnb", "Notion", "Swiggy")
WORK = ("Brand identity sprint", "Landing page build", "UX research", "API integration", "Monthly retainer")
D = Decimal


def is_seeded(session: Session) -> bool:
    """Return whether demo rows already exist."""
    count = session.scalar(select(func.count()).select_from(Invoice).where(Invoice.source == "seed"))
    return bool(count)


def seed_database(session: Session, *, invoice_count: int = 14, expense_count: int = 18) -> dict[str, int]:
    """Insert a deterministic set of invoices and expenses once."""
    if is_seeded(session):
        return {"invoices": 0, "expenses": 0}

    rng = random.Random(42)
    today = date.today()

    for _ in range(invoice_count):
        issued = today - timedelta(days=rng.randint(0, 170))
        quantity = D(rng.randint(1, 4))
        price = D(rng.choice((1200, 2400, 3500, 4800, 6500, 8900))) / 100
        payload = InvoiceIn(
            vendor=rng.choice(VENDORS),
            client=rng.choice(CLIENTS),
            issued_at=issued,
            due_at=issued + timedelta(days=rng.choice((7, 14, 30))),
            currency="INR",
            tax=D("18") / 100 * quantity * price,
            status=rng.choice(("paid", "paid", "pending", "overdue")),
            source="seed",
            items=[LineItemIn(description=rng.choice(WORK), quantity=quantity, unit_price=price)],
        )
        create_invoice(session, payload)

    for _ in range(expense_count):
        create_expense(
            session,
            ExpenseIn(
                merchant=rng.choice(MERCHANTS),
                category=rng.choice(CATEGORIES),
                spent_at=today - timedelta(days=rng.randint(0, 170)),
                amount=D(rng.randint(150, 9500)) / 100,
                tax=D(rng.randint(0, 800)) / 100,
                currency="INR",
                source="seed",
                note="Demo data",
            ),
        )

    return {"invoices": invoice_count, "expenses": expense_count}


def clear_seed(session: Session) -> None:
    """Remove demo rows without touching user-created records."""
    for invoice in session.scalars(select(Invoice).where(Invoice.source == "seed")).all():
        session.delete(invoice)
    for expense in session.scalars(select(Expense).where(Expense.source == "seed")).all():
        session.delete(expense)
    session.commit()
