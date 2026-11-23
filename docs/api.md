# API reference

Interactive OpenAPI docs are served at `/docs` and the schema at `/openapi.json` when the app is running.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Readiness probe returning status and version |
| `GET` | `/api/dashboard` | KPIs, monthly series, category slices, recent records |
| `GET` | `/api/invoices` | Newest 100 invoices |
| `POST` | `/api/invoices` | Create an invoice with line items |
| `DELETE` | `/api/invoices/{id}` | Delete one invoice |
| `GET` | `/api/expenses` | Newest 100 expenses |
| `POST` | `/api/expenses` | Create an expense |
| `DELETE` | `/api/expenses/{id}` | Delete one expense |
| `POST` | `/api/scan` | Extract fields from `text`, JSON, or an uploaded `file` |
| `POST` | `/api/seed` | Insert demo data once |

## Create an expense

```bash
curl -X POST http://localhost:8000/api/expenses \
  -H 'Content-Type: application/json' \
  -d '{"merchant":"Blue Tokai","category":"Meals","spent_at":"2026-11-23","amount":1062.00,"tax":162.00}'
```

## Scan pasted text

```bash
curl -X POST http://localhost:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{"filename":"receipt.txt","text":"Blue Tokai\n12/04/2026\nCoffee beans 2 x 450.00\nGST 18% 162.00\nTOTAL 1,062.00"}'
```

The response contains `merchant`, `purchase_date`, `total`, `tax`, `currency`, `items`, `confidence`, `engine` and `note`. Validation errors return standard FastAPI 422 payloads; oversized uploads return 413; missing records return 404.

All amounts use `Decimal` in Python and numeric strings in JSON, so rounding never depends on binary floats.
