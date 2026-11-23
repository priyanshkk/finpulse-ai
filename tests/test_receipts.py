"""Receipt parsing, Gemini response validation and graceful fallback."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest

from finpulse_ai.schemas import ScannedItem
from finpulse_ai.services import receipts

SAMPLE = """Blue Tokai
12/04/2026
Coffee beans      2 x 450.00
Notebook          1 x 250.00
GST 18%           126.00
TOTAL             1,276.00
"""


class FakeResponse:
    """Minimal stand-in for an httpx response."""

    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


def gemini_payload(raw: str) -> FakeResponse:
    return FakeResponse({"candidates": [{"content": {"parts": [{"text": raw}]}}]})


def test_parse_amount_handles_symbols_and_commas() -> None:
    assert receipts.parse_amount("₹1,276.00") == Decimal("1276.00")
    assert receipts.parse_amount("total: $42.50") == Decimal("42.50")
    assert receipts.parse_amount("nothing here") is None


@pytest.mark.parametrize("bad", ["../../etc/passwd.exe", "receipt.zip", ""])
def test_safe_filename_rejects_unsupported(bad: str) -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        receipts.safe_filename(bad)


def test_safe_filename_strips_directories_and_truncates() -> None:
    assert receipts.safe_filename("C:\\tmp\\scan.txt") == "scan.txt"
    assert len(receipts.safe_filename("a" * 300 + ".txt")) == 120


def test_heuristic_extract_reads_all_fields() -> None:
    result = receipts.scan_receipt(filename="receipt.txt", text=SAMPLE)
    assert result.engine == "heuristic"
    assert result.merchant == "Blue Tokai"
    assert result.purchase_date == date(2026, 4, 12)
    assert result.total == Decimal("1276.00")
    assert result.tax == Decimal("126.00")
    assert result.currency == "INR"
    assert result.items == [
        ScannedItem(description="Coffee beans", quantity=Decimal("2"), amount=Decimal("450.00")),
        ScannedItem(description="Notebook", quantity=Decimal("1"), amount=Decimal("250.00")),
    ]
    assert 0 < result.confidence <= 1


def test_heuristic_extract_handles_iso_date_and_usd() -> None:
    result = receipts.scan_receipt(filename="x.txt", text="Shop\n2026-11-23\nTOTAL 12.99 USD\n")
    assert result.purchase_date == date(2026, 11, 23)
    assert result.currency == "USD"
    assert result.total == Decimal("12.99")


def test_gemini_extract_validates_json(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = """```json
    {"merchant":"Gemini Cafe","purchase_date":"2026-10-05","total":321.5,
     "tax":21.5,"currency":"eur","items":[{"description":"Tea","quantity":2,"amount":160}],
     "confidence":0.93}
    ```"""
    monkeypatch.setattr(receipts.httpx, "post", lambda *a, **k: gemini_payload(raw))
    result = receipts.scan_receipt(filename="receipt.png", text="image text", api_key="real-key")
    assert result.engine == "gemini:gemini-2.0-flash"
    assert result.merchant == "Gemini Cafe"
    assert result.purchase_date == date(2026, 10, 5)
    assert result.total == Decimal("321.5")
    assert result.currency == "EUR"
    assert result.items[0].description == "Tea"
    assert result.confidence == pytest.approx(0.93)


def test_gemini_http_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(receipts.httpx, "post", boom)
    result = receipts.scan_receipt(filename="receipt.txt", text=SAMPLE, api_key="real-key")
    assert result.engine == "heuristic"
    assert "Gemini unavailable" in result.note
    assert result.total == Decimal("1276.00")


def test_gemini_bad_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(receipts.httpx, "post", lambda *a, **k: gemini_payload("not json"))
    result = receipts.scan_receipt(filename="receipt.txt", text=SAMPLE, api_key="real-key")
    assert result.engine == "heuristic"
    assert "JSONDecodeError" in result.note


def test_placeholder_key_never_calls_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network must not be used with a placeholder key")

    monkeypatch.setattr(receipts.httpx, "post", forbidden)
    result = receipts.scan_receipt(filename="receipt.txt", text=SAMPLE, api_key="your_key_here")
    assert result.engine == "heuristic"


def test_text_from_bytes_only_decodes_plain_text() -> None:
    assert receipts.text_from_bytes(b"hello\n", "a.txt") == "hello\n"
    assert receipts.text_from_bytes(b"\x89PNG", "a.png") == ""


def test_binary_without_key_explains_ocr_requirement() -> None:
    result = receipts.scan_receipt(filename="photo.jpg", text="")
    assert "GEMINI_API_KEY" in result.note
    assert result.merchant == "photo"
