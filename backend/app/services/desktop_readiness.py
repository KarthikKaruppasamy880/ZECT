"""Desktop automation readiness — reports Electron/bridge/packaging state."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def build_desktop_readiness() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    queue = root / "backend" / "data" / "desktop_bridge_queue.json"
    computer_js = root / "electron" / "computer.js"
    main_js = root / "electron" / "main.js"
    lifecycle_js = root / "electron" / "service-lifecycle.js"
    package_json = root / "electron" / "package.json"
    win_install_doc = root / "docs" / "WINDOWS_INSTALL.md"
    start_local = root / "scripts" / "start-local.ps1"
    if not start_local.is_file():
        start_local = root / "start-local.ps1"

    backend_bundled = False  # intentional honesty — API not inside NSIS yet
    packaging_status = "PARTIAL"
    blockers = []
    if not backend_bundled:
        blockers.append("backend_not_bundled_in_installer")
    if not lifecycle_js.is_file():
        blockers.append("service_lifecycle_module_missing")

    return {
        "ok": True,
        "electron_main_present": main_js.is_file(),
        "computer_module_present": computer_js.is_file(),
        "service_lifecycle_present": lifecycle_js.is_file(),
        "electron_builder_config_present": package_json.is_file(),
        "windows_install_doc_present": win_install_doc.is_file(),
        "start_local_script_present": start_local.is_file(),
        "bridge_queue_present": queue.is_file(),
        "bridge_queue_path": str(queue) if queue.is_file() else None,
        "desktop_mode_env": (os.getenv("ZECT_DESKTOP_MODE") or os.getenv("MENTRIX_DESKTOP") or "").strip() or None,
        "packaging": {
            "status": packaging_status,
            "backend_bundled": backend_bundled,
            "nsis_configured": True,
            "managed_lifecycle": lifecycle_js.is_file(),
            "target_flow": [
                "Install ZECT",
                "Launch ZECT",
                "required local services managed automatically",
                "ZECT ready",
            ],
            "blockers": blockers,
            "note": (
                "Windows NSIS/portable targets exist; ordinary users still need a running API "
                "(:8000) and optional Voicebox/Presenton. service-lifecycle can probe/start "
                "dev services when ZECT_MANAGE_SERVICES=1 — not a full one-click appliance yet."
            ),
        },
        "capabilities": [
            "desktop_screenshot",
            "desktop_write_note",
            "open_app",
            "companion_computer_mode",
            "service_health_probe",
        ],
        "note": "Uses existing Electron Computer Mode / companion tools — not a parallel desktop agent.",
    }
