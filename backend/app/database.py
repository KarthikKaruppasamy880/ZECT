import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load backend/.env before DATABASE_URL is read (matches main.py; works when importing database alone).
_backend_root = Path(__file__).resolve().parents[1]
load_dotenv(_backend_root / ".env")

# Default to PostgreSQL; fall back to SQLite only if DATABASE_URL is not set
_default_db = "postgresql://postgres:postgres@localhost:5432/zect_db"
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
