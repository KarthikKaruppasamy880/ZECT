"""Mobile Companion → linked Electron desktop command bridge.

In-memory with durable JSON spill so queues survive brief API restarts (PA gap-close).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

_lock = Lock()
_QUEUES: dict[str, list[dict[str, Any]]] = {}
_AGENTS: dict[str, dict[str, Any]] = {}

_STORE = Path(__file__).resolve().parents[3] / "data" / "desktop_bridge_queue.json"


def _key(user_email: str = "", agent_id: str = "") -> str:
    return (agent_id or user_email or "default").strip().lower() or "default"


def _persist() -> None:
    try:
        _STORE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"queues": _QUEUES, "agents": _AGENTS, "ts": time.time()}
        _STORE.write_text(json.dumps(payload, default=str)[:500_000], encoding="utf-8")
    except OSError:
        pass


def _load() -> None:
    global _QUEUES, _AGENTS
    if not _STORE.is_file():
        return
    try:
        data = json.loads(_STORE.read_text(encoding="utf-8"))
        if isinstance(data.get("queues"), dict):
            _QUEUES = data["queues"]
        if isinstance(data.get("agents"), dict):
            _AGENTS = data["agents"]
    except Exception:
        pass


_load()


def register_agent(user_email: str, agent_id: str = "electron") -> dict[str, Any]:
    k = _key(user_email, agent_id)
    with _lock:
        _AGENTS[k] = {"ts": time.time(), "agent_id": agent_id or "electron", "online": True}
        _persist()
    return {"ok": True, "session_key": k, "agent_id": agent_id or "electron"}


def agent_status(user_email: str, agent_id: str = "electron") -> dict[str, Any]:
    k = _key(user_email, agent_id)
    with _lock:
        info = _AGENTS.get(k)
    if not info:
        return {"online": False, "error": "desktop_offline", "hint": "Open ZECT Electron and link desktop agent"}
    age = time.time() - float(info.get("ts") or 0)
    online = age < 90
    return {
        "online": online,
        "age_s": int(age),
        "agent_id": info.get("agent_id"),
        "error": None if online else "desktop_offline",
        "hint": None if online else "Desktop agent heartbeat stale — open Electron Companion",
    }


def heartbeat(user_email: str, agent_id: str = "electron") -> dict[str, Any]:
    return register_agent(user_email, agent_id)


def enqueue(user_email: str, command: dict[str, Any], agent_id: str = "electron") -> dict[str, Any]:
    st = agent_status(user_email, agent_id)
    if not st.get("online"):
        return {
            "ok": False,
            "error": "desktop_offline",
            "hint": st.get("hint") or "Desktop offline",
        }
    item = {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "status": "queued",
        "command": command or {},
    }
    k = _key(user_email, agent_id)
    with _lock:
        q = _QUEUES.setdefault(k, [])
        q.append(item)
        if len(q) > 100:
            del q[0 : len(q) - 100]
        _persist()
    return {"ok": True, "id": item["id"], "queued": True, "durable": True}


def poll(user_email: str, agent_id: str = "electron") -> dict[str, Any]:
    heartbeat(user_email, agent_id)
    k = _key(user_email, agent_id)
    with _lock:
        q = [x for x in _QUEUES.get(k, []) if x.get("status") == "queued"]
    return {"items": q[:20], "online": True, "durable": True}


def ack(user_email: str, cmd_id: str, agent_id: str = "electron", result: dict | None = None) -> dict[str, Any]:
    k = _key(user_email, agent_id)
    with _lock:
        for item in _QUEUES.get(k, []):
            if item.get("id") == cmd_id:
                item["status"] = "acked"
                item["result"] = result or {}
                _persist()
                return {"ok": True}
    return {"ok": False, "error": "not_found"}
