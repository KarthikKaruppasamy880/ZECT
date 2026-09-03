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
from app.services.work_items.model_router import (
    COMPLEXITY_COMPLEX,
    COMPLEXITY_MODERATE,
    COMPLEXITY_TRIVIAL,
    TASK_DEEP_ASK,
    TASK_LIGHTWEIGHT_ASK,
    TASK_PLAN,
    ModelRouteDecision,
    TaskProfile,
    estimate_cost_usd,
    estimate_tokens,
    route_model,
)
from app.services.work_items.telemetry import TelemetryTimer, build_telemetry


class _RouteShape:
    """Adapts a CP-08 ModelRouteDecision to the attribute shape _chat()
    already branches on (route.blocked/.provider/.model/.allow_cloud_
    context/.fallback_used/.fallback_reason) -- fallback_policy.RouteDecision's
    own shape, so passing a `task` costs _chat() nothing structurally.
    """

    def __init__(self, decision: ModelRouteDecision) -> None:
        self.decision = decision
        self.model = decision.selected_model
        self.blocked = decision.blocked
        self.block_reason = decision.block_reason
        if decision.selected_provider == "mentrix_local":
            self.provider = "local"
        elif decision.selected_provider in ("anthropic", "openai_compat"):
            self.provider = "cloud"
        else:
            self.provider = "none"
        self.allow_cloud_context = self.provider == "cloud"
        self.fallback_used = any(not s.accepted for s in decision.chain)
        self.fallback_reason = decision.routing_reason if self.fallback_used else ""


def _route(*, user_allows_cloud: bool | None = None, policy: str | None = None):
    kwargs: dict[str, Any] = {
        "local_configured": mentrix_local_llm_configured(),
        "cloud_configured": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
        "local_model": mentrix_llm_chat_model(),
        "cloud_model": mentrix_llm_chat_model(),
        "user_allows_cloud": user_allows_cloud,
    }
    if policy:
        kwargs["policy"] = policy
    return resolve_model_route(**kwargs)


def _chat(
    messages: list[dict[str, Any]],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    policy: str | None = None,
    user_allows_cloud: bool | None = None,
    task: TaskProfile | None = None,
) -> dict[str, Any]:
    """Call the configured model. Honors fallback policy (never blocks cloud).

    `task`, when given, routes through CP-08's canonical model_router
    instead of the flat single-default `_route()` below -- e.g. a complex
    PLAN can land on claude-opus-5 rather than always the one env-var
    default every other call gets, and the pick is auditable (route.chain).
    Left None (every pre-CP-08 caller: run_plan, run_enhance_blueprint),
    behavior is byte-for-byte what it was before this module existed.
    """
    if task is not None:
        return _chat_routed(messages, max_tokens=max_tokens, temperature=temperature, policy=policy, user_allows_cloud=user_allows_cloud, task=task)
    route = _route(user_allows_cloud=user_allows_cloud, policy=policy)
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


def _chat_routed(
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    temperature: float,
    policy: str | None,
    user_allows_cloud: bool | None,
    task: TaskProfile,
) -> dict[str, Any]:
    """Task-aware sibling of the block above _chat() delegates to when a
    `task` is given. Dispatches through agent_model_adapter.get_agent_
    model_adapter() rather than the raw OpenAI-compat client directly --
    the router can select an Anthropic model for a complex PLAN, and only
    the adapter abstraction (already proven by the AGENT tool-calling
    loop) knows how to actually call Anthropic; the plain client used by
    the non-routed path above only ever speaks to an OpenAI-compatible
    endpoint.
    """
    from app.adapters.llm.agent_model_adapter import AUTO_ROUTED, ModelProviderError, get_agent_model_adapter

    decision = route_model(task, mode=AUTO_ROUTED, policy=policy, user_allows_cloud=user_allows_cloud)
    route = _RouteShape(decision)
    timer = TelemetryTimer()

    def _blocked(reason: str) -> dict[str, Any]:
        return {
            "ok": False,
            "blocked": True,
            "offline": True,
            "content": "",
            "model": "",
            "tokens_used": 0,
            "telemetry": build_telemetry(
                requested_provider=route.provider or "none",
                requested_model=mentrix_llm_chat_model(),
                actual_provider="none",
                actual_model="",
                fallback_used=route.fallback_used,
                fallback_reason=reason,
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
                routing_reason=decision.routing_reason,
                routing_chain=[s.to_dict() for s in decision.chain],
                phase=task.phase,
                context_budget=decision.context_budget,
            ),
            "error": reason,
        }

    if decision.blocked:
        return _blocked(decision.block_reason)
    if route.provider == "cloud" and not route.allow_cloud_context:
        return _blocked("cloud_context_forbidden")

    model = decision.selected_model
    try:
        adapter, resolved_model = get_agent_model_adapter(model, mode=AUTO_ROUTED)
    except ModelProviderError as exc:
        # Belt-and-suspenders: route_model() already confirmed this
        # provider's policy/availability, so this should not happen -- if
        # it ever does, block rather than silently trying the next
        # candidate outside the recorded chain.
        return _blocked(f"adapter_unavailable:{exc.reason}")

    try:
        resp = adapter.create(
            model=resolved_model, messages=messages, tools=None, tool_choice="auto",
            temperature=temperature, max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        try:
            from app.token_tracker import log_tokens

            log_tokens(
                action="llm_phase", feature="forge_loop", model=resolved_model,
                prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        except Exception:  # noqa: BLE001
            pass
        estimated_cost = estimate_cost_usd(resolved_model, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens)
        return {
            "ok": True,
            "blocked": False,
            "offline": False,
            "content": content,
            "model": resolved_model,
            "tokens_used": usage.total_tokens,
            "telemetry": build_telemetry(
                requested_provider=route.provider,
                requested_model=decision.requested_model or resolved_model,
                actual_provider=resp.provider,
                actual_model=resolved_model,
                fallback_used=route.fallback_used,
                fallback_reason=route.fallback_reason,
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
                phase=task.phase,
                routing_reason=decision.routing_reason,
                context_budget=decision.context_budget,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cached_tokens=0,
                estimated_cost=estimated_cost,
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
                requested_model=decision.requested_model or model,
                actual_provider="error",
                actual_model="",
                fallback_used=route.fallback_used,
                fallback_reason=str(e)[:200],
                latency_ms=timer.latency_ms(),
                operation_id="llm_phase",
                phase=task.phase,
                routing_reason=decision.routing_reason,
                context_budget=decision.context_budget,
            ),
            "error": str(e),
        }


def run_ask(
    question: str,
    *,
    repo_context: str = "",
    repo_id: int | None = None,
    db: Any = None,
    images: list[str] | None = None,
) -> dict[str, Any]:
    """Clarify requirements (Ask Mode). Offline/blocked when policy forbids cloud.

    `images`, when given, are data URLs (data:image/png;base64,...) -- e.g. a
    screenshot pasted into the composer. The OpenAI SDK's chat.completions.create
    already accepts multimodal content blocks natively for vision-capable
    models, so this only needs to shape the final user message correctly; if
    the configured model isn't vision-capable, the provider itself returns a
    clear API error rather than this silently dropping the image.
    """
    context = repo_context or ""
    if repo_id and db is not None and not context:
        from app.domains.agent_run.llm import _build_repo_context

        context = _build_repo_context(db, repo_id)

    system_prompt = (
        "You are ZECT Mentrix Ask — a repository-grounded research assistant, not a general coding chat. "
        "Only name a specific file, class, function, API route, or database object if it appears "
        "verbatim in the repository/Lattice context provided below. If the requirement describes "
        "functionality you cannot find evidence for in that context, say plainly: "
        "'Not found in the current repository after searching.' Do not invent plausible-sounding "
        "names to fill a gap in the evidence. You may describe a new/proposed name, but only if you "
        "explicitly label it as proposed rather than existing. "
        "Be concise; list open questions and assumed defaults for any-language → any-language ports."
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append(
            {
                "role": "user",
                "content": f"Repository / Lattice context:\n\n{context[:8000]}",
            }
        )
    task: TaskProfile | None = None
    if images:
        # CP-08 scope boundary: the router's TASK_VISION_BROWSER candidates
        # include Anthropic models, but agent_model_adapter's OpenAI->
        # Anthropic message translation (_to_anthropic_messages) only
        # handles plain-string and tool-call content today -- a multipart
        # image_url content list falls through its str(content) fallback
        # and would ship Anthropic a garbled text repr instead of an image
        # block. Keep this path on its existing, already-working
        # OpenAI-compat-only route (task=None) rather than risk sending a
        # broken vision request; AGENT's browser-verification role (which
        # only ever sends image content via a tool *result*, already
        # handled correctly by that same translator) is unaffected.
        content: list[dict[str, Any]] = [{"type": "text", "text": question}]
        for url in images:
            content.append({"type": "image_url", "image_url": {"url": url}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": question})
        task = TaskProfile(
            task_type=TASK_DEEP_ASK if len(context) > 4000 else TASK_LIGHTWEIGHT_ASK,
            phase="ask",
            complexity=COMPLEXITY_MODERATE if len(context) > 4000 else COMPLEXITY_TRIVIAL,
            context_tokens_estimate=estimate_tokens(context) + estimate_tokens(question),
        )

    out = _chat(messages, max_tokens=2000, temperature=0.3, task=task)
    if out.get("ok"):
        return {
            "answer": out["content"],
            "model": out["model"],
            "tokens_used": out["tokens_used"],
            "offline": False,
            "telemetry": out.get("telemetry"),
        }

    retrieved = f"\n\nRetrieved from authorized repo:\n{context[:2500]}" if context else ""
    return {
        "answer": (
            (
                f"Ask (offline): clarify target language, modules to port, and acceptance tests for: "
                f"{question[:300]}{retrieved}"
            )
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


def run_grounded_plan(
    project_description: str,
    *,
    evidence_ledger_block: str = "",
    architecture_summary: str = "",
    repo_context: str = "",
    constraints: str = "",
    complexity: str = "",
    repo_language: str = "",
    repo_size_files: int = 0,
) -> dict[str, Any]:
    """CP-05 grounded plan generator for the Developer ASK/PLAN path --
    distinct from run_plan() above (which other, unrelated subsystems --
    bugfix_phase.py, forge_loop/orchestrator.py -- still call, so its
    existing behavior is left alone rather than risking those callers).

    Asks for prose covering every mandated section except the two
    file-impact sections (Existing files to modify / New files), which the
    caller always renders deterministically from a validated FileImpact
    list -- never from this model's own words. Also asks for a trailing
    fenced JSON block of *candidate* file impacts (mostly CREATE_NEW
    proposals); the caller must validate every entry via
    plan_generator.validate_file_impacts() before accepting any of them --
    this call's JSON output is a proposal, not a fact.
    """
    system_prompt = (
        "You are ZECT Mentrix Planner -- a repository-grounded engineering planner, not a "
        "general-purpose writer. Use ONLY the Evidence Ledger and repository context provided "
        "below as fact. An entity marked NOT_FOUND does not exist in the repository; you may "
        "propose creating it as a new file (via the trailing JSON block, action CREATE_NEW, with "
        "an explicit rationale) but must never describe it in prose as already existing or as a "
        "target to modify. Never invent a phase name, module name, or file path as a placeholder "
        "(no 'Port Module N', no 'example/file.py', no 'TBD', no generic bracketed names) -- name "
        "real, specific things or say plainly that something is not yet determined.\n\n"
        "Write markdown sections with these exact headers, in this order, covering everything "
        "EXCEPT file impacts (the caller renders those separately from your JSON block): "
        "Goal, Requirement mapping, Current implementation, Missing implementation, "
        "Future/excluded scope, Architecture, API impact, DB/migration impact, UI impact, "
        "Security, Tests, Runtime/App Runner, Browser/Playwright verification, Risks, Delivery, "
        "Acceptance criteria.\n\n"
        "After the prose, append one fenced ```json block: "
        '{"file_impacts": [{"path": "...", "action": "CREATE_NEW|MODIFY_EXISTING|REFERENCE_ONLY|NO_CHANGE", '
        '"language": "...", "rationale": "...", "dependencies": [...], "verification": "..."}]}. '
        "Only propose MODIFY_EXISTING/DELETE_EXISTING for paths you can see verified in the "
        "Evidence Ledger or repository context below -- otherwise use CREATE_NEW or REFERENCE_ONLY."
    )
    user_content = f"Requirement:\n{project_description}"
    if evidence_ledger_block:
        user_content += f"\n\n{evidence_ledger_block}"
    if architecture_summary:
        user_content += f"\n\nDetected repository architecture:\n{architecture_summary}"
    if repo_context:
        user_content += f"\n\nRepository context:\n{repo_context[:6000]}"
    if constraints:
        user_content += f"\n\nConstraints:\n{constraints}"

    combined_context = evidence_ledger_block + architecture_summary + repo_context + constraints
    context_tokens = estimate_tokens(combined_context) + estimate_tokens(project_description)
    # PLAN is inherently more consequential than a lightweight ASK -- never
    # trivial by default -- and escalates to COMPLEX on either an explicit
    # signal from the caller (developer_service.py knows real file-impact/
    # repo-size counts) or a large enough context on its own, so a big CMS
    # PLAN is eligible for the strongest configured model even if nobody
    # bothered to pass complexity explicitly.
    resolved_complexity = complexity or (COMPLEXITY_COMPLEX if context_tokens > 3000 else COMPLEXITY_MODERATE)
    task = TaskProfile(
        task_type=TASK_PLAN, phase="plan", complexity=resolved_complexity,
        repo_language=repo_language, repo_size_files=repo_size_files,
        context_tokens_estimate=context_tokens,
    )
    out = _chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=3500,
        temperature=0.3,
        task=task,
    )
    if not out.get("ok"):
        return {
            "narrative": "",
            "proposed_file_impacts": [],
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
            "telemetry": out.get("telemetry"),
            "error": out.get("error"),
        }

    content = out["content"]
    narrative, proposed = _split_narrative_and_file_impacts(content)
    return {
        "narrative": narrative,
        "proposed_file_impacts": proposed,
        "model": out["model"],
        "tokens_used": out["tokens_used"],
        "offline": False,
        "telemetry": out.get("telemetry"),
    }


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _split_narrative_and_file_impacts(content: str) -> tuple[str, list[dict[str, Any]]]:
    import json as _json

    m = _JSON_FENCE_RE.search(content)
    if not m:
        return content.strip(), []
    narrative = (content[: m.start()] + content[m.end() :]).strip()
    try:
        data = _json.loads(m.group(1))
    except _json.JSONDecodeError:
        return narrative, []
    impacts = data.get("file_impacts") if isinstance(data, dict) else None
    return narrative, list(impacts) if isinstance(impacts, list) else []


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
