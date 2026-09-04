"""CP-08 -- the canonical, task-aware Model Router for ASK/PLAN/AGENT.

Before this module, every phase (ASK, PLAN, and every AGENT role -- Coder,
Debugger, Tester) resolved a model through the exact same call:
`mentrix_llm_chat_model()` (one global, env-var-driven default, "gpt-4o-mini"
if unset) fed into `fallback_policy.resolve_model_route()`, which only
decides *local vs. cloud*, never *which* model fits the task. A one-line
classification question and a large multi-file Java PLAN got the identical
model, purely because that happened to be the UI's configured default --
not because anyone decided a cheap/fast model was fine for the big job.

This module adds the missing axis -- task type + complexity + context size
+ vision/tool-calling requirement + privacy requirement -- on top of, not
instead of, `fallback_policy`'s existing local/cloud policy gate (`never`/
`ask`/`automatic`, env `ZECT_MODEL_FALLBACK_POLICY`): that system already
answers "is cloud reachable and permitted at all," tested and relied on
elsewhere (test_mentrix_p0_consolidation.py), and CP-08 has no reason to
replace it. `route_model()` calls it once per candidate to decide whether
that candidate's provider tier is usable right now.

No silent fallback: every model this function rejects is recorded as a
`RoutingStep` with a reason, in order, ending in either the accepted model
or `blocked=True` with `findings` exhausted -- a caller can always answer
"requested model -> fallback candidate -> reason -> policy decision" from
one `ModelRouteDecision`. A privacy requirement of `local_only` that finds
no local provider configured is a BLOCK, never a quiet substitution to
whatever cloud model happens to be reachable.

Deterministic work stays out of the LLM: this module never calls a model
to decide which model to call. Callers own computing repo size/language/
context length themselves (already deterministic, filesystem-driven work
via plan_generator.detect_repo_architecture and friends) and hand this
module a `TaskProfile` built from those numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Task taxonomy -- the mandate's "at minimum distinguish" list.
# ---------------------------------------------------------------------------

TASK_LIGHTWEIGHT_ASK = "lightweight_ask"      # classification/summarization
TASK_DEEP_ASK = "deep_ask"                    # deep repository ASK/reconciliation
TASK_PLAN = "plan"                            # architecture/PLAN
TASK_MULTI_FILE_CODING = "multi_file_coding"  # large multi-file AGENT coding
TASK_DEBUGGING = "debugging"
TASK_REVIEW_SECURITY = "review_security"
TASK_VISION_BROWSER = "vision_browser"        # vision/browser analysis

TASK_TYPES = frozenset(
    {
        TASK_LIGHTWEIGHT_ASK,
        TASK_DEEP_ASK,
        TASK_PLAN,
        TASK_MULTI_FILE_CODING,
        TASK_DEBUGGING,
        TASK_REVIEW_SECURITY,
        TASK_VISION_BROWSER,
    }
)

COMPLEXITY_TRIVIAL = "trivial"
COMPLEXITY_MODERATE = "moderate"
COMPLEXITY_COMPLEX = "complex"

PRIVACY_NONE = ""
PRIVACY_LOCAL_ONLY = "local_only"

# Routing modes -- re-exported from agent_model_adapter so callers only ever
# import mode constants from one place; POLICY_PINNED/LOCAL_ONLY there keep
# their exact existing behavior (this module composes with them, not around
# them -- see route_model()'s handling below).
from app.adapters.llm.agent_model_adapter import (  # noqa: E402
    AUTO_ROUTED,
    LOCAL_ONLY,
    POLICY_PINNED,
    USER_SELECTED,
)


@dataclass
class TaskProfile:
    """The routing INPUT -- every dimension the mandate lists, computed by
    the caller (deterministically, from things it already knows: repo file
    counts/language from plan_generator, context/evidence sizes from
    ContextPackage, goal length) rather than guessed by this module."""

    task_type: str
    phase: str = ""                      # "ask" | "plan" | "agent" -- for telemetry/audit
    role: str = ""                       # "coder" | "debugger" | "tester" | "" -- for telemetry/audit
    complexity: str = COMPLEXITY_MODERATE
    repo_size_files: int = 0
    repo_language: str = ""
    context_tokens_estimate: int = 0
    needs_vision: bool = False
    needs_tool_calling: bool = False
    privacy_requirement: str = PRIVACY_NONE
    latency_sensitivity: str = "normal"  # "low" | "normal" | "high"
    cost_sensitivity: str = "normal"     # "low" | "normal" | "high"

    def __post_init__(self) -> None:
        if self.task_type not in TASK_TYPES:
            raise ValueError(f"unknown task_type: {self.task_type!r}")
        if self.task_type == TASK_VISION_BROWSER:
            self.needs_vision = True
        if self.task_type in (TASK_MULTI_FILE_CODING, TASK_DEBUGGING, TASK_VISION_BROWSER):
            self.needs_tool_calling = True


@dataclass
class ModelCapability:
    """Routing-relevant metadata per model. cost_per_1k_input/output and
    quality/speed are intentionally sourced from the existing
    app.domains.agent_run.model_selection.MODELS registry where a matching
    entry exists (see _seed_capabilities below) rather than re-typed here --
    CP-08 adds the axes that registry never needed (reasoning_tier, vision,
    tool-calling, context window, local-only), it doesn't duplicate cost data.
    """

    model: str
    provider: str  # "anthropic" | "openai_compat" | "mentrix_local"
    reasoning_tier: int  # 1 (weak) .. 5 (strongest) -- the "coding/reasoning requirement" axis
    supports_vision: bool
    supports_tool_calling: bool
    context_window: int
    cost_tier: int  # 1 (cheapest) .. 5 (most expensive), relative
    latency_tier: int  # 1 (fastest) .. 5 (slowest)
    local_only: bool = False  # can this model satisfy a `local_only` privacy requirement?

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "reasoning_tier": self.reasoning_tier,
            "supports_vision": self.supports_vision,
            "supports_tool_calling": self.supports_tool_calling,
            "context_window": self.context_window,
            "cost_tier": self.cost_tier,
            "latency_tier": self.latency_tier,
            "local_only": self.local_only,
        }


def _seed_capabilities() -> dict[str, ModelCapability]:
    # Anthropic -- the strongest configured coding/reasoning tier lives
    # here. claude-opus-5 is not yet in model_selection.MODELS (that
    # registry predates it), added here since CP-08 explicitly must make
    # the strongest model eligible for complex PLAN/multi-file AGENT work.
    caps = {
        "claude-opus-5": ModelCapability(
            model="claude-opus-5", provider="anthropic", reasoning_tier=5,
            supports_vision=True, supports_tool_calling=True, context_window=200_000,
            cost_tier=5, latency_tier=4,
        ),
        "claude-sonnet-5": ModelCapability(
            model="claude-sonnet-5", provider="anthropic", reasoning_tier=4,
            supports_vision=True, supports_tool_calling=True, context_window=200_000,
            cost_tier=3, latency_tier=3,
        ),
        "claude-haiku-4-5-20251001": ModelCapability(
            model="claude-haiku-4-5-20251001", provider="anthropic", reasoning_tier=2,
            supports_vision=True, supports_tool_calling=True, context_window=200_000,
            cost_tier=1, latency_tier=1,
        ),
        # OpenAI-compatible cloud (mentrix_llm_chat_model()'s current default lives here)
        "gpt-4o": ModelCapability(
            model="gpt-4o", provider="openai_compat", reasoning_tier=4,
            supports_vision=True, supports_tool_calling=True, context_window=128_000,
            cost_tier=4, latency_tier=3,
        ),
        "gpt-4o-mini": ModelCapability(
            model="gpt-4o-mini", provider="openai_compat", reasoning_tier=2,
            supports_vision=True, supports_tool_calling=True, context_window=128_000,
            cost_tier=1, latency_tier=1,
        ),
    }
    # Mentrix Local LLM gateway models -- the only local_only=True candidates.
    # Conservative capability assumptions (no vision; tool-calling depends on
    # the specific local weights/gateway, so left False rather than assumed).
    try:
        from app.adapters.llm.openai_compat import MENTRIX_LOCAL_MODELS

        for entry in MENTRIX_LOCAL_MODELS:
            model_id = str(entry.get("id") or "")
            if not model_id or model_id in caps:
                continue
            caps[model_id] = ModelCapability(
                model=model_id, provider="mentrix_local", reasoning_tier=2,
                supports_vision=False, supports_tool_calling=False, context_window=32_000,
                cost_tier=1, latency_tier=2, local_only=True,
            )
    except Exception:  # noqa: BLE001 -- capability seeding must never crash import
        pass
    return caps


MODEL_CAPABILITIES: dict[str, ModelCapability] = _seed_capabilities()

# Per task type, the ORDER of models to try -- highest-priority-fit first.
# Complexity can escalate a task into a stronger tier (see _candidate_order).
_BASE_CANDIDATES: dict[str, list[str]] = {
    TASK_LIGHTWEIGHT_ASK: ["claude-haiku-4-5-20251001", "gpt-4o-mini", "claude-sonnet-5", "gpt-4o"],
    TASK_DEEP_ASK: ["claude-sonnet-5", "gpt-4o", "claude-opus-5", "claude-haiku-4-5-20251001", "gpt-4o-mini"],
    TASK_PLAN: ["claude-sonnet-5", "claude-opus-5", "gpt-4o", "claude-haiku-4-5-20251001", "gpt-4o-mini"],
    TASK_MULTI_FILE_CODING: ["claude-sonnet-5", "claude-opus-5", "gpt-4o", "claude-haiku-4-5-20251001", "gpt-4o-mini"],
    TASK_DEBUGGING: ["claude-sonnet-5", "claude-opus-5", "gpt-4o", "claude-haiku-4-5-20251001", "gpt-4o-mini"],
    TASK_REVIEW_SECURITY: ["claude-sonnet-5", "claude-opus-5", "gpt-4o", "gpt-4o-mini"],
    TASK_VISION_BROWSER: ["claude-sonnet-5", "gpt-4o", "claude-opus-5", "claude-haiku-4-5-20251001"],
}

# Complexity=complex promotes PLAN/MULTI_FILE_CODING/DEBUGGING to lead with
# the single strongest reasoning tier available, instead of merely trying
# it second -- the mandate's explicit "must be eligible for the strongest
# configured coding/reasoning model, do not default to small/cheap" rule.
_COMPLEX_PROMOTES_TO_TOP: frozenset[str] = frozenset(
    {TASK_PLAN, TASK_MULTI_FILE_CODING, TASK_DEBUGGING, TASK_DEEP_ASK}
)


@dataclass
class RoutingStep:
    model: str
    reason: str
    accepted: bool

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "reason": self.reason, "accepted": self.accepted}


@dataclass
class ModelRouteDecision:
    task_type: str
    requested_model: str
    selected_model: str
    selected_provider: str
    routing_reason: str
    chain: list[RoutingStep] = field(default_factory=list)
    policy_decision: str = "allowed"  # "allowed" | "blocked"
    blocked: bool = False
    block_reason: str = ""
    context_budget: int = 0

    @property
    def ok(self) -> bool:
        return not self.blocked

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "requested_model": self.requested_model,
            "selected_model": self.selected_model,
            "selected_provider": self.selected_provider,
            "routing_reason": self.routing_reason,
            "chain": [s.to_dict() for s in self.chain],
            "policy_decision": self.policy_decision,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "context_budget": self.context_budget,
        }


def _local_only_model_ids() -> list[str]:
    return [m for m, cap in MODEL_CAPABILITIES.items() if cap.local_only]


def _candidate_order(task: TaskProfile) -> list[str]:
    order = list(_BASE_CANDIDATES.get(task.task_type, [TASK_LIGHTWEIGHT_ASK]))
    # Local-only models never appear in _BASE_CANDIDATES (they're a weaker
    # reasoning tier no task should prefer by default) but must still be
    # reachable candidates -- otherwise a `local_only` privacy requirement
    # could never succeed even when the local gateway IS configured, which
    # would make every privacy-scoped task BLOCK unconditionally instead of
    # routing to the one tier that's actually allowed to serve it.
    order = order + [m for m in _local_only_model_ids() if m not in order]
    if task.complexity == COMPLEXITY_COMPLEX and task.task_type in _COMPLEX_PROMOTES_TO_TOP:
        # Reorder by reasoning_tier descending, strongest first -- promotes
        # claude-opus-5 to the very front instead of wherever the base list
        # happened to put it.
        order = sorted(
            order,
            key=lambda m: -(MODEL_CAPABILITIES[m].reasoning_tier if m in MODEL_CAPABILITIES else 0),
        )
    return order


def _provider_configured(provider: str, *, policy: str | None, user_allows_cloud: bool | None) -> tuple[bool, str]:
    """Is this candidate's provider actually usable right now?

    `mentrix_local` is the only LOCAL tier -- always usable once configured,
    no policy gate needed (that's the whole point of local). `anthropic`
    and `openai_compat` are both CLOUD tiers and share the exact same
    fallback_policy.resolve_model_route() never/ask/automatic gate a plain
    provider-availability check would miss entirely: `ZECT_MODEL_FALLBACK_
    POLICY=never` must block Anthropic just as much as OpenAI when no local
    model is configured -- this module adds task-fit on top of that gate,
    it does not carve out a second, laxer cloud policy for Anthropic.
    """
    if provider == "mentrix_local":
        from app.adapters.llm.openai_compat import mentrix_local_llm_configured

        configured = mentrix_local_llm_configured()
        return configured, "" if configured else "mentrix_local_not_configured"

    if provider in ("anthropic", "openai_compat"):
        from app.services.work_items.fallback_policy import resolve_model_route

        if provider == "anthropic":
            from app.adapters.llm.anthropic_client import anthropic_available

            cloud_configured = anthropic_available()
        else:
            import os

            # Matches llm_phase._route()'s existing cloud_configured check
            # exactly (OPENAI_API_KEY only) -- the Mentrix Local gateway is
            # its own candidate/provider tier ("mentrix_local" above), not
            # a second way to satisfy the openai_compat cloud tier's policy.
            cloud_configured = bool((os.getenv("OPENAI_API_KEY") or "").strip())

        route = resolve_model_route(
            local_configured=False,  # this branch is specifically about a CLOUD tier's policy gate
            cloud_configured=cloud_configured,
            policy=policy,
            user_allows_cloud=user_allows_cloud,
        )
        if route.blocked or route.provider == "none":
            return False, route.block_reason or f"{provider}_policy_blocked"
        return True, ""

    return False, f"unknown_provider:{provider}"


def route_model(
    task: TaskProfile,
    *,
    mode: str = AUTO_ROUTED,
    requested_model: str = "",
    policy: str | None = None,
    user_allows_cloud: bool | None = None,
) -> ModelRouteDecision:
    """The one function ASK/PLAN/AGENT call instead of hard-coding a model.

    `Mode` composes with agent_model_adapter's existing modes rather than
    reinventing them:
      POLICY_PINNED -- ZECT_AGENT_MODEL_PIN wins outright, recorded as a
                       single accepted step; the router does not second-
                       guess an operator's explicit pin.
      LOCAL_ONLY / task.privacy_requirement == "local_only" -- candidates
                       are filtered to local_only=True models only; if none
                       are configured, this BLOCKS -- it never substitutes
                       a reachable cloud model for a privacy-scoped task.
      USER_SELECTED -- `requested_model` leads the chain; if unavailable,
                       falls through to the task's normal candidate order
                       (each rejected step recorded) unless a privacy/local
                       constraint forbids it, in which case it BLOCKS.
      AUTO_ROUTED   -- the task's candidate order is used from the start.
    """
    chain: list[RoutingStep] = []

    if mode == POLICY_PINNED:
        import os

        pinned = os.getenv("ZECT_AGENT_MODEL_PIN", "").strip()
        if pinned:
            cap = MODEL_CAPABILITIES.get(pinned)
            chain.append(RoutingStep(model=pinned, reason="policy_pinned_override", accepted=True))
            return ModelRouteDecision(
                task_type=task.task_type, requested_model=requested_model or pinned, selected_model=pinned,
                selected_provider=(cap.provider if cap else "unknown"), routing_reason="policy_pinned_override",
                chain=chain, policy_decision="allowed", context_budget=(cap.context_window if cap else 0),
            )

    local_only_required = mode == LOCAL_ONLY or task.privacy_requirement == PRIVACY_LOCAL_ONLY

    candidates = _candidate_order(task)
    if requested_model:
        # USER_SELECTED (or any mode carrying an explicit ask) tries that
        # model first, then falls through to the task's normal order --
        # never silently swapped for a same-tier model instead.
        candidates = [requested_model] + [c for c in candidates if c != requested_model]

    for model in candidates:
        cap = MODEL_CAPABILITIES.get(model)
        if cap is None:
            chain.append(RoutingStep(model=model, reason="unknown_model_capability", accepted=False))
            continue
        if local_only_required and not cap.local_only:
            chain.append(RoutingStep(model=model, reason="privacy_requires_local_only", accepted=False))
            continue
        if task.needs_vision and not cap.supports_vision:
            chain.append(RoutingStep(model=model, reason="vision_not_supported", accepted=False))
            continue
        if task.needs_tool_calling and not cap.supports_tool_calling:
            chain.append(RoutingStep(model=model, reason="tool_calling_not_supported", accepted=False))
            continue
        if task.context_tokens_estimate and task.context_tokens_estimate > cap.context_window:
            chain.append(RoutingStep(model=model, reason="context_window_insufficient", accepted=False))
            continue
        configured, reason = _provider_configured(cap.provider, policy=policy, user_allows_cloud=user_allows_cloud)
        if not configured:
            chain.append(RoutingStep(model=model, reason=reason or "provider_not_configured", accepted=False))
            continue

        accept_reason = (
            "requested_model_available" if model == requested_model
            else f"best_fit_for_{task.task_type}_complexity_{task.complexity}"
        )
        chain.append(RoutingStep(model=model, reason=accept_reason, accepted=True))
        return ModelRouteDecision(
            task_type=task.task_type, requested_model=requested_model or model, selected_model=model,
            selected_provider=cap.provider, routing_reason=accept_reason, chain=chain,
            policy_decision="allowed", context_budget=cap.context_window,
        )

    # Every candidate was rejected -- block, do not silently downgrade to
    # something not on the list (e.g. the bare openai_compat default).
    block_reason = (
        "no_local_provider_configured_for_privacy_requirement" if local_only_required
        else "no_configured_model_satisfies_task_requirements"
    )
    return ModelRouteDecision(
        task_type=task.task_type, requested_model=requested_model, selected_model="", selected_provider="",
        routing_reason=block_reason, chain=chain, policy_decision="blocked", blocked=True,
        block_reason=block_reason,
    )


def estimate_tokens(text: str) -> int:
    """Deterministic, non-LLM context-size estimate (~4 chars/token, the
    common rough heuristic) -- good enough for routing decisions; never
    used for anything billing-accurate."""
    return max(0, len(text or "")) // 4


def estimate_cost_usd(model: str, *, input_tokens: int, output_tokens: int) -> float:
    """Best-effort cost estimate reusing the SAME per-model rate card the
    Token Controls UI already shows (app.domains.agent_run.model_selection.
    MODELS), instead of yet a third hardcoded pricing table -- falls back to
    0.0 (not a wrong-model's price, unlike token_tracker.PRICING's silent
    gpt-4o-mini default) when the model has no known rate."""
    try:
        from app.domains.agent_run.model_selection import MODELS

        for entry in MODELS:
            if entry.get("id") == model:
                cin = float(entry.get("cost_per_1k_input") or 0.0)
                cout = float(entry.get("cost_per_1k_output") or 0.0)
                return round((input_tokens / 1000.0) * cin + (output_tokens / 1000.0) * cout, 6)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


def to_telemetry_fields(
    decision: ModelRouteDecision,
    *,
    phase: str = "",
    role: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    latency_ms: int = 0,
) -> dict[str, Any]:
    """Exactly the field set the mandate requires be recorded on Mission/
    EventStream: phase, role, provider, model, routing reason, context
    budget, input/output/cached tokens, estimated cost, latency."""
    return {
        "phase": phase,
        "role": role,
        "provider": decision.selected_provider,
        "model": decision.selected_model,
        "routing_reason": decision.routing_reason,
        "context_budget": decision.context_budget,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "estimated_cost": estimate_cost_usd(decision.selected_model, input_tokens=input_tokens, output_tokens=output_tokens),
        "latency_ms": latency_ms,
    }
