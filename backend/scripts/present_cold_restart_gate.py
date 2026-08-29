"""Cold backend restart gate: verify persisted Zinnia deck survives API stop/start.

Acceptance harness only — does not modify Present product code.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
load_dotenv(BACKEND / ".env", override=True)
sys.path.insert(0, str(BACKEND))

ART = REPO / "test-results" / "present-product-ready"


def _health_ok(api_url: str) -> bool:
    base = api_url.rstrip("/")
    for path in ("/healthz", "/health", "/api/health"):
        try:
            with urllib.request.urlopen(f"{base}{path}", timeout=4) as resp:
                return 200 <= resp.status < 500
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    return False


def _wait_health(api_url: str, *, seconds: float = 90.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if _health_ok(api_url):
            return True
        time.sleep(1.5)
    return False


def _deck_has_marker(deck_path: Path, marker: str) -> bool:
    from app.services.pptx_parse import parse_pptx_bytes

    if not deck_path.is_file():
        return False
    slides = parse_pptx_bytes(deck_path.read_bytes())
    blob = json.dumps(slides, sort_keys=True)
    if marker in blob or marker.lower() in blob.lower():
        return True
    for slide in slides:
        if isinstance(slide, dict) and marker in str(slide.get("notes") or ""):
            return True
    return False


def _kill_uvicorn_on_port(port: int) -> None:
    if os.name != "nt":
        raise RuntimeError("cold restart gate is Windows-only in this harness")
    ps = f"""
$port = {port}
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {{
  cmd /c "taskkill /F /PID $($c.OwningProcess) /T" | Out-Null
}}
Get-CimInstance Win32_Process | Where-Object {{
  $_.CommandLine -and $_.CommandLine -match 'uvicorn app\\.main:app' -and $_.CommandLine -match ':{port}'
}} | ForEach-Object {{ cmd /c "taskkill /F /PID $($_.ProcessId) /T" | Out-Null }}
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        cwd=str(REPO),
        check=False,
        capture_output=True,
        text=True,
    )
    time.sleep(2)


def _start_uvicorn(port: int) -> subprocess.Popen[Any]:
    py = os.environ.get("ZECT_PYTHON") or sys.executable
    log = ART / "cold-restart-uvicorn.log"
    ART.mkdir(parents=True, exist_ok=True)
    log_handle = log.open("a", encoding="utf-8")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.Popen(
        [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", f"--port", str(port)],
        cwd=str(BACKEND),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )


def run_gate(*, api_url: str, deck_path: Path, marker: str, do_restart: bool) -> dict[str, Any]:
    from app.services.mentrix.presentation.document_io import validate_export_document

    parsed = urllib.parse.urlparse(api_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 8000)
    evidence: dict[str, Any] = {
        "api_url": api_url,
        "deck_path": str(deck_path),
        "marker": marker,
        "pre_restart_health": _health_ok(api_url),
        "pre_restart_marker_ok": _deck_has_marker(deck_path, marker),
    }
    if not evidence["pre_restart_marker_ok"]:
        evidence["verdict"] = False
        evidence["error"] = "marker_missing_before_restart"
        return evidence

    if do_restart:
        _kill_uvicorn_on_port(port)
        evidence["mid_health"] = _health_ok(api_url)
        proc = _start_uvicorn(port)
        evidence["restart_pid"] = proc.pid
        evidence["post_restart_health"] = _wait_health(api_url)
        if not evidence["post_restart_health"]:
            evidence["verdict"] = False
            evidence["error"] = "api_health_timeout_after_restart"
            return evidence
    else:
        evidence["post_restart_health"] = evidence["pre_restart_health"]

    evidence["post_restart_marker_ok"] = _deck_has_marker(deck_path, marker)
    export_val = validate_export_document(deck_path, expected_slides=None)
    evidence["export_validate"] = export_val
    evidence["verdict"] = (
        evidence["post_restart_marker_ok"]
        and bool(export_val.get("ok"))
        and (evidence["post_restart_health"] if do_restart else True)
    )
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=os.environ.get("ZECT_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--deck-path", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    out = run_gate(api_url=args.api_url, deck_path=Path(args.deck_path), marker=args.marker, do_restart=args.restart)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "cold-restart-gate.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "export_validate"}, indent=2))
    return 0 if out.get("verdict") else 1


if __name__ == "__main__":
    raise SystemExit(main())
