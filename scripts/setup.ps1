$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}
$python = ".venv\Scripts\python.exe"
& $python -m pip install --disable-pip-version-check -q -r requirements-dev.txt

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$env:PYTHONPATH = "src"
$env:DATABASE_URL = "sqlite:///:memory:"
$env:SEED_ON_START = "0"
Write-Host "Running checks..."
& $python -m pytest
& $python -m ruff check .
& $python -m mypy src/finpulse_ai
Write-Host "Done. Run: .\.venv\Scripts\activate then python -m uvicorn finpulse_ai.main:app --reload"
