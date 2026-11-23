"""Server-rendered pages for the dashboard and receipt workflow."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..schemas import ExpenseIn
from ..services import charts, ledger, receipts, seed

router = APIRouter(tags=["web"])
settings = get_settings()
templates = Jinja2Templates(directory=str(settings.app_dir / "templates"))
DbSession = Annotated[Session, Depends(get_db)]


def _render(request: Request, name: str, session: Session | None, **extra: Any) -> HTMLResponse:
    context: dict[str, Any] = {
        "active": name.removesuffix(".html"),
        "ai_enabled": settings.ai_enabled,
        "version": __import__("finpulse_ai").__version__,
    }
    context.update(extra)
    return templates.TemplateResponse(request, name, context)


@router.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request, session: DbSession) -> HTMLResponse:
    """Render KPIs, cashflow and category charts."""
    data = ledger.dashboard(session)
    return _render(
        request,
        "dashboard.html",
        session,
        data=data,
        cashflow=charts.cashflow_svg(data["monthly"]),
        categories=charts.category_svg(data["categories"]),
    )


@router.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, session: DbSession) -> HTMLResponse:
    """Render the invoice table."""
    return _render(request, "invoices.html", session, rows=ledger.list_invoices(session))


@router.get("/expenses", response_class=HTMLResponse)
def expenses_page(request: Request, session: DbSession) -> HTMLResponse:
    """Render the expense table."""
    return _render(request, "expenses.html", session, rows=ledger.list_expenses(session))


@router.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request) -> HTMLResponse:
    """Render the receipt upload form."""
    return _render(request, "scan.html", None, result=None, error=None, today=date.today())


@router.post("/scan", response_class=HTMLResponse)
async def scan_submit(
    request: Request,
    session: DbSession,
    text: Annotated[str, Form()] = "",
    filename: Annotated[str, Form()] = "receipt.txt",
    file: Annotated[UploadFile | None, File()] = None,
) -> HTMLResponse:
    """Extract fields from pasted text or an uploaded file and show a review form."""
    raw_text = text
    name = filename or "receipt.txt"
    if file and file.filename:
        try:
            name = receipts.safe_filename(file.filename)
        except ValueError as exc:
            return _render(request, "scan.html", session, result=None, error=str(exc), today=date.today())
        data = await file.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            return _render(
                request, "scan.html", session, result=None, error="File too large", today=date.today()
            )
        raw_text = receipts.text_from_bytes(data, name) or text
    result = receipts.scan_receipt(
        filename=name,
        text=raw_text,
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )
    return _render(request, "scan.html", session, result=result, error=None, today=date.today())


@router.post("/scan/save")
def scan_save(
    merchant: Annotated[str, Form()],
    spent_at: Annotated[str, Form()],
    amount: Annotated[str, Form()],
    session: DbSession,
    category: Annotated[str, Form()] = "Other",
    tax: Annotated[str, Form()] = "0",
    currency: Annotated[str, Form()] = "INR",
) -> RedirectResponse:
    """Persist the reviewed expense and redirect to the expense list."""
    try:
        payload = ExpenseIn(
            merchant=merchant,
            category=category,
            spent_at=date.fromisoformat(spent_at),
            amount=Decimal(amount.replace(",", "")),
            tax=Decimal(tax.replace(",", "") or "0"),
            currency=currency,
            source="scan",
        )
    except (InvalidOperation, ValueError):
        return RedirectResponse("/scan?error=invalid", status_code=303)
    ledger.create_expense(session, payload)
    return RedirectResponse("/expenses?saved=1", status_code=303)


@router.post("/demo/seed")
def seed_page(session: DbSession) -> RedirectResponse:
    """Seed demo data from the UI."""
    seed.seed_database(session)
    return RedirectResponse("/?seeded=1", status_code=303)
