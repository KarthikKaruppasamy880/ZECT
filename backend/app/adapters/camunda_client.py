"""Mentrix Process — Camunda REST adapter (product brand: Mentrix Process).

Engine product name belongs in THIRD_PARTY_NOTICES only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

PROVIDER = "mentrix_process"


def _base_url() -> str:
    return (os.getenv("ZECT_CAMUNDA_BASE_URL") or "").strip().rstrip("/")


def _auth() -> tuple[str, str] | None:
    user = (os.getenv("ZECT_CAMUNDA_USER") or "").strip()
    password = (os.getenv("ZECT_CAMUNDA_PASSWORD") or "").strip()
    if user or password:
        return user, password
    return None


def process_engine_status() -> dict[str, Any]:
    base = _base_url()
    if not base:
        return {
            "provider": PROVIDER,
            "label": "Mentrix Process",
            "ready": False,
            "status": "degraded",
            "detail": "ZECT_CAMUNDA_BASE_URL unset",
            "cockpit_url": (os.getenv("ZECT_CAMUNDA_COCKPIT_URL") or "").strip(),
        }
    try:
        with httpx.Client(timeout=10.0, auth=_auth()) as client:
            # Engine version endpoint (Camunda 7 REST)
            r = client.get(f"{base}/version")
            if r.status_code >= 400:
                r = client.get(f"{base}/engine")
            ok = r.status_code < 400
            return {
                "provider": PROVIDER,
                "label": "Mentrix Process",
                "ready": ok,
                "status": "ready" if ok else "degraded",
                "detail": f"http_{r.status_code}",
                "base_url": base,
                "cockpit_url": (os.getenv("ZECT_CAMUNDA_COCKPIT_URL") or "").strip(),
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": PROVIDER,
            "label": "Mentrix Process",
            "ready": False,
            "status": "degraded",
            "detail": str(exc)[:300],
            "base_url": base,
            "cockpit_url": (os.getenv("ZECT_CAMUNDA_COCKPIT_URL") or "").strip(),
        }


def deploy_bpmn(*, file_path: str | None = None, content: bytes | None = None, name: str = "process.bpmn") -> dict[str, Any]:
    base = _base_url()
    if not base:
        return {"ok": False, "error": "camunda_not_configured", "provider": PROVIDER}
    data = content
    filename = name
    if file_path:
        p = Path(file_path)
        data = p.read_bytes()
        filename = p.name
    if not data:
        return {"ok": False, "error": "bpmn_required", "provider": PROVIDER}
    with httpx.Client(timeout=60.0, auth=_auth()) as client:
        files = {"data": (filename, data, "application/xml")}
        r = client.post(f"{base}/deployment/create", data={"deployment-name": filename}, files=files)
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:500], "status_code": r.status_code, "provider": PROVIDER}
        body = r.json() if r.content else {}
        return {"ok": True, "provider": PROVIDER, "deployment": body}


def start_process(process_key: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    base = _base_url()
    if not base:
        return {"ok": False, "error": "camunda_not_configured", "provider": PROVIDER}
    payload: dict[str, Any] = {}
    if variables:
        # Camunda variable map: { name: { value, type } }
        mapped = {}
        for k, v in variables.items():
            t = "String"
            if isinstance(v, bool):
                t = "Boolean"
            elif isinstance(v, int):
                t = "Integer"
            elif isinstance(v, float):
                t = "Double"
            mapped[k] = {"value": v, "type": t}
        payload["variables"] = mapped
    with httpx.Client(timeout=30.0, auth=_auth()) as client:
        r = client.post(f"{base}/process-definition/key/{process_key}/start", json=payload)
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:500], "status_code": r.status_code, "provider": PROVIDER}
        return {"ok": True, "provider": PROVIDER, "instance": r.json() if r.content else {}}


def list_incidents(*, max_results: int = 50) -> dict[str, Any]:
    base = _base_url()
    if not base:
        return {"ok": False, "error": "camunda_not_configured", "provider": PROVIDER, "items": []}
    with httpx.Client(timeout=30.0, auth=_auth()) as client:
        r = client.get(f"{base}/incident", params={"maxResults": max_results})
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:500], "status_code": r.status_code, "provider": PROVIDER, "items": []}
        items = r.json() if r.content else []
        return {"ok": True, "provider": PROVIDER, "items": items if isinstance(items, list) else [items]}
