# ZECT Backend

FastAPI backend for ZECT (Engineering Delivery Control Tower).

## Quick Start

```bash
pip install -e ".[test]"
cp .env.example .env  # edit with your API keys
uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
python -m pytest tests/ -v
```

## Lint

```bash
ruff check app/ tests/
```
