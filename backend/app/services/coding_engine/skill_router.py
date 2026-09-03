"""CP-09B -- Skills Router: Mission phase/role -> intent -> selected skill.

Canonical flow the mandate names: Mission -> phase/role/task -> Skill
Router -> selected skill -> instructions/context/tool requirements/checks
-> Model Router -> Tool Governance. This module is only the first arrow:
it turns a role plus a few deterministic signals into an *intent* string
(no LLM call), then reuses the existing DB-backed Skills Engine
(skills_engine.py's SEED_SKILLS + trigger_pattern scoring, already proven
by /api/skills-engine/match) to pick a skill and return the manifest
fragments the caller may fold into its own goal/context string.

Deliberately excluded from this module, by construction, is anything that
grants execution: no import of mentrix_agent_tools, agent_write_policy, or
ROLE_TOOL_ALLOWLISTS. A skill's manifest["allowed_tools"]/config are
descriptive hints a prompt can mention -- CODER/TESTER/DEBUGGER's actual
tool set still comes only from mentrix_lead.ROLE_TOOL_ALLOWLISTS, and every
write still passes through AgentWritePolicy. Selecting a skill can add
instructions and context; it cannot expand what a role is allowed to do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

ROLE_ASK = "ask"
ROLE_PLAN = "plan"
ROLE_EXPLORE = "explore"
ROLE_CODER = "coder"
ROLE_TESTER = "tester"
ROLE_DEBUGGER = "debugger"
ROLE_REVIEWER = "reviewer"
ROLE_DELIVERY = "delivery"

# Deterministic role -> base intent phrase, deliberately built out of the
# same words as the skill's own trigger_pattern so the existing
# substring/word-overlap scorer in skills_engine.match_skills (and the
# copy of that scoring reused below) lands on the intended skill without
# any model call.
_ROLE_INTENT: dict[str, str] = {
    ROLE_ASK: "reconcile evidence ledger ask",
    ROLE_PLAN: "grounded plan file impact approved plan plan validation",
    ROLE_EXPLORE: "explore repo architecture index lattice",
    ROLE_CODER: "build implement multi file coding",
    ROLE_TESTER: "browser test playwright acceptance ui screenshot",
    ROLE_DEBUGGER: "debug error exception traceback bug investigate",
    ROLE_REVIEWER: "code review pull_request lint quality",
    ROLE_DELIVERY: "pr ready delivery readiness",
}

# Structured, deterministic signals that refine intent beyond the base
# role -- still no model call. A caller sets these from facts it already
# has (a failing test, a browser-acceptance pass, a diff touching a
# schema/BPMN/security-sensitive path), never from an LLM guess.
_SIGNAL_INTENT_SUFFIX: dict[str, str] = {
    "test_failed": " debug error exception traceback bug investigate",
    "browser_acceptance": " browser test playwright acceptance ui screenshot",
    "ui_diff": " ui review layout overflow visual regression clipping",
    "security_sensitive": " security review vulnerability scan secrets exposure auth sensitive",
    "db_schema_diff": " database schema migration review db review",
    "bpmn_diff": " bpmn camunda workflow process review",
    "prompt_diff": " prompt engineer optimize prompt prompt optimization",
}

# These signals name a specialized review skill that must win outright,
# not merely nudge the score -- e.g. a security-sensitive diff on a CODER
# turn must route to zect-security-review, not tie with (and lose ties to,
# by insertion order) zect-build. Kept separate from test_failed/
# browser_acceptance, which genuinely extend their own role's base intent
# rather than swap in a different specialist.
_OVERRIDE_SIGNALS = frozenset(
    {"ui_diff", "security_sensitive", "db_schema_diff", "bpmn_diff", "prompt_diff"}
)


@dataclass
class SkillSelection:
    role: str
    intent: str
    skill_name: Optional[str]
    skill_version: Optional[str]
    skill_id: Optional[int]
    score: int
    reason: str
    instructions: str = ""
    context_added: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def to_event_data(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "intent": self.intent,
            "skill_name": self.skill_name,
            "skill_source_version": self.skill_version,
            "skill_id": self.skill_id,
            "score": self.score,
            "selection_reason": self.reason,
            "context_added": self.context_added,
            "checks_invoked": self.checks,
        }

    def goal_prefix(self) -> str:
        """A short, prompt-safe prefix a caller may prepend to its own
        goal/context string. Empty when no skill matched -- callers must
        not fabricate instructions for a skill that wasn't found."""
        if not self.skill_name or not self.instructions:
            return ""
        return f"SKILL ({self.skill_name} v{self.skill_version}): {self.instructions}\n\n"


def build_intent(role: str, signals: Optional[dict[str, bool]] = None) -> str:
    if signals:
        overrides = [key for key in _OVERRIDE_SIGNALS if signals.get(key)]
        if overrides:
            return " ".join(_SIGNAL_INTENT_SUFFIX[key].strip() for key in overrides)
    intent = _ROLE_INTENT.get(role, role)
    for key, suffix in _SIGNAL_INTENT_SUFFIX.items():
        if key not in _OVERRIDE_SIGNALS and signals and signals.get(key):
            intent += suffix
    return intent


def _score_skill(trigger_pattern: str, intent_lower: str) -> int:
    score = 0
    for p in (trigger_pattern or "").split("|"):
        p_clean = p.strip().replace(".", " ").lower()
        if not p_clean:
            continue
        if p_clean in intent_lower:
            score += 2
        elif any(w in intent_lower for w in p_clean.split()):
            score += 1
    return score


def select_skill(
    role: str,
    *,
    signals: Optional[dict[str, bool]] = None,
    project_id: Optional[int] = None,
) -> SkillSelection:
    """Deterministic skill selection for a Mission/WorkItem role. Opens its
    own short-lived DB session -- lifecycle.py is intentionally
    DB-decoupled (same pattern agent_write_policy.build_agent_write_policy
    uses), and developer_service.py already has a `self.db` it can pass
    through instead via `select_skill_with_db`."""
    from app.infrastructure.database import SessionLocal

    db = SessionLocal()
    try:
        return select_skill_with_db(db, role, signals=signals, project_id=project_id)
    finally:
        db.close()


def select_skill_with_db(
    db,
    role: str,
    *,
    signals: Optional[dict[str, bool]] = None,
    project_id: Optional[int] = None,
) -> SkillSelection:
    from app.domains.personal_agent.skills_engine import SkillDefinition, _seed_if_empty, _skill_to_dict

    intent = build_intent(role, signals)
    _seed_if_empty(db)
    query = db.query(SkillDefinition).filter(
        SkillDefinition.is_active == True,  # noqa: E712
        SkillDefinition.trigger_pattern != "",
    )
    if project_id is not None:
        query = query.filter(
            (SkillDefinition.project_id == None) | (SkillDefinition.project_id == project_id)  # noqa: E711
        )
    all_skills = query.all()

    intent_lower = intent.lower()
    best = None
    best_score = 0
    for s in all_skills:
        score = _score_skill(s.trigger_pattern, intent_lower)
        if score > best_score:
            best_score = score
            best = s

    if best is None:
        return SkillSelection(
            role=role,
            intent=intent,
            skill_name=None,
            skill_version=None,
            skill_id=None,
            score=0,
            reason="no_skill_matched_intent",
        )

    d = _skill_to_dict(best)
    manifest = d.get("manifest") or {}
    return SkillSelection(
        role=role,
        intent=intent,
        skill_name=d["name"],
        skill_version=d["version"],
        skill_id=d["id"],
        score=best_score,
        reason=f"trigger_pattern_match:{d['trigger_pattern']}",
        instructions=d.get("description", "") or "",
        context_added=list(manifest.get("outputs") or []),
        checks=list((manifest.get("config") or {}).get("checks") or []),
    )
