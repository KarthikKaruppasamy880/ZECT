"""Desktop automation readiness — reports Electron/bridge state (no new automation stack)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def build_desktop_readiness() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    queue = root / "backend" / "data" / "desktop_bridge_queue.json"
    computer_js = root / "electron" / "computer.js"
    main_js = root / "electron" / "main.js"
    return {
        "ok": True,
        "electron_main_present": main_js.is_file(),
        "computer_module_present": computer_js.is_file(),
        "bridge_queue_present": queue.is_file(),
        "bridge_queue_path": str(queue) if queue.is_file() else None,
        "desktop_mode_env": (os.getenv("ZECT_DESKTOP_MODE") or os.getenv("MENTRIX_DESKTOP") or "").strip() or None,
        "capabilities": [
            "desktop_screenshot",
            "desktop_write_note",
            "open_app",
            "companion_computer_mode",
        ],
        "note": "Uses existing Electron Computer Mode / companion tools — not a parallel desktop agent.",
    }
