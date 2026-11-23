"""JSON API contract tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from finpulse_ai.config import get_settings
from finpulse_ai.routers import api

SAMPLE = """Blue Tokai
12/04/2026
Coffee beans      2 x 450.00
GST 18%           162.00
TOTAL             1,062.00
"""
INVOICE = {
    "vendor": "Northstar Studio",
    "client": "Acme Corp",
    "issued_at": "2026-11-23",
    "due_at": "2026-12-07",
    "tax": "18.00",
    "items": [{"description": "Design sprint", "quantity": 2, "unit_price": "100.00"}],
}
EXPENSE = {
    "merchant": "Blue Tokai",
    "category": "Meals",
    "spent_at": "2026-11-23",
    "amount": "1062.00",
    "tax": "162.00",
}


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_seed_and_dashboard(client: TestClient) -> None:
    assert client.post("/api/seed").json() == {"invoices": 14, "expenses": 18}
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["invoice_count"] == 14
    assert body["expense_count"] == 18
    assert len(body["monthly"]) == 6
    assert len(body["categories"]) >= 4
    assert len(body["recent_invoices"]) == 5


def test_empty_dashboard(client: TestClient) -> None:
    body = client.get("/api/dashboard").json()
    assert body["total_invoiced"] == "0"
    assert body["recent_expenses"] == []


def test_create_list_and_delete_invoice(client: TestClient) -> None:
    created = client.post("/api/invoices", json=INVOICE)
    assert created.status_code == 201
    body = created.json()
    assert body["number"] == "INV-2026-0001"
    assert body["total"] == "218.00"
    assert len(body["items"]) == 1
    assert client.get("/api/invoices").json()[0]["id"] == body["id"]
    assert client.delete(f"/api/invoices/{body['id']}").json() == {"deleted": True}
    assert client.delete(f"/api/invoices/{body['id']}").status_code == 404


def test_create_and_delete_expense(client: TestClient) -> None:
    created = client.post("/api/expenses", json=EXPENSE)
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert client.get("/api/expenses").json()[0]["merchant"] == "Blue Tokai"
    assert client.delete(f"/api/expenses/{record_id}").status_code == 200
    assert client.delete(f"/api/expenses/{record_id}").status_code == 404


def test_invalid_payload_returns_422(client: TestClient) -> None:
    bad = {**INVOICE, "vendor": "", "items": []}
    assert client.post("/api/invoices", json=bad).status_code == 422
    assert client.post("/api/expenses", json={**EXPENSE, "amount": -5}).status_code == 422


def test_scan_json_uses_offline_parser(client: TestClient) -> None:
    response = client.post("/api/scan", json={"filename": "receipt.txt", "text": SAMPLE})
    assert response.status_code == 200
    body = response.json()
    assert body["merchant"] == "Blue Tokai"
    assert body["total"] == "1062.00"
    assert body["tax"] == "162.00"
    assert body["engine"] == "heuristic"
    assert len(body["items"]) == 1


def test_scan_text_form(client: TestClient) -> None:
    response = client.post("/api/scan", data={"text": SAMPLE, "filename": "receipt.txt"})
    assert response.status_code == 200
    assert response.json()["purchase_date"] == "2026-04-12"


def test_scan_uploaded_txt_file(client: TestClient) -> None:
    response = client.post(
        "/api/scan",
        files={"file": ("cafe.txt", SAMPLE.encode(), "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["merchant"] == "Blue Tokai"


def test_scan_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post("/api/scan", files={"file": ("bad.exe", b"x", "application/octet-stream")})
    assert response.status_code == 400


def test_scan_rejects_oversized_upload(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(api, "get_settings", lambda: replace(settings, max_upload_mb=1))
    response = client.post("/api/scan", files={"file": ("big.txt", b"x" * 1_100_000, "text/plain")})
    assert response.status_code == 413


def test_dates_are_serialized_as_iso(client: TestClient) -> None:
    created = client.post("/api/invoices", json=INVOICE).json()
    assert created["issued_at"] == date(2026, 11, 23).isoformat()
    assert Decimal(created["subtotal"]) == Decimal("200.00")
