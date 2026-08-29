"""Desktop automation readiness — reports Electron/bridge/packaging state."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _main_js_has_single_instance(main_js: Path) -> bool:
    if not main_js.is_file():
        return False
    try:
        text = main_js.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "requestSingleInstanceLock" in text


def _backend_dir(root: Path) -> Path:
    return root / "electron" / "resources" / "backend"


def _detect_backend_launcher(root: Path) -> bool:
    return (_backend_dir(root) / "run-api.ps1").is_file()


def _detect_backend_runtime(root: Path) -> bool:
    resources = _backend_dir(root)
    candidates = [
        resources / "zect-api.exe",
        resources / "python-runtime" / "python.exe",
        resources / "python-runtime" / "Scripts" / "python.exe",
        resources / "python-runtime" / "bin" / "python",
    ]
    return any(p.is_file() for p in candidates)


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

    launcher = _detect_backend_launcher(root)
    runtime = _detect_backend_runtime(root)
    backend_bundled = runtime
    # Runtime in the source/build tree is not clean-machine NSIS proof.
    packaging_status = "PARTIAL"
    single_instance = _main_js_has_single_instance(main_js)
    blockers = []
    if not runtime:
        blockers.append("backend_runtime_not_in_source_tree")
    blockers.append("clean_machine_nsis_unproven")
    if not launcher:
        blockers.append("backend_launcher_missing")
    if not lifecycle_js.is_file():
        blockers.append("service_lifecycle_module_missing")
    if not single_instance:
        blockers.append("single_instance_lock_missing")

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
        "single_instance_lock": single_instance,
        "canonical_api_port": 8000,
        "packaging": {
            "status": packaging_status,
            "backend_bundled": backend_bundled,
            "backend_launcher_present": launcher,
            "backend_runtime_present": runtime,
            "nsis_configured": True,
            "managed_lifecycle": lifecycle_js.is_file(),
            "single_instance": single_instance,
            "user_data_dirs": ["logs", "config", "data"],
            "classification": {
                "electron": "PACKAGED",
                "frontend": "PACKAGED",
                "backend": "PACKAGED" if runtime else "MANAGED_EXTERNAL",
                "storage_database": "PACKAGED",
                "database_mode": (
                    "server_postgres"
                    if (os.getenv("DATABASE_URL") or "").strip().lower().startswith("postgres")
                    else "desktop_sqlite"
                ),
                "voicebox": "OPTIONAL",
                "presentation_provider": "OPTIONAL",
                "local_model_runtime": "NOT_REQUIRED",
                "helpers": "MANAGED_EXTERNAL",
            },
            "target_flow": [
                "Install ZECT",
                "Launch ZECT",
                "required local services managed automatically",
                "ZECT ready",
            ],
            "blockers": blockers,
            "note": (
                "NSIS/portable targets + sidecar launcher (run-api.ps1) ship in-tree. "
                "python-runtime / zect-api.exe are produced by backend/packaging/bundle_sidecar.py "
                "at installer build time (gitignored). Voicebox and Presenton remain OPTIONAL external. "
                "Clean-machine NSIS install is a separate gate — never claim PASS without that proof."
            ),
        },
        "capabilities": [
            "desktop_screenshot",
            "desktop_write_note",
            "open_app",
            "companion_computer_mode",
            "service_health_probe",
            "single_instance_lock",
            "backend_sidecar_launch",
        ],
        "note": "Uses existing Electron Computer Mode / companion tools — not a parallel desktop agent.",
    }
