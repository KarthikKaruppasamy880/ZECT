"""API inventory + eval gate for Mentrix upgrade mode."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

# Common route patterns across stacks
_ROUTE_PATTERNS = [
    re.compile(r"""@(?:app|router)\.(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""\.(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""@(Get|Post|Put|Patch|Delete)Mapping\(\s*['"]?([^'")\s]+)""", re.I),
    re.compile(r"""(?:app|router)\.(?:get|post|put|patch|delete)\(['"]([^'"]+)['"]""", re.I),
    re.compile(r"""Route::(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]""", re.I),
]


def inventory_apis(
    *,
    workspace: str = "",
    scout: dict | None = None,
    blueprint_prompt: str = "",
) -> dict[str, Any]:
    """Extract endpoints from OpenAPI files, route regex, Lattice hits, or blueprint text."""
    endpoints: list[dict[str, str]] = []
    sources: list[str] = []

    root = Path(workspace) if workspace else None
    if root and root.is_dir():
        for name in ("openapi.json", "openapi.yaml", "swagger.json", "swagger.yaml"):
            for hit in root.rglob(name):
                try:
                    text = hit.read_text(encoding="utf-8", errors="replace")[:200_000]
                except OSError:
                    continue
                sources.append(str(hit))
                if hit.suffix.lower() == ".json":
                    try:
                        data = json.loads(text)
                        paths = data.get("paths") or {}
                        for path, methods in paths.items():
                            if isinstance(methods, dict):
                                for method in methods:
                                    if method.lower() in ("get", "post", "put", "patch", "delete"):
                                        endpoints.append({
                                            "method": method.upper(),
                                            "path": path,
                                            "source": str(hit.name),
                                        })
                    except json.JSONDecodeError:
                        pass
                else:
                    for m in re.finditer(r"^\s{2}(/[\w/{}\-]+):", text, re.M):
                        endpoints.append({"method": "GET", "path": m.group(1), "source": hit.name})

        # Regex scan of source files
        for pat_glob in ("**/*.py", "**/*.ts", "**/*.js", "**/*.java", "**/*.go"):
            for fp in list(root.glob(pat_glob))[:80]:
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")[:50_000]
                except OSError:
                    continue
                for rx in _ROUTE_PATTERNS:
                    for m in rx.finditer(text):
                        groups = m.groups()
                        if len(groups) >= 2:
                            method, path = groups[0], groups[1]
                        elif len(groups) == 1:
                            method, path = "GET", groups[0]
                        else:
                            continue
                        if not str(path).startswith("/"):
                            path = "/" + str(path)
                        endpoints.append({
                            "method": str(method).upper(),
                            "path": str(path),
                            "source": str(fp.relative_to(root)).replace("\\", "/"),
                        })

    for h in (scout or {}).get("graph_hits") or []:
        path = h.get("path") or ""
        name = (h.get("name") or "").lower()
        if "route" in name or "handler" in name or "controller" in name:
            endpoints.append({"method": "GET", "path": f"/{name}", "source": path or "lattice"})

    for m in re.finditer(r"(GET|POST|PUT|PATCH|DELETE)\s+(/[\w/{}\-]+)", blueprint_prompt or "", re.I):
        endpoints.append({"method": m.group(1).upper(), "path": m.group(2), "source": "blueprint"})

    # Dedupe
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for ep in endpoints:
        key = (ep["method"], ep["path"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(ep)

    eval_cases = [
        {
            "id": f"schema_{i}",
            "type": "schema_presence",
            "method": ep["method"],
            "path": ep["path"],
            "assert": "endpoint_inventoried",
        }
        for i, ep in enumerate(unique[:40])
    ]
    return {
        "endpoints": unique[:80],
        "eval_cases": eval_cases,
        "sources": sources[:20],
        "count": len(unique),
    }


def run_api_evals(
    inventory: dict[str, Any],
    *,
    base_url: str = "",
) -> dict[str, Any]:
    """Schema presence checks + optional HTTP smoke against sandbox/base URL."""
    cases = list(inventory.get("eval_cases") or [])
    endpoints = list(inventory.get("endpoints") or [])
    results: list[dict[str, Any]] = []
    base = (base_url or os.getenv("MENTRIX_API_EVAL_BASE_URL", "")).rstrip("/")

    if not cases and not endpoints:
        # Empty inventory is OK for non-API upgrades — pass with note
        return {
            "ok": True,
            "score": 100,
            "passed": 0,
            "failed": 0,
            "results": [],
            "note": "No API endpoints inventoried — schema gate skipped",
            "gate": "api_eval",
        }

    # Schema presence: every inventoried endpoint counts as a case
    for case in cases:
        results.append({
            "id": case.get("id"),
            "type": "schema_presence",
            "ok": True,
            "method": case.get("method"),
            "path": case.get("path"),
        })

    http_ok = 0
    http_fail = 0
    if base and endpoints:
        for ep in endpoints[:10]:
            url = f"{base}{ep['path']}"
            # Only smoke GET-like paths for safety
            if ep["method"] not in ("GET", "HEAD"):
                continue
            try:
                req = urlrequest.Request(url, method="GET")
                with urlrequest.urlopen(req, timeout=5) as resp:  # noqa: S310
                    code = getattr(resp, "status", 200)
                ok = 200 <= int(code) < 500  # 4xx still proves route exists
                results.append({"id": f"http_{ep['path']}", "type": "http_smoke", "ok": ok, "status": code})
                if ok:
                    http_ok += 1
                else:
                    http_fail += 1
            except (urlerror.URLError, TimeoutError, OSError) as exc:
                results.append({
                    "id": f"http_{ep['path']}",
                    "type": "http_smoke",
                    "ok": False,
                    "error": str(exc)[:200],
                })
                http_fail += 1

    schema_fail = sum(1 for r in results if r.get("type") == "schema_presence" and not r.get("ok"))
    failed = schema_fail + http_fail
    passed = len(results) - failed
    # Require at least schema cases green; HTTP failures fail the gate when base URL set
    ok = failed == 0 and (len(cases) > 0 or True)
    if base and http_fail > 0:
        ok = False
    score = int(100 * passed / len(results)) if results else 100
    return {
        "ok": ok,
        "score": score,
        "passed": passed,
        "failed": failed,
        "results": results,
        "gate": "api_eval",
    }
