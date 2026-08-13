"""Packaged ZECT API entry — production uvicorn, no reload, no secret logging."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _prepare_paths() -> None:
    here = Path(__file__).resolve().parent
    src = here / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))
    user_data = (os.getenv("ZECT_USER_DATA") or "").strip()
    if user_data:
        os.environ.setdefault("ZECT_PACKAGED", "1")
        data = Path(user_data) / "data"
        data.mkdir(parents=True, exist_ok=True)
        db = data / "zect.db"
        os.environ.setdefault("DATABASE_URL", f"sqlite:///{db.as_posix()}")


def main() -> None:
    _prepare_paths()
    parser = argparse.ArgumentParser(prog="zect-api")
    parser.add_argument("--host", default=os.getenv("ZECT_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ZECT_API_PORT", "8000")))
    args = parser.parse_args()
    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
