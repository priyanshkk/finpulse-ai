# FinPulse AI

Self-hosted invoice and expense tracking with an optional AI receipt scanner.

!!! tip "Try it first"
    Open the [interactive demo](https://priyanshkk.github.io/finpulse-ai/demo/) and click **Continue as Guest**. It is a static preview of the real interface; the full app runs locally through Docker.

## What it does

- Stores invoices with line items, due dates and statuses.
- Records expenses from a form or from a scanned receipt.
- Extracts merchant, date, tax, totals and items from pasted text offline, or from images/PDFs with Gemini.
- Renders cashflow and category charts as inline SVG — no CDN, no tracking.
- Seeds 14 invoices and 18 expenses on first boot so the dashboard is never empty.

## Three-minute start

```bash
git clone https://github.com/priyanshkk/finpulse-ai.git
cd finpulse-ai
cp .env.example .env
docker compose up -d
```

Visit `http://localhost:8000`. Press **Refresh demo data** in the sidebar to re-seed.

## Privacy

`DATABASE_URL` defaults to a SQLite file under `./data`, which is gitignored and mounted into the container. Add `GEMINI_API_KEY` only if you want image/PDF OCR. Without it, text receipts are parsed locally and nothing is sent to an external service.

Continue with [Usage](usage.md) or the [API reference](api.md).
