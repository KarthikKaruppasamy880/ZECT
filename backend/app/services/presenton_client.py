"""Thin Presenton self-host client — prompt → PPTX path for Mentrix Present Deck."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx


def presenton_base_url() -> str:
    return (os.getenv("PRESENTON_BASE_URL") or "").strip().rstrip("/")


def presenton_configured() -> bool:
    return bool(presenton_base_url())


def _auth() -> tuple[str, str] | None:
    user = (os.getenv("PRESENTON_USERNAME") or "").strip()
    password = (os.getenv("PRESENTON_PASSWORD") or "").strip()
    if user and password:
        return (user, password)
    return None


def _bearer_headers() -> dict[str, str]:
    key = (os.getenv("PRESENTON_API_KEY") or "").strip()
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}


def _session_headers(client: httpx.Client) -> dict[str, str]:
    """Authenticate Presenton (≥0.9 session cookie or API key; Basic as legacy).

    Fresh self-host builds return 428 setup_required until an admin exists, then
    use cookie sessions for /api/v1/* (HTTP Basic alone often returns 401).
    """
    headers = {**_bearer_headers()}
    if headers.get("Authorization"):
        return headers

    creds = _auth()
    if not creds:
        return headers

    base = presenton_base_url()
    if not base:
        return headers

    try:
        login = client.post(
            f"{base}/api/v1/auth/login",
            json={"username": creds[0], "password": creds[1]},
            headers={"Content-Type": "application/json"},
        )
        if login.status_code < 400:
            cookie = login.cookies.get("presenton_session")
            if cookie:
                headers["Cookie"] = f"presenton_session={cookie}"
                return headers
            data: dict[str, Any] = {}
            try:
                data = login.json()
            except Exception:  # noqa: BLE001
                data = {}
            token = (
                data.get("access_token")
                or data.get("token")
                or data.get("api_key")
                or ""
            )
            if token:
                headers["Authorization"] = f"Bearer {token}"
                return headers
    except Exception:  # noqa: BLE001
        pass

    return headers


def _client_kwargs() -> dict[str, Any]:
    """httpx client options.

    Presenton 0.9+ prefers session cookies from /api/v1/auth/login. Do not attach
    HTTP Basic by default — it returns 401 on /api/v1/* even with correct password
    while cookie sessions succeed.
    """
    return {"timeout": 15.0, "follow_redirects": True}


def _safe_filename(name: str) -> str:
    base = re.sub(r"[^\w.\- ]+", "", (name or "mentrix-deck").strip())[:80] or "mentrix-deck"
    if not base.lower().endswith(".pptx"):
        base = f"{base}.pptx"
    return base


def default_save_dir() -> Path:
    home = Path.home()
    for candidate in (
        home / "Documents",
        home / "OneDrive" / "Documents",
        home / "Desktop",
    ):
        if candidate.is_dir():
            return candidate
    return home


# Presenton built-in template names (docs.presenton.ai).
BUILTIN_TEMPLATES: list[dict[str, str]] = [
    {"id": "general", "name": "General"},
    {"id": "modern", "name": "Modern"},
    {"id": "standard", "name": "Standard"},
    {"id": "swift", "name": "Swift"},
]


def _normalize_template_rows(raw: Any) -> list[dict[str, str]]:
    """Map Presenton template payloads to {id, name}."""
    rows: list[Any]
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("templates") or raw.get("items") or raw.get("data") or []
        if not isinstance(rows, list):
            rows = []
    else:
        rows = []

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in rows:
        if isinstance(item, str):
            tid = item.strip()
            if not tid or tid in seen:
                continue
            seen.add(tid)
            out.append({"id": tid, "name": tid.replace("-", " ").replace("_", " ").title()})
            continue
        if not isinstance(item, dict):
            continue
        tid = str(
            item.get("id")
            or item.get("name")
            or item.get("template")
            or item.get("template_name")
            or ""
        ).strip()
        if not tid or tid in seen:
            continue
        seen.add(tid)
        label = str(item.get("title") or item.get("display_name") or item.get("name") or tid).strip()
        out.append({"id": tid, "name": label or tid})
    return out


def list_templates() -> dict[str, Any]:
    """List Presenton templates; fall back to built-ins when unset/unreachable."""
    base = presenton_base_url()
    if not base:
        return {
            "ok": True,
            "source": "builtin",
            "templates": list(BUILTIN_TEMPLATES),
            "reachable": False,
            "configured": False,
            "hint": "Set PRESENTON_BASE_URL and run Presenton Docker to load remote templates",
        }

    url = f"{base}/api/v1/ppt/template/all"
    try:
        with httpx.Client(**_client_kwargs()) as client:
            headers = _session_headers(client)
            res = client.get(url, params={"include_defaults": "true"}, headers=headers)
            if res.status_code in (401, 403, 428):
                detail = (res.text or "")[:400]
                setup = "setup_required" in detail or res.status_code == 428
                return {
                    "ok": True,
                    "source": "builtin",
                    "templates": list(BUILTIN_TEMPLATES),
                    "reachable": False,
                    "configured": True,
                    "hint": (
                        "Presenton requires admin setup / auth "
                        "(set PRESENTON_USERNAME+PASSWORD or PRESENTON_API_KEY; open Presenton UI once)"
                        if setup or res.status_code in (401, 403)
                        else f"Presenton templates HTTP {res.status_code}"
                    ),
                    "detail": detail,
                    "blocked_external": True,
                    "block_code": "presenton_auth_or_setup",
                }
            if res.status_code >= 400:
                return {
                    "ok": True,
                    "source": "builtin",
                    "templates": list(BUILTIN_TEMPLATES),
                    "reachable": False,
                    "configured": True,
                    "hint": f"Presenton templates HTTP {res.status_code} — using built-ins",
                    "detail": (res.text or "")[:400],
                }
            mapped = _normalize_template_rows(res.json())
            if not mapped:
                mapped = list(BUILTIN_TEMPLATES)
            return {
                "ok": True,
                "source": "presenton",
                "templates": mapped,
                "reachable": True,
                "configured": True,
            }
    except httpx.ConnectError:
        return {
            "ok": True,
            "source": "builtin",
            "templates": list(BUILTIN_TEMPLATES),
            "reachable": False,
            "configured": True,
            "hint": f"Cannot reach {base} — start Presenton Docker; showing built-ins",
            "blocked_external": True,
            "block_code": "presenton_unreachable",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": True,
            "source": "builtin",
            "templates": list(BUILTIN_TEMPLATES),
            "reachable": False,
            "configured": True,
            "hint": "Presenton template list failed — using built-ins",
            "detail": str(exc)[:500],
        }


def presenton_reachable() -> bool:
    """True when PRESENTON_BASE_URL is set and template list (or ping) succeeds."""
    if not presenton_configured():
        return False
    result = list_templates()
    return bool(result.get("reachable"))


def resolve_presenton_template_id(
    choice: str | None,
    *,
    custom_id: str | None = None,
    user_id: str | int | None = None,
) -> dict[str, Any]:
    """Map UI template choice to the Presenton template id actually sent on generate.

    Canonical ZECT ids (zinnia-executive-v1, …) resolve through the ZECT template
    registry. Env ZINNIA_PRESENTON_TEMPLATE_ID may seed that registry once; it is
    not a normal-user mapping path. Silently mapping zinnia-* → modern is not a
    Zinnia PASS.
    """
    from app.services.mentrix.presentation import template_registry as tmpl

    raw = (choice or "general").strip() or "general"
    custom = (custom_id or "").strip()
    canon = tmpl.canonical_id(raw) or raw

    if raw == "__custom__" or raw.lower() == "custom":
        tid = custom or "general"
        verified = tmpl.is_verified_provider_id(tid)
        return {
            "template_id": tid,
            "ui_choice": raw,
            "canonical_id": canon,
            "zinnia_verified": verified,
            "mapping_source": "custom" if custom else "none",
            "note": "custom_template_id" if custom else "fallback_general",
            "lifecycle": tmpl.LIFECYCLE_READY if verified else tmpl.LIFECYCLE_TEMPLATE_NOT_READY,
        }

    if canon.startswith("zinnia-") or raw.startswith("zinnia-"):
        if custom and tmpl.is_verified_provider_id(custom):
            return {
                "template_id": custom,
                "ui_choice": raw,
                "canonical_id": canon,
                "zinnia_verified": True,
                "mapping_source": "custom",
                "note": "zinnia_preset_with_custom_master",
                "lifecycle": tmpl.LIFECYCLE_READY,
            }
        mapped = tmpl.get_provider_mapping(canon)
        pid = str((mapped or {}).get("provider_template_id") or "")
        if tmpl.is_verified_provider_id(pid) and str((mapped or {}).get("source") or "") == "registry":
            return {
                "template_id": pid,
                "ui_choice": raw,
                "canonical_id": canon,
                "zinnia_verified": True,
                "mapping_source": "registry",
                "note": "zinnia_registry_mapping",
                "lifecycle": tmpl.LIFECYCLE_READY,
            }
        return {
            "template_id": "modern",
            "ui_choice": raw,
            "canonical_id": canon,
            "zinnia_verified": False,
            "mapping_source": "none",
            "note": "zinnia_unmapped_not_a_master_PASS",
            "lifecycle": tmpl.LIFECYCLE_TEMPLATE_NOT_READY,
        }

    if canon.startswith("org-") or raw.startswith("org-"):
        if custom and tmpl.is_verified_provider_id(custom):
            return {
                "template_id": custom,
                "ui_choice": raw,
                "canonical_id": canon,
                "zinnia_verified": False,
                "mapping_source": "custom",
                "note": "org_with_custom_master",
                "lifecycle": tmpl.LIFECYCLE_READY,
            }
        mapped = tmpl.get_provider_mapping(canon)
        pid = str((mapped or {}).get("provider_template_id") or "")
        if tmpl.is_verified_provider_id(pid):
            return {
                "template_id": pid,
                "ui_choice": raw,
                "canonical_id": canon,
                "zinnia_verified": False,
                "mapping_source": "registry",
                "note": "org_registry_mapping",
                "lifecycle": tmpl.LIFECYCLE_READY,
            }
        upload = tmpl.get_template(user_id or "anon", raw) if user_id is not None else None
        upid = str((upload or {}).get("presenton_template_id") or "")
        if tmpl.is_verified_provider_id(upid):
            return {
                "template_id": upid,
                "ui_choice": raw,
                "canonical_id": canon,
                "zinnia_verified": False,
                "mapping_source": "org_upload",
                "note": "org_uploaded_pptx_bound",
                "lifecycle": tmpl.LIFECYCLE_READY,
            }
        return {
            "template_id": "standard",
            "ui_choice": raw,
            "canonical_id": canon,
            "zinnia_verified": False,
            "mapping_source": "none",
            "note": "org_preset_unmapped",
            "lifecycle": tmpl.LIFECYCLE_TEMPLATE_NOT_READY,
        }

    if raw.startswith("user-"):
        upload = tmpl.get_template(user_id or "anon", raw) if user_id is not None else None
        upid = str((upload or {}).get("presenton_template_id") or "")
        if custom and tmpl.is_verified_provider_id(custom):
            upid = custom
        if tmpl.is_verified_provider_id(upid):
            return {
                "template_id": upid,
                "ui_choice": raw,
                "canonical_id": canon,
                "zinnia_verified": False,
                "mapping_source": "user_upload",
                "note": "user_pptx_bound_to_provider",
                "lifecycle": tmpl.LIFECYCLE_READY,
            }
        return {
            "template_id": "general",
            "ui_choice": raw,
            "canonical_id": canon,
            "zinnia_verified": False,
            "mapping_source": "none",
            "note": "user_pptx_local_only_needs_provider_bind",
            "blocked_external": True,
            "lifecycle": tmpl.LIFECYCLE_TEMPLATE_NOT_READY,
        }

    return {
        "template_id": raw,
        "ui_choice": raw,
        "canonical_id": canon,
        "zinnia_verified": False,
        "mapping_source": "direct",
        "note": "direct_template_id",
        "lifecycle": tmpl.LIFECYCLE_READY,
    }


def generate_presentation(
    content: str,
    *,
    n_slides: int = 6,
    template: str | None = None,
    instructions: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """Call Presenton generate API and download PPTX into Documents/Desktop.

    Bounded cold-start retries on ConnectError / 502 / ReadTimeout (PRESENTON_GENERATE_RETRIES, default 2).
    """
    base = presenton_base_url()
    if not base:
        return {
            "ok": False,
            "error": "presenton_not_configured",
            "hint": "Set PRESENTON_BASE_URL (e.g. http://127.0.0.1:5000) and run Presenton Docker",
            "blocked_external": True,
            "block_code": "presenton_not_configured",
        }
    prompt = (content or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_content"}

    payload: dict[str, Any] = {
        "content": prompt,
        "n_slides": max(3, min(int(n_slides or 6), 20)),
        "language": "English",
        "template": (template or "general").strip() or "general",
        "export_as": "pptx",
    }
    if instructions:
        payload["instructions"] = instructions

    template_sent = str(payload["template"])
    url = f"{base}/api/v1/ppt/presentation/generate"
    try:
        max_attempts = max(1, min(int(os.getenv("PRESENTON_GENERATE_RETRIES", "2") or "2"), 4))
    except ValueError:
        max_attempts = 2
    last_err: dict[str, Any] | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            kwargs = _client_kwargs()
            # Presenton LLM generate + export is often >3m on first run
            kwargs["timeout"] = float(os.getenv("PRESENTON_GENERATE_TIMEOUT", "600") or "600")
            with httpx.Client(**kwargs) as client:
                headers = {"Content-Type": "application/json", **_session_headers(client)}
                res = client.post(url, json=payload, headers=headers)
                if res.status_code in (401, 403, 428):
                    return {
                        "ok": False,
                        "error": "presenton_auth_or_setup",
                        "status": res.status_code,
                        "detail": (res.text or "")[:800],
                        "template_sent": template_sent,
                        "blocked_external": True,
                        "block_code": "presenton_auth_or_setup",
                        "hint": "Presenton auth/setup required — set PRESENTON_USERNAME/PASSWORD and complete admin login",
                        "retries": attempt,
                    }
                if res.status_code in (502, 503, 504) and attempt < max_attempts:
                    last_err = {
                        "ok": False,
                        "error": "presenton_generate_failed",
                        "status": res.status_code,
                        "detail": (res.text or "")[:800],
                        "template_sent": template_sent,
                        "blocked_external": True,
                        "block_code": "presenton_cold_start",
                        "retries": attempt,
                    }
                    time.sleep(min(2.0 * attempt, 6.0))
                    continue
                if res.status_code >= 400:
                    return {
                        "ok": False,
                        "error": "presenton_generate_failed",
                        "status": res.status_code,
                        "detail": (res.text or "")[:800],
                        "template_sent": template_sent,
                        "blocked_external": res.status_code >= 500,
                        "block_code": "presenton_generate_failed",
                        "retries": attempt,
                    }
                data = res.json()
                rel = data.get("path") or data.get("edit_path") or ""
                if not rel:
                    return {
                        "ok": False,
                        "error": "presenton_missing_path",
                        "response": data,
                        "template_sent": template_sent,
                        "retries": attempt,
                    }

                download_url = rel if str(rel).startswith("http") else urljoin(base + "/", str(rel).lstrip("/"))
                file_res = client.get(download_url, headers=_session_headers(client), follow_redirects=True)
                if file_res.status_code >= 400 or not file_res.content:
                    return {
                        "ok": False,
                        "error": "presenton_download_failed",
                        "status": file_res.status_code,
                        "url": download_url,
                        "template_sent": template_sent,
                        "retries": attempt,
                    }

                out_name = _safe_filename(filename or Path(str(rel)).name or "mentrix-deck.pptx")
                out_path = default_save_dir() / out_name
                out_path.write_bytes(file_res.content)
                return {
                    "ok": True,
                    "path": str(out_path.resolve()),
                    "presentation_id": data.get("presentation_id"),
                    "presenton_path": rel,
                    "bytes": len(file_res.content),
                    "template_sent": template_sent,
                    "presenton_request": {"template": template_sent, "n_slides": payload["n_slides"]},
                    "retries": attempt,
                }
        except httpx.ConnectError:
            last_err = {
                "ok": False,
                "error": "presenton_unreachable",
                "hint": f"Cannot reach {base} — start Presenton Docker or fix PRESENTON_BASE_URL",
                "blocked_external": True,
                "block_code": "presenton_unreachable",
                "template_sent": template_sent,
                "retries": attempt,
            }
            if attempt < max_attempts:
                time.sleep(min(1.5 * attempt, 4.0))
                continue
            return last_err
        except httpx.ReadTimeout:
            last_err = {
                "ok": False,
                "error": "presenton_timeout",
                "hint": "Presenton generate timed out — raise PRESENTON_GENERATE_TIMEOUT or retry when warm",
                "blocked_external": True,
                "block_code": "presenton_timeout",
                "template_sent": template_sent,
                "retries": attempt,
            }
            if attempt < max_attempts:
                continue
            return last_err
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": "presenton_error",
                "detail": str(exc)[:500],
                "template_sent": template_sent,
                "retries": attempt,
            }

    return last_err or {
        "ok": False,
        "error": "presenton_failed",
        "template_sent": template_sent,
        "blocked_external": True,
    }
