"""Propose bounded file patches from an approved PLAN using ContextPack."""

from __future__ import annotations

import json
import re
from typing import Any


_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def propose_from_plan(mission: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Return {repo_id: [{path, old, new}, ...]} — empty dict if LLM unavailable."""
    from app.adapters.llm.openai_compat import get_openai_compat_client, openai_compat_available, mentrix_llm_chat_model
    from app.services.coding_engine.agent_context import compose_coding_agent_context

    if not openai_compat_available():
        raise ValueError("llm_offline")

    pack = compose_coding_agent_context(
        goal=f"{mission.get('goal') or ''}\n{mission.get('plan') or ''}",
        project_id=mission.get("project_id"),
    )
    roots = []
    for repo in mission.get("repos") or []:
        rid = repo.get("repository_id") or repo.get("id")
        roots.append(f"{rid}: {repo.get('label') or ''} @ {repo.get('source_path') or ''}")
    prompt = (
        "Return JSON only: {\"patches_by_repo\": {\"<repository_id>\": [{\"path\": \"rel/file.py\", \"old\": \"exact\", \"new\": \"replacement\"}]}}.\n"
        "At most 8 patches total. Paths must be relative. old must exist in the file or be empty for new files.\n"
        "Do not invent secrets. If you cannot ground a change in the PLAN + Lattice facts, return {\"patches_by_repo\": {}}.\n\n"
        f"Goal:\n{mission.get('goal') or ''}\n\nPLAN:\n{(mission.get('plan') or '')[:6000]}\n\n"
        f"Authorized roots:\n" + "\n".join(roots) + f"\n\nContextPack:\n{pack[:2500]}"
    )
    client = get_openai_compat_client()
    resp = client.chat.completions.create(
        model=mentrix_llm_chat_model(),
        messages=[
            {"role": "system", "content": "You propose small, reviewable code patches. JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or "{}"
    data = _parse_json(raw)
    patches = data.get("patches_by_repo") if isinstance(data, dict) else {}
    if not isinstance(patches, dict):
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    count = 0
    for key, rows in patches.items():
        if count >= 8:
            break
        if not isinstance(rows, list):
            continue
        cleaned = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "").replace("\\", "/").lstrip("/")
            if not path or ".." in path.split("/"):
                continue
            cleaned.append(
                {
                    "path": path[:240],
                    "old": str(row.get("old") or "")[:8000],
                    "new": str(row.get("new") or "")[:8000],
                }
            )
            count += 1
            if count >= 8:
                break
        if cleaned:
            out[str(key)] = cleaned
    return out


def _parse_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    match = _JSON_FENCE.search(text)
    if match:
        text = match.group(1)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
