"""Mentrix OpenAI-compatible LLM client factory.

When ZECT_LLM_BASE_URL is set, chat uses the Mentrix Local LLM gateway
(OpenAI-compatible /v1). Otherwise falls back to cloud OPENAI_API_KEY.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from openai import OpenAI


def mentrix_llm_base_url() -> str:
    return (os.getenv("ZECT_LLM_BASE_URL") or "").strip().rstrip("/")


def mentrix_llm_api_key() -> str:
    return (os.getenv("ZECT_LLM_API_KEY") or "local").strip() or "local"


def mentrix_llm_chat_model() -> str:
    return (
        os.getenv("ZECT_LLM_CHAT_MODEL")
        or os.getenv("MENTRIX_COMPANION_MODEL")
        or "gpt-4o-mini"
    ).strip()


def mentrix_local_llm_configured() -> bool:
    return bool(mentrix_llm_base_url())


def get_openai_compat_client(*, timeout: float | None = None) -> OpenAI:
    """Return an OpenAI SDK client aimed at Mentrix Local LLM or cloud OpenAI."""
    base = mentrix_llm_base_url()
    if base:
        kwargs: dict[str, Any] = {
            "api_key": mentrix_llm_api_key(),
            "base_url": base if base.endswith("/v1") else f"{base}/v1",
        }
        if timeout is not None:
            kwargs["timeout"] = timeout
        return OpenAI(**kwargs)

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "No Mentrix Local LLM gateway (ZECT_LLM_BASE_URL) and OPENAI_API_KEY is not set."
        )
    kwargs = {"api_key": key}
    if timeout is not None:
        kwargs["timeout"] = timeout
    return OpenAI(**kwargs)


def openai_compat_available() -> bool:
    if mentrix_local_llm_configured():
        return True
    return bool((os.getenv("OPENAI_API_KEY") or "").strip())


def probe_mentrix_local_llm(*, timeout: float = 1.5) -> dict[str, Any]:
    """Short health probe for Mentrix Local LLM (/v1/models)."""
    base = mentrix_llm_base_url()
    if not base:
        return {
            "configured": False,
            "online": False,
            "base_url": "",
            "models": [],
            "label": "Mentrix Local LLM not configured",
        }
    url = base if base.endswith("/v1") else f"{base}/v1"
    models_url = f"{url}/models"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                models_url,
                headers={"Authorization": f"Bearer {mentrix_llm_api_key()}"},
            )
        if r.status_code >= 400:
            return {
                "configured": True,
                "online": False,
                "base_url": url,
                "models": [],
                "label": "Mentrix Local LLM offline",
                "detail": f"HTTP {r.status_code}",
            }
        data = r.json() if r.content else {}
        items = data.get("data") if isinstance(data, dict) else []
        ids: list[str] = []
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("id"):
                    ids.append(str(it["id"]))
        return {
            "configured": True,
            "online": True,
            "base_url": url,
            "models": ids[:40],
            "label": "Mentrix Local LLM online",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "configured": True,
            "online": False,
            "base_url": url,
            "models": [],
            "label": "Mentrix Local LLM offline",
            "detail": str(exc)[:200],
        }


# Seed Mentrix Local model ids (weights pulled via Mentrix Local LLM runtime).
MENTRIX_LOCAL_MODELS = [
    {
        "id": "qwen2.5:7b",
        "name": "Mentrix Local — Qwen 2.5 7B",
        "provider": "mentrix_local",
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "free": True,
        "quality": "good",
        "speed": "medium",
    },
    {
        "id": "llama3.1",
        "name": "Mentrix Local — Llama 3.1",
        "provider": "mentrix_local",
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "free": True,
        "quality": "good",
        "speed": "medium",
    },
    {
        "id": "llama3.1:8b",
        "name": "Mentrix Local — Llama 3.1 8B",
        "provider": "mentrix_local",
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "free": True,
        "quality": "good",
        "speed": "medium",
    },
]
