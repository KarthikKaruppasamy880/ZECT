"""Mentrix Automation Loops — thin ZECT-native loop runtime (concepts from loop-engineering MIT patterns).

Does not replace ForgeLoop, WorkItem, PersonalAction, Skills, Memory, Scheduler,
Permission Broker, or EvidenceVerifier. Cadence reuses Schedule; state persists in
LoopDefinition / LoopRun (+ checkpoint JSON). No STATE.md second store.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

AUTONOMY_L0 = "L0"  # Observe
AUTONOMY_L1 = "L1"  # Recommend
AUTONOMY_L2 = "L2"  # Assisted
AUTONOMY_L3 = "L3"  # Autonomous

AUTONOMY_LEVELS = (AUTONOMY_L0, AUTONOMY_L1, AUTONOMY_L2, AUTONOMY_L3)

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_KILLED = "killed"
STATUS_NEEDS_HUMAN = "NEEDS_HUMAN_DECISION"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


@dataclass
class LoopBudget:
    """Hard caps — loops must not complete on LLM claim alone."""

    max_runtime_seconds: int = 300
    max_tokens: int = 50_000
    max_cost_usd: float = 5.0
    max_actions: int = 20
    max_retries: int = 3
    max_same_failure: int = 3
    max_files_changed: int = 200
    max_coder_test_cycles: int = 3
    max_coder_review_cycles: int = 3
    no_progress_threshold: int = 2

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LoopTrigger:
    kind: str = "manual"  # manual | schedule | event
    schedule_task_type: str = ""
    event_name: str = ""
    cron: str = ""
    interval_minutes: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LoopPolicy:
    """Permission + autonomy gate — L2/L3 require explicit allow."""

    autonomy_level: str = AUTONOMY_L0
    require_human_gate: bool = True
    allow_l2: bool = False
    allow_l3: bool = False
    permission_requirement: str = "require_approval"
    user_scoped: bool = True
    org_scoped: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def effective_level(self, requested: str | None = None) -> str:
        req = (requested or self.autonomy_level or AUTONOMY_L0).upper()
        if req not in AUTONOMY_LEVELS:
            req = AUTONOMY_L0
        if req == AUTONOMY_L3 and not self.allow_l3:
            return AUTONOMY_L1 if self.allow_l2 is False else (AUTONOMY_L2 if self.allow_l2 else AUTONOMY_L1)
        if req == AUTONOMY_L2 and not self.allow_l2:
            return AUTONOMY_L1
        return req


@dataclass
class LoopCheckpoint:
    iteration: int = 0
    phase: str = "init"
    state: dict[str, Any] = field(default_factory=dict)
    last_error: str = ""
    same_failure_count: int = 0
    actions_used: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d.get("updated_at"):
            d["updated_at"] = datetime.now(timezone.utc).isoformat()
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "LoopCheckpoint":
        raw = raw or {}
        return cls(
            iteration=int(raw.get("iteration") or 0),
            phase=str(raw.get("phase") or "init"),
            state=dict(raw.get("state") or {}),
            last_error=str(raw.get("last_error") or ""),
            same_failure_count=int(raw.get("same_failure_count") or 0),
            actions_used=int(raw.get("actions_used") or 0),
            tokens_used=int(raw.get("tokens_used") or 0),
            cost_usd=float(raw.get("cost_usd") or 0),
            updated_at=str(raw.get("updated_at") or ""),
        )


class CircuitBreaker:
    """Trip to NEEDS_HUMAN_DECISION after repeated identical failures."""

    def __init__(self, max_same_failure: int = 3):
        self.max_same_failure = max(1, int(max_same_failure))

    def record(self, checkpoint: LoopCheckpoint, error: str) -> tuple[LoopCheckpoint, bool]:
        err = (error or "").strip()[:500]
        if err and err == checkpoint.last_error:
            checkpoint.same_failure_count += 1
        else:
            checkpoint.last_error = err
            checkpoint.same_failure_count = 1 if err else 0
        tripped = bool(err) and checkpoint.same_failure_count >= self.max_same_failure
        return checkpoint, tripped
