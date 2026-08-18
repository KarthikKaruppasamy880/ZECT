"""Database URL helpers with no engine/connection side effects."""


def is_postgres_url(url: str) -> bool:
    scheme = (url or "").strip().lower().split(":", 1)[0]
    return scheme.startswith("postgres")


def normalize_database_url(url: str) -> str:
    raw = (url or "").strip()
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+psycopg://", 1)
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw
