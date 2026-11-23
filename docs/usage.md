# Usage

## Dashboard

The overview page shows four KPIs — total invoiced, total expenses, net cashflow and outstanding amount — followed by a six-month cashflow chart and a spend-by-category chart. Every number comes from the database on each request.

## Invoices

Invoices are numbered `INV-YEAR-NNNN` automatically. Create them through the JSON API with `POST /api/invoices`. `subtotal` is the sum of `quantity × unit_price`, `total` adds tax, and `due_at` is never earlier than the issue date plus one day. Status is one of `paid`, `pending` or `overdue`.

## Scanning receipts

Open `/scan` in the browser. Paste the receipt text (a `.txt` file also works) and submit. The offline parser looks for a merchant on the first line, an ISO or `DD/MM/YYYY` date, `TOTAL` and `GST`/`tax` lines, and lines shaped like `Coffee beans 2 x 450.00`.

Review the extracted fields, then press **Save as expense**. Nothing is persisted until you confirm.

For image or PDF OCR, set a real key in `.env`:

```bash
GEMINI_API_KEY=your_real_key
GEMINI_MODEL=gemini-2.0-flash
```

The service posts to Gemini's `generateContent` endpoint with `responseMimeType=application/json`. If the key is a placeholder, missing, or the request fails, it silently falls back to the offline parser and reports the engine on screen.

## Demo data

`SEED_ON_START=1` seeds once. Run `POST /api/seed` or click **Refresh demo data** any time; the operation is idempotent. Set `SEED_ON_START=0` for a clean database.

## Running from source

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
set PYTHONPATH=src             # macOS/Linux: export PYTHONPATH=src
python -m uvicorn finpulse_ai.main:app --reload
```
