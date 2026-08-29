"""Clone real Zinnia master to a stable path for cold-restart acceptance."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))


def main() -> int:
    dest = Path(sys.argv[1]).resolve()
    from app.services.mentrix.presentation.deck_catalog import instantiate_from_template

    src = instantiate_from_template("zinnia-executive-v1")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"{dest} bytes={dest.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
