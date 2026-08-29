"""Translate remote Agent Server event payloads into stable ZECT RuntimeEvents.

React and Mentrix never see remote-specific shapes — only RuntimeEvent fields.
"""

from __future__ import annotations

from typing import Any

from app.adapters.coding_runtime import RuntimeEvent

# Map common remote event type strings → ZECT event + phase
_TYPE_MAP: dict[str, tuple[str, str]] = {
    "message": ("message", "running"),
    "agent_message": ("message", "running"),
    "user_message": ("message", "running"),
    "action": ("action", "running"),
    "observation": ("observation", "running"),
    "error": ("error", "failed"),
    "agent_state_changed": ("status", "running"),
    "agent_state": ("status", "running"),
    "status": ("status", "running"),
    "thinking": ("progress", "running"),
    "tool_call": ("action", "running"),
    "tool_result": ("observation", "running"),
    "file_edit": ("file_change", "build"),
    "file_write": ("file_change", "build"),
    "cmd": ("terminal", "build"),
    "command": ("terminal", "build"),
    "finish": ("completed", "validating"),
    "done": ("completed", "validating"),
    "completed": ("completed", "validating"),
    "cancelled": ("cancelled", "cancel"),
    "approval_required": ("awaiting_approval", "awaiting_approval"),
    "security_risk": ("awaiting_approval", "awaiting_approval"),
}


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _message_from_remote(payload: dict[str, Any]) -> str:
    for key in ("message", "content", "text", "summary", "observation"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:2000]
    args = payload.get("args")
    if isinstance(args, dict):
        for key in ("content", "command", "path", "thought"):
            val = args.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:2000]
    action = payload.get("action")
    if isinstance(action, str) and action.strip():
        return action.strip()[:500]
    et = payload.get("type") or payload.get("event_type") or payload.get("kind")
    if et:
        return str(et)
    return "remote_event"


def _type_key(payload: dict[str, Any]) -> str:
    for key in ("type", "event_type", "kind", "action"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    source = payload.get("source")
    if isinstance(source, str) and source.strip():
        return source.strip().lower()
    return "status"


def translate_remote_event(raw: Any, *, sequence_id: int) -> RuntimeEvent:
    """Convert one remote event dict into a ZECT RuntimeEvent."""
    payload = _as_dict(raw)
    if "event" in payload and isinstance(payload["event"], dict):
        inner = payload["event"]
        payload = {**inner, **{k: v for k, v in payload.items() if k != "event"}}
    tkey = _type_key(payload)
    event_name, phase = _TYPE_MAP.get(tkey, ("progress", "running"))
    state = str(payload.get("agent_state") or payload.get("state") or "").upper()
    if state in ("FINISHED", "COMPLETED", "DONE"):
        event_name, phase = "completed", "validating"
    elif state in ("ERROR", "FAILED"):
        event_name, phase = "error", "failed"
    elif state in ("AWAITING_USER_CONFIRMATION", "WAITING", "PAUSED"):
        event_name, phase = "awaiting_approval", "awaiting_approval"
    elif state in ("STOPPED", "CANCELLED"):
        event_name, phase = "cancelled", "cancel"

    data: dict[str, Any] = {}
    for key in ("path", "file", "filename", "exit_code", "tool", "action_id", "id"):
        if key in payload and payload[key] is not None:
            val = payload[key]
            if isinstance(val, (str, int, float, bool)):
                data[key] = val if not isinstance(val, str) else val[:500]
    return RuntimeEvent(
        sequence_id=sequence_id,
        event=event_name,
        message=_message_from_remote(payload),
        phase=phase,
        data=data,
    )


def translate_remote_events(raw_list: Any, *, after: int = 0) -> list[RuntimeEvent]:
    """Translate a list/payload of remote events; assign 1-based sequence ids."""
    if isinstance(raw_list, dict):
        items = raw_list.get("events") or raw_list.get("items") or raw_list.get("data") or []
    elif isinstance(raw_list, list):
        items = raw_list
    else:
        items = []
    out: list[RuntimeEvent] = []
    for i, item in enumerate(items):
        seq = i + 1
        if isinstance(item, dict):
            for sk in ("sequence_id", "seq", "id", "event_id"):
                if isinstance(item.get(sk), int) and item[sk] > 0:
                    seq = int(item[sk])
                    break
        if seq <= after:
            continue
        out.append(translate_remote_event(item, sequence_id=seq))
    out.sort(key=lambda e: e.sequence_id)
    return out
