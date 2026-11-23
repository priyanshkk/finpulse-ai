"""JSON API routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from .. import __version__
from ..config import get_settings
from ..db import get_db
from ..schemas import DashboardOut, ExpenseIn, ExpenseOut, InvoiceIn, InvoiceOut, ScanResult
from ..services import ledger, receipts, seed

router = APIRouter(prefix="/api", tags=["api"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health() -> dict[str, str]:
    """Lightweight readiness probe used by Docker and CI."""
    return {"status": "ok", "version": __version__}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(session: DbSession) -> dict[str, Any]:
    """Return KPIs, monthly cashflow and category breakdown."""
    return ledger.dashboard(session)


@router.get("/invoices", response_model=list[InvoiceOut])
def invoices(session: DbSession) -> list[InvoiceOut]:
    """List recent invoices."""
    return ledger.list_invoices(session)


@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def add_invoice(payload: InvoiceIn, session: DbSession) -> InvoiceOut:
    """Create an invoice with derived line totals."""
    return InvoiceOut.model_validate(ledger.create_invoice(session, payload))


@router.get("/expenses", response_model=list[ExpenseOut])
def expenses(session: DbSession) -> list[ExpenseOut]:
    """List recent expenses."""
    return ledger.list_expenses(session)


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def add_expense(payload: ExpenseIn, session: DbSession) -> ExpenseOut:
    """Record a business expense."""
    return ExpenseOut.model_validate(ledger.create_expense(session, payload))


@router.delete("/invoices/{record_id}")
def remove_invoice(record_id: int, session: DbSession) -> dict[str, bool]:
    """Delete an invoice by id."""
    if not ledger.delete_record(session, "invoice", record_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"deleted": True}


@router.delete("/expenses/{record_id}")
def remove_expense(record_id: int, session: DbSession) -> dict[str, bool]:
    """Delete an expense by id."""
    if not ledger.delete_record(session, "expense", record_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"deleted": True}


@router.post("/scan", response_model=ScanResult)
async def scan(
    request: Request,
    session: DbSession,
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
) -> ScanResult:
    """Extract receipt fields from an uploaded file or pasted text."""
    settings = get_settings()
    raw_text = ""
    filename = "receipt.txt"

    if file and file.filename:
        try:
            filename = receipts.safe_filename(file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        data = await file.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        raw_text = receipts.text_from_bytes(data, filename)
    elif text is None and request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
        text = str(body.get("text", ""))
        filename = str(body.get("filename") or "receipt.txt")
        raw_text = text
    else:
        raw_text = text or ""

    if not raw_text.strip() and not filename.lower().endswith(".txt") and not settings.ai_enabled:
        return receipts.scan_receipt(
            filename=filename,
            text="",
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    return receipts.scan_receipt(
        filename=filename,
        text=raw_text,
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )


@router.post("/seed")
def seed_demo(session: DbSession) -> dict[str, int]:
    """Populate deterministic demo data (idempotent)."""
    return seed.seed_database(session)
