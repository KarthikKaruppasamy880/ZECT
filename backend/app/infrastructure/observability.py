"""Safe structured telemetry — correlation/run IDs, stages, durations, audits.

Never log secrets, tokens, private mappings, or presentation/patch bodies.
Process-local ring buffer plus optional JSONL; no new Postgres table in this tranche
(Alembic catch-up already stamped — new tables need an explicit revision).
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from contextvars import ContextVar
from typing import Any, Callable

from app.security.redact import contains_raw_secret, redact_mapping, redact_secrets, redact_text

_correlation: ContextVar[str] = ContextVar("zect_correlation", default="")
_run: ContextVar[str] = ContextVar("zect_run", default="")

_LOCK = threading.Lock()
_EVENTS: deque[dict[str, Any]] = deque(maxlen=2000)
_OPS: dict[str, dict[str, Any]] = {}
_MAX_MESSAGE = 400
_MAX_EXTRA_CHARS = 1200


class OperationCancelled(RuntimeError):
    """Cooperative cancel of a bounded operation (index/present/agent)."""


def new_id() -> str:
    return str(uuid.uuid4())


def current_correlation() -> str:
    return _correlation.get() or ""


def current_run_id() -> str:
    return _run.get() or ""


def bind_correlation(correlation_id: str) -> None:
    _correlation.set((correlation_id or "").strip())


def bind_run_id(run_id: str) -> None:
    _run.set((run_id or "").strip())


def reset_observability() -> None:
    """Test helper — clear process-local telemetry and cancel registry."""
    with _LOCK:
        _EVENTS.clear()
        _OPS.clear()
    bind_correlation("")
    bind_run_id("")


def _safe_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    cleaned = redact_mapping(extra or {})
    blob = json.dumps(cleaned, default=str)
    if len(blob) > _MAX_EXTRA_CHARS:
        cleaned = {"truncated": True, "keys": sorted(cleaned.keys())[:20]}
    if contains_raw_secret(cleaned):
        return {"redacted": True}
    return cleaned


def emit_event(
    *,
    operation: str,
    stage: str,
    message: str = "",
    duration_ms: int | None = None,
    retries: int = 0,
    failure_class: str = "",
    work_item_id: int | None = None,
    project_id: int | None = None,
    repo: str = "",
    workspace: str = "",
    commit: str = "",
    worktree: str = "",
    model_route: str = "",
    tool: str = "",
    run_id: str = "",
    correlation_id: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a redacted structured event. Returns the stored record."""
    rec = {
        "ts": time.time(),
        "correlation_id": (correlation_id or current_correlation() or "").strip(),
        "run_id": (run_id or current_run_id() or "").strip(),
        "operation": redact_text(operation)[:80],
        "stage": redact_text(stage)[:80],
        "message": redact_text(message)[:_MAX_MESSAGE],
        "duration_ms": int(duration_ms) if duration_ms is not None else None,
        "retries": int(retries or 0),
        "failure_class": redact_text(failure_class)[:80],
        "work_item_id": work_item_id,
        "project_id": project_id,
        "repo": redact_text(repo)[:200],
        "workspace": redact_text(workspace)[:200],
        "commit": redact_text(commit)[:64],
        "worktree": redact_text(worktree)[:200],
        "model_route": redact_text(model_route)[:120],
        "tool": redact_text(tool)[:80],
        "extra": _safe_extra(extra),
    }
    with _LOCK:
        _EVENTS.append(rec)
    _maybe_jsonl(rec)
    return rec


def query_events(
    *,
    correlation_id: str = "",
    run_id: str = "",
    operation: str = "",
    failure_class: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    cid = (correlation_id or "").strip()
    rid = (run_id or "").strip()
    op = (operation or "").strip()
    fc = (failure_class or "").strip()
    cap = max(1, min(int(limit or 50), 200))
    with _LOCK:
        rows = list(_EVENTS)
    out: list[dict[str, Any]] = []
    for rec in reversed(rows):
        if cid and rec.get("correlation_id") != cid:
            continue
        if rid and rec.get("run_id") != rid:
            continue
        if op and rec.get("operation") != op:
            continue
        if fc and rec.get("failure_class") != fc:
            continue
        out.append(rec)
        if len(out) >= cap:
            break
    return out


def begin_operation(
    run_id: str,
    *,
    kind: str,
    extra: dict[str, Any] | None = None,
) -> str:
    rid = (run_id or "").strip() or new_id()
    bind_run_id(rid)
    with _LOCK:
        prev = _OPS.get(rid)
        already = bool(prev and prev.get("cancelled"))
        _OPS[rid] = {
            "kind": kind,
            "cancelled": already,
            "started": time.time(),
            "extra": _safe_extra(extra),
        }
    emit_event(operation=kind, stage="start", run_id=rid, extra=extra)
    return rid


def cancel_operation(run_id: str) -> bool:
    rid = (run_id or "").strip()
    if not rid:
        return False
    with _LOCK:
        row = _OPS.get(rid)
        if row is None:
            _OPS[rid] = {"kind": "unknown", "cancelled": True, "started": time.time(), "extra": {}}
            row = _OPS[rid]
        row["cancelled"] = True
    emit_event(operation=str(row.get("kind") or "unknown"), stage="cancel_requested", run_id=rid, failure_class="cancelled")
    return True


def is_cancelled(run_id: str = "") -> bool:
    rid = (run_id or current_run_id() or "").strip()
    if not rid:
        return False
    with _LOCK:
        row = _OPS.get(rid)
        return bool(row and row.get("cancelled"))


def raise_if_cancelled(run_id: str = "") -> None:
    if is_cancelled(run_id):
        raise OperationCancelled("operation_cancelled")


def snapshot_summary() -> dict[str, Any]:
    with _LOCK:
        n = len(_EVENTS)
        ops = {k: {"kind": v.get("kind"), "cancelled": bool(v.get("cancelled"))} for k, v in list(_OPS.items())[-20:]}
    rss, handles = resource_snapshot()
    return {
        "event_count": n,
        "active_operations": ops,
        "rss_bytes": rss,
        "handle_count": handles,
    }


def resource_snapshot() -> tuple[int, int | None]:
    """Return (rss_bytes, handle_count_or_None). Handles may be unmeasured on some hosts."""
    rss = 0
    handles: int | None = None
    if os.name == "nt":
        try:
            import ctypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                ctypes.c_ulong,
            ]
            psapi.GetProcessMemoryInfo.restype = ctypes.c_int
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = kernel32.GetCurrentProcess()
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                rss = int(counters.WorkingSetSize)
            count = ctypes.c_ulong(0)
            kernel32.GetProcessHandleCount.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
            kernel32.GetProcessHandleCount.restype = ctypes.c_int
            if kernel32.GetProcessHandleCount(handle, ctypes.byref(count)):
                handles = int(count.value)
        except Exception:
            rss = 0
            handles = None
    if rss <= 0:
        try:
            import resource as posix_resource

            usage = posix_resource.getrusage(posix_resource.RUSAGE_SELF).ru_maxrss
            # Linux: KB; macOS: bytes
            rss = int(usage) * 1024 if os.name == "posix" and usage < 10**9 else int(usage)
        except Exception:
            pass
    if rss <= 0:
        try:
            import tracemalloc

            if not tracemalloc.is_tracing():
                tracemalloc.start()
            current, _peak = tracemalloc.get_traced_memory()
            rss = int(current) or 1
        except Exception:
            rss = 0
    return rss, handles


def db_checked_out() -> int | None:
    try:
        from app.infrastructure.database import engine

        pool = getattr(engine, "pool", None)
        if pool is None or not hasattr(pool, "checkedout"):
            return None
        return int(pool.checkedout())
    except Exception:
        return None


def emit_privileged(
    *,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    resource_name: str = "",
    details: dict[str, Any] | str | None = None,
    user_id: int | None = None,
) -> None:
    """Privileged-action audit (redacted). Fail-soft — never raises to callers."""
    try:
        from app.domains.audit.audit_trail import log_audit
        from app.infrastructure.database import SessionLocal

        payload: dict[str, Any] | str
        if isinstance(details, dict):
            payload = redact_mapping(details)
            payload["correlation_id"] = current_correlation()
            payload["run_id"] = current_run_id()
        else:
            payload = redact_text(str(details or ""))
        db = SessionLocal()
        try:
            log_audit(
                db,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                details=payload,
                user_id=user_id,
            )
        finally:
            db.close()
    except Exception:
        emit_event(
            operation="audit",
            stage="write_failed",
            failure_class="audit_error",
            extra={"action": action, "resource_type": resource_type},
        )


def diagnose(correlation_id: str = "", run_id: str = "") -> dict[str, Any]:
    """Root-stage diagnosis from telemetry (no secrets)."""
    rows = query_events(correlation_id=correlation_id, run_id=run_id, limit=80)
    failures = [r for r in rows if r.get("failure_class")]
    first = failures[-1] if failures else (rows[0] if rows else None)
    return {
        "correlation_id": correlation_id or current_correlation(),
        "run_id": run_id or current_run_id(),
        "event_count": len(rows),
        "root_stage": (first or {}).get("stage") or "",
        "failure_class": (first or {}).get("failure_class") or "",
        "operation": (first or {}).get("operation") or "",
        "message": (first or {}).get("message") or "",
        "events": rows,
    }


def _maybe_jsonl(rec: dict[str, Any]) -> None:
    dest = (os.getenv("ZECT_TELEMETRY_JSONL") or "").strip()
    if not dest:
        return
    try:
        path = dest
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except OSError:
        return


def cancel_check_for(run_id: str) -> Callable[[], bool]:
    rid = (run_id or "").strip()

    def _check() -> bool:
        return is_cancelled(rid)

    return _check
