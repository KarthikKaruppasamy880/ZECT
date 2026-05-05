FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg and weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

COPY . .

# Start server (init_db() on startup handles table creation and auto-migration)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
