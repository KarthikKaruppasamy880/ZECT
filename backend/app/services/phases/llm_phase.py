"""Ask / Plan / enhance-blueprint — callable from ForgeLoop via openai_compat."""

from __future__ import annotations

import os
import re
from typing import Any

from app.adapters.llm.openai_compat import (
    get_openai_compat_client,
    mentrix_llm_chat_model,
    mentrix_local_llm_configured,
    openai_compat_available,
)
from app.services.work_items.fallback_policy import resolve_model_route
from app.services.work_items.telemetry import TelemetryTimer, build_telemetry


def _route(*, user_allows_cloud: bool | None = None):
    return resolve_model_route(
        local_configured=mentrix_local_llm_configured(),
        cloud_configured=bool((os.getenv("OPENAI_API_KEY") or "").strip()),
        local_model=mentrix_llm_chat_model(),
        cloud_model=mentrix_llm_chat_model(),
        user_allows_cloud=user_allows_cloud,
    )


def _chat(messages: list[dict[str, str]], *, max_tokens: int = 2000, temperature: float = 0.3) -> dict[str, Any]:
    """Call openai_compat gateway. Honors fallback policy (never blocks cloud)."""
    route = _route()
    timer = TelemetryTimer()
    if route.blocked or route.provider == "none":
        return {
            "ok": False,
            "blocked": True,
            "offline": True,
            "content": "",
            "model": "",
            "tokens_used": 0,
            "telemetry": build_telemetry(
                requested_provider="local",
                requested_model=mentrix_llm_chat_model(),
                actual_provider="none",
                actual_model="",
                fallback_used=route.fallback_used,
                fallback_reason=route.fallback_reason or route.block_reason,
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
            ),
            "error": route.block_reason or "llm_unavailable",
        }

    if not openai_compat_available():
        return {
            "ok": False,
            "blocked": True,
            "offline": True,
            "content": "",
            "model": "",
            "tokens_used": 0,
            "telemetry": build_telemetry(
                requested_provider=route.provider,
                requested_model=route.model,
                actual_provider="none",
                actual_model="",
                fallback_used=False,
                fallback_reason="openai_compat_unavailable",
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
            ),
            "error": "openai_compat_unavailable",
        }

    # Policy never: only local gateway (already enforced by resolve_model_route)
    if route.provider == "cloud" and not route.allow_cloud_context:
        return {
            "ok": False,
            "blocked": True,
            "offline": True,
            "content": "",
            "model": "",
            "tokens_used": 0,
            "telemetry": build_telemetry(
                requested_provider=route.provider,
                requested_model=route.model,
                actual_provider="none",
                actual_model="",
                fallback_used=False,
                fallback_reason="cloud_context_forbidden",
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
            ),
            "error": "cloud_context_forbidden",
        }

    try:
        client = get_openai_compat_client(timeout=90.0)
        model = route.model or mentrix_llm_chat_model()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        try:
            from app.token_tracker import log_tokens

            log_tokens(
                action="llm_phase",
                feature="forge_loop",
                model=model,
                prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
                total_tokens=tokens,
            )
        except Exception:  # noqa: BLE001
            pass
        return {
            "ok": True,
            "blocked": False,
            "offline": False,
            "content": content,
            "model": model,
            "tokens_used": tokens,
            "telemetry": build_telemetry(
                requested_provider=route.provider,
                requested_model=route.model,
                actual_provider=route.provider,
                actual_model=model,
                fallback_used=route.fallback_used,
                fallback_reason=route.fallback_reason,
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
            ),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "blocked": False,
            "offline": True,
            "content": "",
            "model": "error",
            "tokens_used": 0,
            "telemetry": build_telemetry(
                requested_provider=route.provider,
                requested_model=route.model,
                actual_provider="error",
                actual_model="",
                fallback_used=route.fallback_used,
                fallback_reason=str(e)[:200],
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
            ),
            "error": str(e),
        }


def run_ask(
    question: str,
    *,
    repo_context: str = "",
    repo_id: int | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Clarify requirements (Ask Mode). Offline/blocked when policy forbids cloud."""
    context = repo_context or ""
    if repo_id and db is not None and not context:
        from app.domains.agent_run.llm import _build_repo_context

        context = _build_repo_context(db, repo_id)

    system_prompt = (
        "You are ZECT Mentrix Ask — clarify upgrade requirements. "
        "Be concise; list open questions and assumed defaults for any-language → any-language ports."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append(
            {
                "role": "user",
                "content": f"Repository / Lattice context:\n\n{context[:8000]}",
            }
        )
    messages.append({"role": "user", "content": question})

    out = _chat(messages, max_tokens=2000, temperature=0.3)
    if out.get("ok"):
        return {
            "answer": out["content"],
            "model": out["model"],
            "tokens_used": out["tokens_used"],
            "offline": False,
            "telemetry": out.get("telemetry"),
        }

    return {
        "answer": (
            f"Ask (offline): clarify target language, modules to port, and acceptance tests for: "
            f"{question[:300]}"
            if out.get("blocked") or out.get("offline")
            else f"Ask failed: {out.get('error')}"
        ),
        "model": out.get("model") or "offline",
        "tokens_used": 0,
        "offline": True,
        "telemetry": out.get("telemetry"),
        "error": out.get("error"),
        "context_chars": len(context),
    }


def run_plan(
    project_description: str,
    *,
    repo_context: str = "",
    constraints: str = "",
    repo_id: int | None = None,
    db: Any = None,
    upgrade: bool = False,
) -> dict[str, Any]:
    """Structured engineering plan via openai_compat + fallback policy."""
    context = repo_context or ""
    if repo_id and db is not None and not context:
        from app.domains.agent_run.llm import _build_repo_context

        context = _build_repo_context(db, repo_id)

    def _offline_plan() -> dict[str, Any]:
        phases = [
            "Inventory APIs and modules",
            "Port module 1 (core)",
            "Port module 2 (integrations)",
            "Tests and API evals",
            "Mentrix Ultra Review + lint",
            "Human approve → PR",
        ]
        plan_text = (
            f"# Upgrade plan\n\nGoal: {project_description[:500]}\n\n"
            + "\n".join(f"## Phase {i+1}: {p}" for i, p in enumerate(phases))
        )
        steps = [
            {"step": i + 1, "title": p, "action": p, "files": [], "phase": p}
            for i, p in enumerate(phases)
        ]
        return {
            "plan": plan_text,
            "phases": phases,
            "steps": steps,
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
        }

    extra = ""
    if upgrade:
        extra = (
            " This is a language/platform upgrade. Phases MUST include: "
            "inventory → port module N → tests → API eval → review. "
            "Support any source→target language pair implied by the goal."
        )
    system_prompt = (
        "You are ZECT Mentrix Planner — senior engineering planner."
        f"{extra} "
        "Generate a detailed phased plan with markdown headers. "
        "Include architecture, risks, and acceptance criteria."
    )
    user_content = f"Project Description:\n{project_description}"
    if context:
        user_content += f"\n\nContext:\n{context[:6000]}"
    if constraints:
        user_content += f"\n\nConstraints:\n{constraints}"

    out = _chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=3000,
        temperature=0.4,
    )
    if not out.get("ok"):
        base = _offline_plan()
        base["telemetry"] = out.get("telemetry")
        base["error"] = out.get("error")
        return base

    plan_text = out["content"]
    phases = re.findall(r"^#{1,3}\s+(.+)$", plan_text, re.MULTILINE)[:20]
    if not phases:
        phases = [f"Phase {i+1}" for i in range(4)]
    steps = [
        {"step": i + 1, "title": p, "action": p, "files": [], "phase": p}
        for i, p in enumerate(phases)
    ]
    return {
        "plan": plan_text,
        "phases": phases,
        "steps": steps,
        "model": out["model"],
        "tokens_used": out["tokens_used"],
        "offline": False,
        "telemetry": out.get("telemetry"),
    }


def run_enhance_blueprint(raw_blueprint: str, instructions: str = "") -> dict[str, Any]:
    if not raw_blueprint.strip():
        return {
            "enhanced_prompt": instructions or "(empty blueprint)",
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
        }
    out = _chat(
        [
            {
                "role": "system",
                "content": (
                    "Enhance this migration blueprint into a clear Mentrix upgrade prompt. "
                    "Keep actionable file/module lists."
                ),
            },
            {
                "role": "user",
                "content": f"{instructions}\n\n{raw_blueprint[:10000]}" if instructions else raw_blueprint[:10000],
            },
        ],
        max_tokens=3000,
        temperature=0.3,
    )
    if not out.get("ok"):
        return {
            "enhanced_prompt": raw_blueprint,
            "model": out.get("model") or "offline",
            "tokens_used": 0,
            "offline": True,
            "telemetry": out.get("telemetry"),
            "error": out.get("error"),
        }
    return {
        "enhanced_prompt": out["content"] or raw_blueprint,
        "model": out["model"],
        "tokens_used": out["tokens_used"],
        "offline": False,
        "telemetry": out.get("telemetry"),
    }
