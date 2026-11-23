"""Create and list invoices and expenses."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Expense, Invoice, LineItem
from ..schemas import ExpenseIn, ExpenseOut, InvoiceIn, InvoiceOut


def _next_number(session: Session, issued_at: date) -> str:
    prefix = f"INV-{issued_at.year}-"
    numbers = session.scalars(select(Invoice.number).where(Invoice.number.startswith(prefix))).all()
    highest = max(
        (int(value.rsplit("-", 1)[-1]) for value in numbers if value.rsplit("-", 1)[-1].isdigit()), default=0
    )
    return f"{prefix}{highest + 1:04d}"


def create_invoice(session: Session, payload: InvoiceIn) -> Invoice:
    """Persist an invoice with its line items and derived totals."""
    subtotal = sum((item.quantity * item.unit_price for item in payload.items), Decimal("0"))
    invoice = Invoice(
        number=_next_number(session, payload.issued_at),
        vendor=payload.vendor,
        client=payload.client,
        issued_at=payload.issued_at,
        due_at=max(payload.due_at, payload.issued_at + timedelta(days=1)),
        currency=payload.currency,
        subtotal=subtotal,
        tax=payload.tax,
        total=subtotal + payload.tax,
        status=payload.status,
        source=payload.source,
    )
    for item in payload.items:
        invoice.items.append(
            LineItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=item.quantity * item.unit_price,
            )
        )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice


def list_invoices(session: Session, limit: int = 100) -> list[InvoiceOut]:
    """Return the newest invoices first."""
    rows = session.scalars(
        select(Invoice).order_by(Invoice.issued_at.desc(), Invoice.id.desc()).limit(limit)
    ).all()
    return [InvoiceOut.model_validate(row) for row in rows]


def create_expense(session: Session, payload: ExpenseIn) -> Expense:
    """Persist a single business expense."""
    expense = Expense(**payload.model_dump())
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def list_expenses(session: Session, limit: int = 100) -> list[ExpenseOut]:
    """Return the newest expenses first."""
    rows = session.scalars(
        select(Expense).order_by(Expense.spent_at.desc(), Expense.id.desc()).limit(limit)
    ).all()
    return [ExpenseOut.model_validate(row) for row in rows]


def delete_record(session: Session, kind: str, record_id: int) -> bool:
    """Delete an invoice or expense by id; return False when not found."""
    model = Invoice if kind == "invoice" else Expense
    record = session.get(model, record_id)
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True


def dashboard(session: Session) -> dict[str, Any]:
    """Compute the numbers and series rendered on the dashboard."""
    from datetime import datetime

    from .analytics import build_dashboard

    rows_in: Sequence[Invoice] = session.scalars(select(Invoice)).all()
    rows_ex: Sequence[Expense] = session.scalars(select(Expense)).all()
    return build_dashboard(rows_in, rows_ex, generated_at=datetime.now(UTC))
