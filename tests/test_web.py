"""Server-rendered pages and the scan-to-expense workflow."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finpulse_ai.models import Expense

SAMPLE = """Blue Tokai
12/04/2026
Coffee beans      2 x 450.00
GST 18%           162.00
TOTAL             1,062.00
"""


@pytest.mark.parametrize(
    "path", ["/", "/invoices", "/expenses", "/scan", "/static/app.css", "/static/logo.svg"]
)
def test_pages_are_served(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    if path.endswith(".css") or path.endswith(".svg"):
        assert len(response.content) > 20
    else:
        assert b"FinPulse" in response.content


def test_dashboard_renders_seeded_charts(client: TestClient) -> None:
    client.post("/api/seed")
    html = client.get("/").text
    assert "Monthly cashflow chart" in html
    assert "Spend by category" in html
    assert "₹" in html


def test_scan_form_extracts_and_reviews(client: TestClient) -> None:
    html = client.post("/scan", data={"text": SAMPLE, "filename": "receipt.txt"}).text
    assert "Blue Tokai" in html
    assert "Save as expense" in html
    assert "heuristic" in html
    assert 'value="2026-04-12"' in html


def test_scan_save_creates_expense(client: TestClient, session: Session) -> None:
    response = client.post(
        "/scan/save",
        data={
            "merchant": "Blue Tokai",
            "spent_at": "2026-04-12",
            "amount": "1062.00",
            "tax": "162.00",
            "category": "Meals",
            "currency": "INR",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/expenses?saved=1"
    count = session.scalar(select(func.count()).select_from(Expense))
    assert count == 1
    assert session.scalars(select(Expense)).first().source == "scan"


def test_scan_save_rejects_bad_amount(client: TestClient) -> None:
    response = client.post(
        "/scan/save",
        data={
            "merchant": "Shop",
            "spent_at": "2026-04-12",
            "amount": "not-a-number",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/scan?error=invalid"


def test_seed_button_redirects(client: TestClient) -> None:
    response = client.post("/demo/seed", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?seeded=1"


def test_toast_after_save(client: TestClient) -> None:
    response = client.get("/expenses?saved=1")
    assert "Changes are live" in response.text
