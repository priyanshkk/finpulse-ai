"""Receipt data extraction.

Uses the Gemini API when ``GEMINI_API_KEY`` is configured, otherwise a
deterministic regex parser keeps the whole app usable offline. No API key is
ever stored in code or in the database.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx

from ..schemas import ScannedItem, ScanResult

ALLOWED_EXTENSIONS = frozenset({".txt", ".png", ".jpg", ".jpeg", ".webp", ".pdf"})
_MONEY = re.compile(r"[-+]?\d[\d,]*\.?\d{0,2}")
_ISO_DATE = re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
_DMY_DATE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b")
_ITEM = re.compile(r"^(.{2,60}?)\s{1,}(\d{1,4})\s*[xX×*]\s*([\d,]+\.\d{2}|\d+)\s*$")
_CURRENCY = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}

_JSON_PROMPT = """Extract receipt fields and return ONLY valid JSON with keys:
merchant (string), purchase_date (YYYY-MM-DD or null), total (number or null),
tax (number or null), currency (ISO 4217 code), items (array of objects with
description, quantity, amount), confidence (number 0-1).
Do not guess values that are absent; use null. Receipt text follows:
---
{text}
---"""


def safe_filename(filename: str) -> str:
    """Return a bare, length-limited filename or raise for unsupported types."""
    name = Path(filename.replace("\\", "/")).name
    if len(name) > 120:
        suffix = Path(name).suffix
        name = name[: 120 - len(suffix)] + suffix
    if not name or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type. Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    return name


def parse_amount(value: str) -> Decimal | None:
    """Parse the first money-like number in ``value``."""
    match = _MONEY.search(value.replace("₹", "").replace("$", ""))
    if not match:
        return None
    try:
        return Decimal(match.group().replace(",", ""))
    except InvalidOperation:
        return None


def _last_amount(value: str) -> Decimal | None:
    """Parse the last money-like number on a labelled total/tax line."""
    matches = _MONEY.finditer(value.replace("₹", "").replace("$", ""))
    amounts: list[Decimal] = []
    for match in matches:
        try:
            amounts.append(Decimal(match.group().replace(",", "")))
        except InvalidOperation:
            continue
    return amounts[-1] if amounts else None


def _parse_date(text: str) -> date | None:
    match = _ISO_DATE.search(text)
    if match:
        year, month, day = (int(part) for part in match.groups())
    else:
        match = _DMY_DATE.search(text)
        if not match:
            return None
        first, second, year = (int(part) for part in match.groups())
        if year < 100:
            year += 2000 if year < 70 else 1900
        # Ambiguous dates default to day-first, the common format on Indian receipts.
        day, month = (first, second) if second <= 12 or first > 12 else (second, first)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _heuristic_extract(text: str, filename: str) -> ScanResult:
    """Extract common receipt fields without any external service."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    merchant = lines[0][:160] if lines else Path(filename).stem[:160] or "Unknown merchant"

    total: Decimal | None = None
    tax: Decimal | None = None
    for line in reversed(lines):
        lowered = line.lower()
        if total is None and any(
            word in lowered for word in ("grand total", "total", "amount due", "net payable")
        ):
            total = _last_amount(line)
        if tax is None and any(word in lowered for word in ("gst", "tax", "vat", "cgst", "sgst")):
            tax = _last_amount(line)
    if total is None:
        numbers = [parse_amount(line) for line in lines]
        total = next((number for number in reversed(numbers) if number is not None), None)

    currency = "INR"
    for symbol, code in _CURRENCY.items():
        if symbol in text:
            currency = code
            break
    else:
        found = re.search(r"\b(INR|USD|EUR|GBP)\b", text, re.IGNORECASE)
        if found:
            currency = found.group().upper()

    items: list[ScannedItem] = []
    for line in lines[1:]:
        match = _ITEM.match(line)
        if match:
            description, quantity, amount = match.groups()
            items.append(
                ScannedItem(
                    description=description.strip()[:240],
                    quantity=Decimal(quantity),
                    amount=Decimal(amount.replace(",", "")),
                )
            )

    return ScanResult(
        merchant=merchant,
        purchase_date=_parse_date(text),
        total=total,
        tax=tax,
        currency=currency,
        items=items[:20],
        confidence=0.55 if lines else 0.0,
        engine="heuristic",
        note="Offline parser. Add GEMINI_API_KEY for image and PDF extraction.",
    )


def _clean_json(raw: str) -> str:
    """Strip optional Markdown fences around a JSON payload."""
    value = raw.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    return value


def _gemini_extract(text: str, api_key: str, model: str) -> ScanResult:
    """Call Gemini's generateContent endpoint and validate its JSON response."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": _JSON_PROMPT.format(text=text[:12000])}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    response = httpx.post(url, json=payload, timeout=25.0)
    response.raise_for_status()
    body = response.json()
    raw = body["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(_clean_json(raw))

    items: list[ScannedItem] = []
    for entry in data.get("items") or []:
        try:
            items.append(
                ScannedItem(
                    description=str(entry.get("description", "Item"))[:240],
                    quantity=Decimal(str(entry.get("quantity", 1))),
                    amount=Decimal(str(entry.get("amount", 0))),
                )
            )
        except (InvalidOperation, TypeError, ValueError):
            continue

    purchase_date = None
    if data.get("purchase_date"):
        try:
            purchase_date = date.fromisoformat(str(data["purchase_date"])[:10])
        except ValueError:
            purchase_date = None

    return ScanResult(
        merchant=str(data.get("merchant") or "Unknown merchant")[:160],
        purchase_date=purchase_date,
        total=parse_amount(str(data.get("total") or "")),
        tax=parse_amount(str(data.get("tax") or "")),
        currency=str(data.get("currency") or "INR")[:8].upper(),
        items=items[:20],
        confidence=float(data.get("confidence") or 0.85),
        engine=f"gemini:{model}",
        note="Extracted with Gemini API.",
    )


def scan_receipt(
    *,
    filename: str,
    text: str = "",
    api_key: str = "",
    model: str = "gemini-2.0-flash",
) -> ScanResult:
    """Extract structured fields from a receipt.

    Falls back to the offline parser if Gemini is unconfigured or unavailable,
    so the application never fails just because an AI provider is down.
    """
    name = safe_filename(filename)
    if api_key and api_key not in {"your_key_here", "changeme"} and text.strip():
        try:
            return _gemini_extract(text, api_key, model)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            result = _heuristic_extract(text, name)
            result.engine = "heuristic"
            result.note = f"Gemini unavailable ({type(exc).__name__}); used offline parser."
            return result
    result = _heuristic_extract(text, name)
    if not text.strip() and Path(name).suffix.lower() != ".txt":
        result.note = "Image/PDF OCR requires GEMINI_API_KEY. Text receipts work offline."
    return result


def text_from_bytes(data: bytes, filename: str) -> str:
    """Decode a plain-text receipt; binary files need the AI provider."""
    if Path(filename).suffix.lower() == ".txt":
        return data.decode("utf-8", errors="replace")
    return ""
