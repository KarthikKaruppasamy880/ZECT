"""Local profile + sample store (JSON under ZECT_VOICEBOX_DATA_DIR)."""

from __future__ import annotations

import json
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import config

_lock = threading.Lock()


def _store_path() -> Path:
    return config.data_dir() / "profiles.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    path = _store_path()
    if not path.is_file():
        return {"profiles": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"profiles": {}}


def _save(data: dict[str, Any]) -> None:
    path = _store_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def list_profiles() -> list[dict[str, Any]]:
    with _lock:
        data = _load()
        out = []
        for pid, p in data.get("profiles", {}).items():
            out.append(_public(pid, p))
        return out


def get_profile(profile_id: str) -> dict[str, Any] | None:
    with _lock:
        p = _load().get("profiles", {}).get(profile_id)
        if not p:
            return None
        return _public(profile_id, p)


def get_profile_raw(profile_id: str) -> dict[str, Any] | None:
    with _lock:
        p = _load().get("profiles", {}).get(profile_id)
        return dict(p) if p else None


def create_profile(name: str, language: str = "en", voice_type: str = "cloned") -> dict[str, Any]:
    pid = uuid.uuid4().hex
    profile_dir = config.data_dir() / "profiles" / pid
    profile_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "name": name[:100],
        "language": language or "en",
        "voice_type": voice_type or "cloned",
        "created_at": _now(),
        "sample_path": "",
        "reference_text": "",
        "sample_filename": "",
    }
    with _lock:
        data = _load()
        data.setdefault("profiles", {})[pid] = row
        _save(data)
    return _public(pid, row)


def delete_profile(profile_id: str) -> bool:
    with _lock:
        data = _load()
        profiles = data.get("profiles", {})
        if profile_id not in profiles:
            return False
        del profiles[profile_id]
        _save(data)
    profile_dir = config.data_dir() / "profiles" / profile_id
    if profile_dir.is_dir():
        shutil.rmtree(profile_dir, ignore_errors=True)
    return True


def attach_sample(
    profile_id: str,
    audio_bytes: bytes,
    filename: str,
    reference_text: str,
) -> dict[str, Any]:
    with _lock:
        data = _load()
        profiles = data.get("profiles", {})
        if profile_id not in profiles:
            raise KeyError(profile_id)
        profile_dir = config.data_dir() / "profiles" / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        safe = Path(filename or "sample.wav").name
        dest = profile_dir / safe
        dest.write_bytes(audio_bytes)
        profiles[profile_id]["sample_path"] = str(dest)
        profiles[profile_id]["sample_filename"] = safe
        profiles[profile_id]["reference_text"] = (reference_text or "")[:2000]
        profiles[profile_id]["updated_at"] = _now()
        _save(data)
        return _public(profile_id, profiles[profile_id])


def _public(pid: str, p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": pid,
        "name": p.get("name") or "",
        "language": p.get("language") or "en",
        "voice_type": p.get("voice_type") or "cloned",
        "has_sample": bool(p.get("sample_path")),
        "created_at": p.get("created_at"),
    }
