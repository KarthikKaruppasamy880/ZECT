"""One-off: print database connection details (run from backend/)."""
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.infrastructure.database import engine, DATABASE_URL  # noqa: E402


def mask_url(u: str) -> str:
    if "@" not in u or "://" not in u:
        return u
    scheme, rest = u.split("://", 1)
    if "@" not in rest:
        return u
    creds, hostpart = rest.rsplit("@", 1)
    if ":" in creds:
        user, _pw = creds.split(":", 1)
        return f"{scheme}://{user}:****@{hostpart}"
    return u


print("Configured DATABASE_URL (password masked):", mask_url(DATABASE_URL))
print()

with engine.connect() as conn:
    ver = conn.execute(text("SELECT version()")).scalar_one()
    print("PostgreSQL:", ver.split(",")[0])
    dbn = conn.execute(text("SELECT current_database()")).scalar_one()
    print("Connected database:", dbn)
    print()
    rows = conn.execute(
        text(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
            """
        )
    ).fetchall()
    names = [r[0] for r in rows]
    print("Tables (public):", ", ".join(names) if names else "(none)")
    print()
    for tname in ["projects", "repos", "settings", "token_logs"]:
        if tname not in names:
            print(f"  {tname}: (missing)")
            continue
        n = conn.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar_one()
        print(f"  {tname}: {n} row(s)")

print()
print("OK: SQLAlchemy engine connected successfully.")
