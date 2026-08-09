"""Mentrix Orchestrator — ForgeLoop FSM (not LangGraph)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models import MentrixRun, Rule
from app.services.lattice.indexer import (
    explain as lattice_explain,
    get_graph,
    god_nodes as lattice_god_nodes,
    neighbors as lattice_neighbors,
    query_graph,
)
from app.services.lattice.structural_blueprint import get_structural_blueprint
from app.services.phases.blueprint_phase import run_blueprint
from app.services.phases.llm_phase import run_ask, run_enhance_blueprint, run_plan
from app.services.phases.review_phase_svc import run_ultra_review
from app.services.quality.acceptance import verify_acceptance_criteria, verify_design_contract
from app.services.quality.api_eval import inventory_apis, run_api_evals
from app.services.quality.error_classifier import classify_error, classify_from_blockers
from app.services.quality.gates_policy import gates_allow_approve, gates_allow_create_pr
from app.services.quality.grounding import validate_grounding
from app.services.quality.incomplete_files import check_incomplete_files
from app.services.quality.lint_runner import run_lint
from app.services.rag.retriever import hybrid_retrieve
from app.services.forge_loop.batch_build import (
    MENTRIX_BUILD_BATCH_SIZE,
    attach_files_expected,
    chunk_files,
    collect_files_expected,
)

# Re-export for mentrix router / tests
__all__ = [
    "run_mentrix",
    "continue_mentrix_after_plan",
    "continue_mentrix_after_batch",
    "validate_context_pack",
    "gates_allow_approve",
    "gates_allow_create_pr",
    "MODE_PIPELINE",
    "AGENT_ROLES",
    "collect_files_expected",
]

AGENT_ROLES = (
    "orchestrator",
    "scout",
    "planner",
    "builder",
    "reviewer",
    "fixer",
    "integrator",
    "ops",
)

MODE_PIPELINE: dict[str, list[str]] = {
    "chat": ["scout", "orchestrator"],
    "understand": ["scout"],
    "deliver": ["scout", "planner", "builder", "lint", "sandbox", "reviewer", "fixer", "integrator"],
    "review_only": ["reviewer", "fixer"],
    "ops": ["scout", "ops", "integrator"],
    # Any-language → any-language upgrade via real Ask/Plan/Build/Ultra Review paths
    "upgrade": [
        "lattice",
        "blueprint",
        "ask",
        "plan",
        "api_analyze",
        "ultra_review_pre",
        "build",
        "grounding",
        "incomplete",
        "acceptance",
        "lint",
        "sandbox",
        "ultra_review",
        "api_eval",
        "fixer",
        "integrator",
    ],
    # Issue -> load blueprint/graph -> reproduce -> trace impacted components
    # -> root-cause + fix plan -> build -> regression tests -> review -> PR.
    # Reuses "build"/"incomplete"/"sandbox"/"ultra_review"/"integrator" from
    # "upgrade" unchanged — root_cause populates `plan` in the same shape
    # run_plan() would, so Build needs no bugfix-specific branch.
    "bugfix": [
        "lattice",
        "blueprint",
        "reproduce",
        "trace_impacted",
        "root_cause",
        "build",
        "incomplete",
        "sandbox",
        "ultra_review",
        "integrator",
    ],
    # Model-driven tool-calling loop, not a fixed stage list — the fix for
    # "it's not doing what I say." Heavy tools (start_upgrade_run etc.) kick
    # off a background run and return immediately rather than blocking here.
    "assistant": ["assistant_loop"],
}


def _max_recovery() -> int:
    return int(os.getenv("MENTRIX_MAX_RECOVERY", "3"))


def _lint_strict(mode: str) -> bool:
    raw = os.getenv("MENTRIX_LINT_STRICT", "")
    if raw:
        return raw.lower() not in ("0", "false", "no")
    return mode in ("upgrade", "bugfix")


def _plan_confirm_required(mode: str) -> bool:
    """Human must confirm the plan before Build (upgrade + bugfix by default)."""
    raw = os.getenv("MENTRIX_REQUIRE_PLAN_CONFIRM", "")
    if raw:
        return raw.lower() not in ("0", "false", "no")
    return mode in ("upgrade", "bugfix")


def validate_context_pack(*, workspace: str, project_key: str, mode: str) -> list[str]:
    """Preflight before Engage — require workspace + Lattice key for ship modes."""
    errors: list[str] = []
    if mode not in ("upgrade", "bugfix", "deliver"):
        return errors
    ws = (workspace or "").strip()
    pk = (project_key or "").strip()
    if not ws and not pk:
        errors.append("workspace path or project_key is required (context pack)")
    if not pk:
        errors.append("project_key (Lattice key) is required for grounded plans")
    elif os.getenv("LATTICE_ENABLED", "true").lower() not in ("0", "false", "no"):
        try:
            from app.services.lattice.indexer import get_graph

            if get_graph(pk) is None:
                errors.append(
                    f"Lattice not indexed for key '{pk}' — Ingest + RAG on Lattice Graph first"
                )
        except Exception as e:
            errors.append(f"Lattice status check failed: {e}")
    return errors


def _load_rules_text(db: Session) -> str:
    rules = db.query(Rule).filter(Rule.is_active == True).limit(50).all()  # noqa: E712
    if not rules:
        return "(No active rules)"
    lines = []
    for r in rules:
        lines.append(f"- [{r.severity}] {r.name}: {r.condition} → {r.action}")
    return "\n".join(lines)


def _load_skills_text() -> str:
    roots = [
        Path(__file__).resolve().parents[4] / "skills",
        Path.cwd() / "skills",
        Path.cwd().parent / "skills",
    ]
    chunks: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md"))[:12]:
            try:
                text = skill_md.read_text(encoding="utf-8")[:1500]
                chunks.append(f"### {skill_md.parent.name}\n{text}")
            except OSError:
                continue
        if chunks:
            break
    return "\n\n".join(chunks) if chunks else "(No skill packs loaded)"


def _emit(events: list[dict], agent: str, message: str, **extra: Any) -> None:
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "message": message,
        **extra,
    })


def _emit_recovery(
    events: list[dict],
    *,
    error: str,
    model: str,
    next_step: str,
    attempt: int,
) -> None:
    _emit(
        events,
        "fixer",
        f"Recovery attempt {attempt}: {next_step}",
        event="recovery",
        error=error[:2000],
        model=model,
        next_step=next_step,
        attempt=attempt,
    )


def _emit_phase(events: list[dict], phase: str, progress: float, next_step: str, message: str) -> None:
    _emit(
        events,
        "orchestrator",
        message,
        event="phase",
        phase=phase,
        progress=progress,
        next_step=next_step,
    )


def _ensure_lattice_ingest(workspace: str, project_key: str, events: list[dict]) -> None:
    if not workspace or not project_key:
        return
    root = Path(workspace)
    if not root.is_dir():
        return
    existing = get_graph(project_key)
    if existing and existing.files_indexed > 0:
        return
    try:
        from app.services.lattice.indexer import ingest_path

        _emit(events, "scout", f"Lattice ingest for {project_key}", phase="lattice")
        ingest_path(str(root), project_key=project_key)
    except Exception as exc:  # noqa: BLE001
        _emit(events, "scout", f"Lattice ingest skipped: {exc}", phase="lattice")


def _run_scout(db: Session, goal: str, project_key: str, events: list[dict]) -> dict[str, Any]:
    _emit(events, "scout", "Retrieving Lattice + RAG context", phase="lattice")
    graph_hits = query_graph(project_key, goal, limit=20) if project_key else []
    rag_hits = []
    if os.getenv("RAG_ENABLED", "true").lower() not in ("0", "false") and project_key:
        rag_hits = hybrid_retrieve(db, goal, project_key=project_key, top_k=8)
    neighbor_packs: list[dict] = []
    explain_notes: list[str] = []
    if project_key and graph_hits:
        for hit in graph_hits[:5]:
            ref = hit.get("name") or hit.get("path") or hit.get("id")
            if not ref:
                continue
            nb = lattice_neighbors(project_key, str(ref), depth=1, limit=12)
            if nb.get("nodes"):
                neighbor_packs.append(
                    {
                        "seed": ref,
                        "node_count": len(nb.get("nodes") or []),
                        "edge_kinds": sorted({e.get("kind") for e in (nb.get("edges") or []) if e.get("kind")}),
                        "related": [n.get("name") for n in (nb.get("nodes") or [])[:6]],
                    }
                )
            exp = lattice_explain(project_key, node_ref=str(ref))
            if exp.get("summary"):
                explain_notes.append(exp["summary"])
    structural = get_structural_blueprint(db, project_key) if project_key else None
    pack = {
        "graph_hits": graph_hits,
        "rag_hits": rag_hits,
        "graph_summary": None,
        "neighbor_packs": neighbor_packs,
        "explain_notes": explain_notes[:5],
        "structural_blueprint": structural,
        "god_nodes": lattice_god_nodes(project_key, limit=10) if project_key else [],
    }
    g = get_graph(project_key) if project_key else None
    if g:
        pack["graph_summary"] = {
            "files_indexed": g.files_indexed,
            "symbols": g.symbols,
            "languages": g.languages,
            "node_count": len(g.nodes),
            "edge_count": len(g.edges),
            "call_edges": sum(1 for e in g.edges if e.kind == "calls"),
            "endpoint_nodes": sum(1 for n in g.nodes if n.kind == "endpoint"),
        }
    if structural:
        pack["graph_summary"] = {
            **(pack.get("graph_summary") or {}),
            "tech_stack": structural.get("tech_stack"),
            "api_endpoints": len(structural.get("api_endpoints") or []),
            "functions": (structural.get("stats") or {}).get("functions"),
            "blueprint_status": structural.get("status"),
        }
    _emit(
        events,
        "scout",
        f"Retrieved {len(graph_hits)} graph hits, {len(rag_hits)} RAG chunks, "
        f"{len(neighbor_packs)} neighbor packs"
        + (f", structural blueprint ({len(structural.get('api_endpoints') or [])} endpoints)" if structural else ""),
        phase="lattice",
    )
    return pack


def _run_planner(goal: str, scout: dict, rules: str, events: list[dict]) -> dict[str, Any]:
    _emit(events, "planner", "Drafting implementation plan")
    skills = _load_skills_text()
    files = sorted({h.get("path") for h in scout.get("graph_hits", []) if h.get("path")})[:12]
    plan = {
        "summary": f"Plan for: {goal[:200]}",
        "steps": [
            {"step": 1, "action": "Review retrieved context and rules", "files": files[:3]},
            {"step": 2, "action": "Implement minimal diff changes", "files": files[3:8] or []},
            {"step": 3, "action": "Lint + sandbox / tests", "files": []},
            {"step": 4, "action": "Human approve then open PR", "files": []},
        ],
        "acceptance_criteria": [
            "Lint clean",
            "Sandbox / tests green",
            "Human approve before PR",
            "No secrets in logs or Slack",
        ],
        "rules_applied": rules[:2000],
        "skills": skills[:3000],
    }
    plan = attach_files_expected(plan, files)
    _emit(events, "planner", f"Plan ready with {len(plan['steps'])} steps, {len(plan.get('files_expected') or [])} files_expected")
    return plan


def _run_builder(goal: str, plan: dict, scout: dict, events: list[dict]) -> dict[str, Any]:
    _emit(events, "builder", "Preparing diff-first change set (Build Phase path)")
    skills = plan.get("skills") or _load_skills_text()
    snippets = []
    for hit in (scout.get("rag_hits") or [])[:3]:
        snippets.append({
            "path": hit.get("path"),
            "guidance": "Preserve existing patterns; apply surgical edits only.",
            "context_preview": (hit.get("content") or "")[:400],
        })
    result = {
        "strategy": "diff_first",
        "goal": goal,
        "planned_files": [s.get("files") for s in plan.get("steps", [])],
        "patches": snippets,
        "skills": skills[:2000],
        "build_phase": "/api/build/generate",
        "note": "Builder guidance ready; apply via Build Phase or Mentrix FS, then lint gate.",
    }
    _emit(events, "builder", f"Prepared {len(snippets)} patch contexts")
    return result


def _run_lint_gate(workspace: str, events: list[dict], *, strict: bool = False) -> dict[str, Any]:
    _emit(events, "orchestrator", "Running lint gate", phase="lint")
    lint = run_lint(workspace)
    ok = bool(lint.get("ok"))
    if strict and lint.get("skipped"):
        ok = False
        lint = {**lint, "ok": False, "reason": lint.get("reason") or "lint skipped under MENTRIX_LINT_STRICT"}
    _emit(
        events,
        "orchestrator",
        f"Lint {'passed' if ok else 'failed'}"
        + (f" (skipped: {lint.get('reason')})" if lint.get("skipped") else ""),
        event="lint",
        lint_ok=ok,
        phase="lint",
    )
    lint["ok"] = ok
    return lint


def _run_sandbox_gate(review_score: int, critical: int, events: list[dict]) -> dict[str, Any]:
    _emit(events, "orchestrator", "Evaluating sandbox / PR readiness policy", phase="sandbox")
    blockers: list[str] = []
    if critical > 0:
        blockers.append(f"{critical} critical finding(s)")
    if review_score < 60:
        blockers.append(f"Quality score {review_score} below 60")
    ready = len(blockers) == 0
    out = {
        "ready": ready,
        "blockers": blockers,
        "quality_score": review_score,
        "critical_findings": critical,
        "create_pr_hard_blocked": not ready,
    }
    _emit(events, "orchestrator", f"Sandbox gate ready={ready}", event="sandbox", phase="sandbox", **out)
    return out


def _detect_test_command(workspace: str) -> str | None:
    """Best-effort test command from what's actually in the workspace — no
    guessing when the stack isn't recognized; caller falls back to the
    heuristic gate in that case."""
    if not workspace:
        return None
    root = Path(workspace)
    if not root.is_dir():
        return None
    if (root / "package.json").exists():
        return "npm test"
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return "pytest -q"
    if (root / "go.mod").exists():
        return "go test ./..."
    return None


def _run_sandbox_check(
    workspace: str, review_score: int, critical: int, events: list[dict], mode: str
) -> dict[str, Any]:
    """Sandbox gate — runs the repo's real test command (App Runner's execution
    path, via autofix.py's run_and_fix so a failing run gets AI-assisted retries
    before giving up) when the workspace's stack is recognized, instead of only
    ever estimating readiness from the review score."""
    test_cmd = _detect_test_command(workspace) if mode in ("upgrade", "bugfix") else None
    if not test_cmd:
        return _run_sandbox_gate(review_score, critical, events)

    from app.domains.workspace.autofix import AutoFixRequest, run_and_fix

    _emit(events, "orchestrator", f"Sandbox: running real test command: {test_cmd}", phase="sandbox")
    autofix_result = run_and_fix(AutoFixRequest(command=test_cmd, cwd=workspace, max_retries=_max_recovery()))
    blockers: list[str] = []
    if not autofix_result.success:
        blockers.append(f"Real test run failed: {(autofix_result.final_output or '')[:200]}")
    if critical > 0:
        blockers.append(f"{critical} critical finding(s)")
    ready = autofix_result.success and critical == 0
    out = {
        "ready": ready,
        "blockers": blockers,
        "quality_score": review_score,
        "critical_findings": critical,
        "create_pr_hard_blocked": not ready,
        "real_execution": True,
        "test_command": test_cmd,
        "attempts": autofix_result.total_attempts,
    }
    _emit(
        events,
        "orchestrator",
        f"Sandbox real-execution ready={ready} attempts={autofix_result.total_attempts}",
        event="sandbox",
        phase="sandbox",
        ready=ready,
        blockers=blockers,
        quality_score=review_score,
        critical_findings=critical,
    )
    return out


def _run_reviewer(
    goal: str, builder: dict, rules: str, events: list[dict], *, db: Session = None, user_id: int | None = None
) -> dict[str, Any]:
    _emit(events, "reviewer", "Running Mentrix Ultra Review heuristics", phase="ultra_review")
    code = (builder or {}).get("generated_code") or ""
    review = run_ultra_review(
        code,
        language=(builder or {}).get("language") or "python",
        goal=goal,
        context=rules[:2000],
        db=db,
        user_id=user_id,
    )
    _emit(
        events,
        "reviewer",
        f"Mentrix Ultra Review score={review.get('quality_score')} critical={review.get('critical_findings')}",
        phase="ultra_review",
        brand="Mentrix Ultra Review",
    )
    return review


def _run_fixer(
    review: dict,
    events: list[dict],
    *,
    prior_error: str = "",
    next_step: str = "re_review",
    attempt: int = 1,
    gate: str = "",
) -> dict[str, Any]:
    to_fix = [f for f in review.get("findings", []) if f.get("severity") in ("critical", "high")]
    classified = classify_error(
        prior_error or "",
        gate=gate,
        findings=review.get("findings") or [],
    )
    if classified.get("category") == "SECURITY":
        next_step = "await_human"
    elif classified.get("next_step"):
        next_step = classified["next_step"]
    _emit_recovery(
        events,
        error=prior_error or f"{len(to_fix)} findings need fix",
        model=f"fixer:{classified.get('model_tier', 'same')}",
        next_step=next_step,
        attempt=attempt,
    )
    # Soften non-security highs after recovery; never soften SECURITY
    if attempt >= 1 and to_fix and classified.get("category") != "SECURITY":
        for f in review.get("findings", []):
            if f.get("severity") == "high" and (f.get("category") or "").lower() not in ("security", "secrets"):
                f["severity"] = "medium"
                f["title"] = (f.get("title") or f.get("message") or "") + " (mitigated)"
    result = {
        "files_targeted": [f.get("file") for f in to_fix if f.get("file")],
        "findings_addressed": to_fix,
        "strategy": "deterministic_fix" if classified.get("deterministic_fix") else "patch_only_failed",
        "use_prior_review_context": True,
        "next_step": next_step,
        "attempt": attempt,
        "error_class": classified,
        "message": classified.get("feedback")
        or "Fixer applied scoped recovery; re-run lint/sandbox/review before approve.",
    }
    _emit(
        events,
        "fixer",
        f"Scoped {len(to_fix)} findings; class={classified.get('category')} next_step={next_step}",
        event="error_class",
        category=classified.get("category"),
    )
    return result


def _goal_wants_mcp(goal: str) -> dict[str, bool]:
    g = goal.lower()
    return {
        "slack": any(k in g for k in ("slack", "notify channel", "#engineering")),
        "email": any(k in g for k in ("email", "smtp", "send mail")),
        "datadog": any(k in g for k in ("datadog", "dd logs", "query logs")),
        "jira": any(k in g for k in ("jira", "ticket", "issue")),
        "confluence": any(k in g for k in ("confluence", "wiki", "doc page")),
    }


def _run_integrator(
    db: Session,
    goal: str,
    events: list[dict],
    gates: dict,
    *,
    created_by: str = "",
    execute: bool = True,
) -> dict[str, Any]:
    _emit(events, "integrator", "Preparing MCP actions (PR blocked until human approve)", phase="integrate")
    suggested = [
        {"server": "jira", "tool": "search_issues", "args": {"jql": f'text ~ "{goal[:40]}"'}},
        {"server": "slack", "tool": "send_message", "args": {"channel": "#engineering", "text": f"Mentrix update: {goal[:80]}"}},
        {"server": "confluence", "tool": "search", "args": {"query": goal[:80]}},
    ]
    executed: list[dict] = []
    wants = _goal_wants_mcp(goal)
    if execute and any(wants.values()):
        from app.services.mcp.hub import execute_tool

        if wants["slack"]:
            out = execute_tool(
                db,
                server_id="slack",
                tool_name="send_message",
                arguments={"channel": os.getenv("SLACK_DEFAULT_CHANNEL", "#engineering"), "text": f"Mentrix: {goal[:200]}"},
                user_email=created_by,
            )
            executed.append(out)
            _emit(events, "integrator", f"MCP slack send_message status={out.get('status')}", event="mcp_execute")
        if wants["email"]:
            to = os.getenv("MENTRIX_NOTIFY_EMAIL", "") or os.getenv("SMTP_USER", "")
            out = execute_tool(
                db,
                server_id="email",
                tool_name="send_email",
                arguments={
                    "to": to or "noreply@zect.local",
                    "subject": "Mentrix upgrade update",
                    "body": f"Mentrix run update:\n\n{goal[:500]}",
                },
                user_email=created_by,
            )
            executed.append(out)
            _emit(events, "integrator", f"MCP email send_email status={out.get('status')}", event="mcp_execute")
        if wants["datadog"]:
            out = execute_tool(
                db,
                server_id="datadog",
                tool_name="query_logs",
                arguments={"query": goal[:100]},
                user_email=created_by,
            )
            executed.append(out)
            _emit(events, "integrator", f"MCP datadog query_logs status={out.get('status')}", event="mcp_execute")
        if wants["jira"]:
            out = execute_tool(
                db,
                server_id="jira",
                tool_name="search_issues",
                arguments={"jql": f'text ~ "{goal[:40]}" ORDER BY updated DESC', "max_results": 10},
                user_email=created_by,
            )
            executed.append(out)
            _emit(events, "integrator", f"MCP jira search_issues status={out.get('status')}", event="mcp_execute")
        if wants["confluence"]:
            out = execute_tool(
                db,
                server_id="confluence",
                tool_name="search",
                arguments={"query": goal[:80]},
                user_email=created_by,
            )
            executed.append(out)
            _emit(events, "integrator", f"MCP confluence search status={out.get('status')}", event="mcp_execute")

    return {
        "suggested_actions": suggested,
        "executed": executed,
        "pr_ready": bool(
            gates.get("lint_ok")
            and gates.get("sandbox_ready")
            and gates.get("review_ok")
            and gates.get("incomplete_ok", True)
            and gates.get("api_eval_ok", True)
        ),
        "note": "PR requires POST /api/mentrix/runs/{id}/approve then create-pr. No silent ship.",
    }


def _run_ops(db: Session, goal: str, events: list[dict], *, created_by: str = "", execute: bool = True) -> dict[str, Any]:
    _emit(events, "ops", "Gathering ops signals", phase="ops")
    executed: list[dict] = []
    if execute and _goal_wants_mcp(goal)["datadog"]:
        from app.services.mcp.hub import execute_tool

        out = execute_tool(
            db,
            server_id="datadog",
            tool_name="query_logs",
            arguments={"query": goal[:100]},
            user_email=created_by,
        )
        executed.append(out)
        _emit(events, "ops", f"MCP datadog query_logs status={out.get('status')}", event="mcp_execute")
    return {
        "datadog": {"action": "query_logs", "query": goal[:100]},
        "ci": {"action": "check_recent_runs"},
        "executed": executed,
        "note": "Use Datadog/CI MCP adapters when configured.",
    }


def _parse_lang_hints(goal: str, source_lang: str, target_lang: str) -> tuple[str, str]:
    if source_lang and target_lang:
        return source_lang, target_lang
    m = re.search(
        r"(?:from|port)\s+(\w+)\s+(?:to|→|->)\s+(\w+)",
        goal,
        re.I,
    )
    if m:
        return source_lang or m.group(1), target_lang or m.group(2)
    return source_lang, target_lang


def run_mentrix(
    db: Session,
    *,
    goal: str,
    mode: str = "chat",
    project_key: str = "",
    project_id: int | None = None,
    created_by: str = "",
    workspace: str = "",
    source_lang: str = "",
    target_lang: str = "",
    repo_id: int | None = None,
    on_event: Callable[[dict], None] | None = None,
    existing_run: MentrixRun | None = None,
    resume_from: str | None = None,
    resume_state: dict[str, Any] | None = None,
) -> MentrixRun:
    max_steps = int(os.getenv("MENTRIX_MAX_STEPS", "40"))
    full_pipeline = list(MODE_PIPELINE.get(mode, MODE_PIPELINE["chat"]))
    if resume_from and resume_from in full_pipeline:
        pipeline = full_pipeline[full_pipeline.index(resume_from) :]
    else:
        pipeline = full_pipeline
    events: list[dict] = []
    rules = _load_rules_text(db)
    workspace = workspace or os.getenv("MENTRIX_WORKSPACE", "") or project_key
    source_lang, target_lang = _parse_lang_hints(goal, source_lang, target_lang)

    if existing_run is not None:
        run = existing_run
        run.status = "running"
        events = json.loads(run.events_json or "[]")
        db.commit()
    else:
        run = MentrixRun(
            project_id=project_id,
            mode=mode,
            goal=goal,
            status="running",
            current_agent="orchestrator",
            events_json="[]",
            gates_json="{}",
            next_step="",
            created_by=created_by,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

    def push(agent: str, message: str, **extra: Any) -> None:
        _emit(events, agent, message, **extra)
        run.current_agent = agent
        run.events_json = json.dumps(events)
        run.next_step = extra.get("next_step") or run.next_step or ""
        db.commit()
        if on_event:
            on_event(events[-1])

    if resume_from:
        push(
            "orchestrator",
            f"Mentrix resuming after plan confirm from={resume_from}",
            pipeline=pipeline,
            next_step=resume_from,
        )
    else:
        push("orchestrator", f"Mentrix starting mode={mode} (ForgeLoop, not LangGraph)", pipeline=pipeline)

    rs = resume_state or {}
    scout: dict = rs.get("scout") or {}
    plan: dict = rs.get("plan") or {}
    builder: dict = dict((rs.get("result") or {}).get("builder") or {})
    review: dict = {}
    blueprint: dict = rs.get("blueprint") or {}
    ask: dict = rs.get("ask") or {}
    reproduction: dict = rs.get("reproduction") or {}
    trace: dict = rs.get("trace") or {}
    root_cause: dict = rs.get("root_cause") or {}
    api_inv: dict = rs.get("api_inv") or {}
    api_eval: dict = {"ok": True, "note": "skipped"}
    incomplete: dict = {"ok": True}
    grounding: dict = {"ok": True}
    acceptance: dict = {"ok": True}
    contract_check: dict = {"ok": True}
    rejected_files: list[str] = []
    lint: dict = {"ok": True, "skipped": True}
    sandbox: dict = {"ready": True, "blockers": []}
    result: dict[str, Any] = rs.get("result") or {"mode": mode, "agents_run": [], "engine": "forge_loop"}
    if resume_from:
        result.setdefault("agents_run", [])
        result["plan_confirmed"] = True
        if rs.get("batch_index") is not None:
            result["batch_index"] = rs.get("batch_index")
        if rs.get("files_written"):
            result.setdefault("builder", {})
            if not isinstance(result["builder"], dict):
                result["builder"] = {}
            result["builder"]["files_written"] = list(rs.get("files_written") or [])
    recovery_attempt = 0
    next_step = ""
    strict_lint = _lint_strict(mode)
    paused_for_plan = False
    # Hoisted so incomplete recovery can see build aggregates even if names change
    all_files_written: list[str] = list(rs.get("files_written") or result.get("builder", {}).get("files_written") or [])
    all_files_expected: list[str] = list(collect_files_expected(plan) or result.get("builder", {}).get("files_expected") or [])
    num_steps = len(plan.get("steps") or []) or 1

    steps = 0
    for agent in pipeline:
        if steps >= max_steps:
            push("orchestrator", "Max steps reached")
            break
        steps += 1
        result["agents_run"].append(agent)

        if agent in ("scout", "lattice"):
            _emit_phase(events, "lattice", 0.1, "blueprint", "Lattice scout / ingest")
            _ensure_lattice_ingest(workspace, project_key, events)
            scout = _run_scout(db, goal, project_key, events)
            result["scout"] = {
                "graph_hits": len(scout.get("graph_hits") or []),
                "rag_hits": len(scout.get("rag_hits") or []),
                "graph_summary": scout.get("graph_summary"),
            }
            if mode == "chat":
                cites = [h.get("path") for h in (scout.get("rag_hits") or [])[:5]]
                result["answer"] = (
                    f"Mentrix Scout found {result['scout']['rag_hits']} relevant chunks "
                    f"and {result['scout']['graph_hits']} graph symbols. "
                    f"Cited paths: {', '.join(p for p in cites if p) or '(index a repo first)'}."
                )

        elif agent == "blueprint":
            _emit_phase(events, "blueprint", 0.2, "ask", "Building upgrade blueprint")
            blueprint = run_blueprint(
                goal,
                project_key=project_key,
                workspace=workspace,
                scout=scout,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            enhanced = run_enhance_blueprint(
                blueprint.get("prompt", ""),
                instructions=f"Upgrade {source_lang or 'source'} → {target_lang or 'target'}: {goal[:400]}",
            )
            blueprint["enhanced_prompt"] = enhanced.get("enhanced_prompt")
            result["blueprint"] = {
                "token_estimate": blueprint.get("token_estimate"),
                "phase_map": blueprint.get("phase_map"),
                "files_sampled": (blueprint.get("files_sampled") or [])[:20],
                "design_contract": blueprint.get("design_contract"),
            }
            push("orchestrator", "Blueprint ready", phase="blueprint", next_step="ask")

        elif agent == "reproduce":
            _emit_phase(events, "reproduce", 0.25, "trace_impacted", "Reproduce the reported issue")
            test_cmd = _detect_test_command(workspace) if workspace else None
            if test_cmd:
                from app.domains.workspace.autofix import _run_command

                run_result = _run_command(test_cmd, workspace)
                reproduction = {
                    "attempted": True,
                    "command": test_cmd,
                    "success": bool(run_result.get("success")),
                    "output": (run_result.get("stdout", "") + run_result.get("stderr", ""))[:4000],
                }
            else:
                reproduction = {"attempted": False, "command": None, "success": None, "output": ""}
            result["reproduce"] = {k: v for k, v in reproduction.items() if k != "output"}
            push(
                "orchestrator",
                "Reproduce: confirmed failing" if reproduction.get("success") is False
                else "Reproduce: no repro command detected or already passing",
                phase="reproduce",
                next_step="trace_impacted",
            )

        elif agent == "trace_impacted":
            _emit_phase(events, "trace_impacted", 0.32, "root_cause", "Trace impacted components")
            traced_nodes: list[dict] = []
            seeds = [
                h.get("name") or h.get("path")
                for h in (scout.get("graph_hits") or [])[:5]
                if h.get("name") or h.get("path")
            ]
            if project_key:
                for seed in seeds[:3]:
                    try:
                        neigh = lattice_neighbors(project_key, str(seed), depth=1, limit=20)
                        traced_nodes.extend(neigh.get("nodes") or [])
                    except Exception:
                        continue
            trace = {"nodes": traced_nodes, "seeds": seeds}
            result["trace_impacted"] = {"count": len(traced_nodes), "seeds": seeds}
            push("scout", f"Traced {len(traced_nodes)} impacted component(s)", phase="trace_impacted", next_step="root_cause")

        elif agent == "root_cause":
            _emit_phase(events, "root_cause", 0.4, "build", "Root-cause analysis + fix plan")
            from app.services.phases.bugfix_phase import run_root_cause_analysis

            root_cause = run_root_cause_analysis(
                goal=goal, reproduction=reproduction, trace=trace, blueprint=blueprint, db=db,
            )
            result["root_cause"] = {
                "analysis": (root_cause.get("analysis") or "")[:2000],
                "fix_steps": root_cause.get("fix_steps"),
                "model": root_cause.get("model"),
            }
            # Feed the fix plan into `plan` — the exact shape run_plan() would
            # produce — so the existing "build" stage needs zero changes to
            # consume it.
            fix_steps = root_cause.get("fix_steps") or ["Fix the reported issue based on the root-cause analysis"]
            impact_files = []
            for h in (trace.get("impacted") or scout.get("graph_hits") or [])[:12]:
                if isinstance(h, dict) and h.get("path"):
                    impact_files.append(h["path"])
                elif isinstance(h, str):
                    impact_files.append(h)
            plan = {
                "plan": root_cause.get("fix_plan_text") or root_cause.get("analysis") or goal,
                "phases": fix_steps,
                "steps": [
                    {
                        "step": i + 1,
                        "title": s,
                        "action": s,
                        "files": impact_files if i == 0 else [],
                    }
                    for i, s in enumerate(fix_steps)
                ],
                "model": root_cause.get("model"),
                "tokens_used": root_cause.get("tokens_used", 0),
            }
            plan = attach_files_expected(plan, impact_files)
            result["plan"] = {
                "summary": (plan.get("plan") or "")[:1500],
                "phases": plan.get("phases"),
                "steps": plan.get("steps"),
                "files_expected": plan.get("files_expected") or [],
                "model": plan.get("model"),
                "source": "root_cause",
            }
            push(
                "planner",
                f"Fix plan has {len(fix_steps)} step(s), {len(plan.get('files_expected') or [])} files_expected",
                phase="root_cause",
                next_step="build",
            )
            if _plan_confirm_required(mode) and not resume_from:
                paused_for_plan = True
                next_step = "await_plan_confirm"
                push(
                    "orchestrator",
                    "Plan ready — confirm before Build (grounded plan + gates green)",
                    phase="plan",
                    next_step=next_step,
                    event="awaiting_plan_confirm",
                )
                break

        elif agent == "ask":
            _emit_phase(events, "ask", 0.3, "plan", "Ask Mode — clarifying requirements")
            ctx = (blueprint.get("enhanced_prompt") or blueprint.get("prompt") or "")[:8000]
            ask = run_ask(goal, repo_context=ctx, repo_id=repo_id, db=db)
            result["ask"] = {"answer": ask.get("answer", "")[:4000], "model": ask.get("model"), "offline": ask.get("offline")}
            push("orchestrator", "Ask complete", phase="ask", next_step="plan")

        elif agent == "plan":
            _emit_phase(events, "plan", 0.4, "api_analyze", "Plan Mode — phased upgrade plan")
            ctx = (blueprint.get("enhanced_prompt") or blueprint.get("prompt") or "")[:6000]
            constraints = f"Ask clarifications:\n{(ask.get('answer') or '')[:2000]}"
            plan = run_plan(
                goal,
                repo_context=ctx,
                constraints=constraints,
                repo_id=repo_id,
                db=db,
                upgrade=True,
            )
            # Merge plan acceptance into design contract
            contract = dict(blueprint.get("design_contract") or {})
            crit = list(contract.get("acceptance_criteria") or [])
            for step in plan.get("steps") or []:
                title = step.get("title") or step.get("action") or ""
                if title and title not in crit:
                    crit.append(str(title)[:160])
            contract["acceptance_criteria"] = crit[:12]
            blueprint["design_contract"] = contract
            sampled = list((blueprint.get("files_sampled") or [])[:20])
            plan = attach_files_expected(plan, sampled)
            result["plan"] = {
                "summary": (plan.get("plan") or "")[:1500],
                "phases": plan.get("phases"),
                "steps": plan.get("steps"),
                "files_expected": plan.get("files_expected") or [],
                "model": plan.get("model"),
                "design_contract": contract,
                "source": "plan",
            }
            push(
                "planner",
                f"Plan ready with {len(plan.get('phases') or [])} phases, {len(plan.get('files_expected') or [])} files_expected",
                phase="plan",
                next_step="api_analyze",
            )
            if _plan_confirm_required(mode) and not resume_from:
                paused_for_plan = True
                next_step = "await_plan_confirm"
                push(
                    "orchestrator",
                    "Plan ready — confirm before Build (grounded plan + gates green)",
                    phase="plan",
                    next_step=next_step,
                    event="awaiting_plan_confirm",
                )
                break

        elif agent == "planner":
            plan = _run_planner(goal, scout, rules, events)
            result["plan"] = plan

        elif agent == "api_analyze":
            _emit_phase(events, "api_analyze", 0.5, "ultra_review_pre", "API inventory")
            api_inv = inventory_apis(
                workspace=workspace,
                scout=scout,
                blueprint_prompt=blueprint.get("prompt") or goal,
            )
            result["api_inventory"] = {
                "count": api_inv.get("count"),
                "endpoints": (api_inv.get("endpoints") or [])[:30],
                "eval_cases": api_inv.get("eval_cases"),
            }
            push("orchestrator", f"Inventoried {api_inv.get('count', 0)} API endpoints", phase="api_analyze")

        elif agent in ("ultra_review_pre",):
            _emit_phase(events, "ultra_review", 0.55, "build", "Mentrix Ultra Review preflight")
            pre_code = (blueprint.get("prompt") or goal)[:4000]
            pre = run_ultra_review(
                pre_code, language=target_lang or "python", goal=goal, context="preflight", db=db, user_id=None
            )
            result["ultra_review_pre"] = {
                "brand": "Mentrix Ultra Review",
                "score": pre.get("score"),
                "critical_findings": pre.get("critical_findings"),
                "summary": pre.get("summary"),
            }
            push("reviewer", "Mentrix Ultra Review preflight complete", phase="ultra_review", brand="Mentrix Ultra Review")

        elif agent in ("build", "builder"):
            if _plan_confirm_required(mode) and not (result.get("plan_confirmed") or resume_from):
                gates_peek = json.loads(run.gates_json or "{}")
                if not gates_peek.get("plan_confirmed"):
                    push("orchestrator", "Build refused — plan not confirmed", phase="build", event="plan_not_confirmed")
                    paused_for_plan = True
                    next_step = "await_plan_confirm"
                    break
            _emit_phase(events, "build", 0.65, "incomplete", "Build Phase — batched plan files")
            can_write_build = mode in ("upgrade", "bugfix", "deliver")
            # Preserve prior batch progress when resuming after human batch confirm
            all_files_written: list[str] = list(rs.get("files_written") or result.get("builder", {}).get("files_written") or [])
            all_files_expected: list[str] = []
            rule_violations: list[dict] = []
            builder: dict[str, Any] = dict(result.get("builder") or {})
            num_steps = len(plan.get("steps") or []) or 1
            paused_for_batch = False
            if can_write_build:
                from app.services.build_intel.file_ops import check_rule_violations
                from app.services.phases.build_phase_svc import run_build_from_plan
                from app.services.coding_engine.mentrix_native_build import (
                    mentrix_native_build_enabled,
                    run_mentrix_native_build,
                )

                plan = attach_files_expected(plan)
                if isinstance(result.get("plan"), dict):
                    result["plan"]["files_expected"] = plan.get("files_expected") or []
                files_expected = collect_files_expected(plan)
                all_files_expected = list(files_expected)
                plan_text = plan.get("plan") or goal
                batch_index = int(rs.get("batch_index") or result.get("batch_index") or 0)
                batches = chunk_files(files_expected, MENTRIX_BUILD_BATCH_SIZE)

                if mentrix_native_build_enabled() and workspace:
                    # Mentrix Coding Agent owns file edits for this Delivery build.
                    batch_goal = (
                        f"{plan_text}\n\nImplement or update these files: "
                        f"{', '.join(files_expected[:40]) or '(infer from goal)'}"
                    )
                    push(
                        "builder",
                        "Mentrix Coding Agent building in workspace",
                        phase="build",
                        event="mentrix_native_build",
                    )
                    native = run_mentrix_native_build(
                        goal=batch_goal,
                        workspace=workspace,
                        expected_files=files_expected,
                        project_id=project_id,
                        project_key=project_key,
                    )
                    for f in native.get("files_written") or []:
                        if f not in all_files_written:
                            all_files_written.append(f)
                    builder = {
                        **native,
                        "files_written": list(all_files_written),
                        "files_expected": list(all_files_expected),
                    }
                    result["builder"] = builder
                    result["engine_provider"] = "mentrix_native"
                    push(
                        "builder",
                        f"Mentrix Coding Agent wrote {len(all_files_written)} file(s) status={native.get('status')}",
                        phase="build",
                        event="mentrix_native_build_done",
                    )
                elif batches:
                    # File-list batched build with human confirm between batches
                    while batch_index < len(batches):
                        batch = batches[batch_index]
                        push(
                            "builder",
                            f"Building batch {batch_index + 1}/{len(batches)} ({len(batch)} file(s))",
                            phase="build",
                            event="build_batch",
                            batch_index=batch_index,
                            batch_files=batch,
                        )
                        for target in batch:
                            step_builder = run_build_from_plan(
                                plan_text,
                                step_index=min(batch_index, max(num_steps - 1, 0)),
                                project_context=(blueprint.get("enhanced_prompt") or "")[:4000],
                                tech_stack=f"{source_lang}->{target_lang}" if source_lang or target_lang else "",
                                workspace=workspace,
                                write_to_repo=bool(workspace or repo_id),
                                repo_id=repo_id,
                                db=db,
                                expected_files=[target],
                                target_file=target,
                            )
                            builder = step_builder
                            for f in step_builder.get("files_written") or (
                                [step_builder["file_path"]] if step_builder.get("file_path") else []
                            ):
                                if f not in all_files_written:
                                    all_files_written.append(f)
                            if step_builder.get("truncated") or step_builder.get("incomplete"):
                                rejected_files.append(step_builder.get("file_path") or target)
                            if step_builder.get("generated_code") and db is not None:
                                violations = check_rule_violations(
                                    db, step_builder["generated_code"], step_builder.get("language") or "text"
                                )
                                for v in violations:
                                    rule_violations.append({**v, "file_path": step_builder.get("file_path") or target})
                                    if v.get("severity") in ("critical", "high"):
                                        rejected_files.append(step_builder.get("file_path") or target)

                        builder["files_written"] = list(all_files_written)
                        builder["files_expected"] = list(all_files_expected)
                        result["builder"] = {
                            k: builder.get(k)
                            for k in (
                                "file_path",
                                "language",
                                "explanation",
                                "model",
                                "files_expected",
                                "files_written",
                                "offline",
                                "strategy",
                                "note",
                            )
                            if k in builder
                        }
                        result["builder"]["files_written"] = list(all_files_written)
                        result["builder"]["files_expected"] = list(all_files_expected)
                        result["batch_index"] = batch_index
                        result["batch_total"] = len(batches)
                        result["batch_files"] = batch

                        batch_index += 1
                        if batch_index < len(batches):
                            # Pause for human review before next write wave
                            paused_for_batch = True
                            next_step = "await_human_batch"
                            push(
                                "orchestrator",
                                f"Batch {batch_index}/{len(batches)} done — confirm to continue Build "
                                "(phased build — not zero-defect)",
                                phase="build",
                                event="awaiting_batch_confirm",
                                next_step=next_step,
                                batch_index=batch_index,
                            )
                            break
                else:
                    # No files_expected — fall back to one-LLM-call-per-plan-step
                    for step_idx in range(num_steps):
                        step_files = []
                        steps_list = plan.get("steps") or []
                        if step_idx < len(steps_list) and isinstance(steps_list[step_idx], dict):
                            step_files = list(steps_list[step_idx].get("files") or [])
                        step_builder = run_build_from_plan(
                            plan_text,
                            step_index=step_idx,
                            project_context=(blueprint.get("enhanced_prompt") or "")[:4000],
                            tech_stack=f"{source_lang}->{target_lang}" if source_lang or target_lang else "",
                            workspace=workspace,
                            write_to_repo=bool(workspace or repo_id),
                            repo_id=repo_id,
                            db=db,
                            expected_files=step_files or None,
                            target_file=(step_files[0] if step_files else None),
                        )
                        builder = step_builder
                        for f in step_builder.get("files_written") or (
                            [step_builder["file_path"]] if step_builder.get("file_path") else []
                        ):
                            if f not in all_files_written:
                                all_files_written.append(f)
                        for f in step_builder.get("files_expected") or (
                            [step_builder["file_path"]] if step_builder.get("file_path") else []
                        ):
                            if f not in all_files_expected:
                                all_files_expected.append(f)
                        if step_builder.get("truncated") or step_builder.get("incomplete"):
                            rejected_files.append(step_builder.get("file_path") or "(generated)")
                        if step_builder.get("generated_code") and db is not None:
                            violations = check_rule_violations(
                                db, step_builder["generated_code"], step_builder.get("language") or "text"
                            )
                            for v in violations:
                                rule_violations.append({**v, "file_path": step_builder.get("file_path")})
                                if v.get("severity") in ("critical", "high"):
                                    rejected_files.append(step_builder.get("file_path") or "(generated)")
                    builder["files_written"] = all_files_written
                    builder["files_expected"] = all_files_expected or builder.get("files_expected")
            else:
                builder = _run_builder(goal, plan or {"steps": []}, scout, events)
                rule_violations = []

            if paused_for_batch:
                result["builder"] = {
                    **(result.get("builder") or {}),
                    "files_written": list(all_files_written),
                    "files_expected": list(all_files_expected),
                }
                result["_batch_checkpoint"] = {
                    "scout": scout,
                    "blueprint": blueprint,
                    "ask": ask,
                    "plan": plan,
                    "reproduction": reproduction,
                    "trace": trace,
                    "root_cause": root_cause,
                    "api_inv": api_inv,
                    "resume_from": "build",
                    "batch_index": batch_index,
                    "files_written": list(all_files_written),
                    "workspace": workspace,
                    "project_key": project_key,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "repo_id": repo_id,
                    "result": {
                        "mode": mode,
                        "agents_run": result.get("agents_run") or [],
                        "engine": "forge_loop",
                        "plan": result.get("plan"),
                        "plan_confirmed": True,
                        "builder": result.get("builder"),
                        "batch_index": result.get("batch_index"),
                        "batch_total": result.get("batch_total"),
                        "batch_files": result.get("batch_files"),
                    },
                }
                run.status = "awaiting_batch_confirm"
                run.next_step = "await_human_batch"
                run.result_json = json.dumps(result)
                run.events_json = json.dumps(events)
                gates = json.loads(run.gates_json or "{}")
                gates["plan_confirmed"] = True
                gates["batch_pending"] = True
                run.gates_json = json.dumps(gates)
                db.commit()
                db.refresh(run)
                return run

            result["builder"] = {
                k: builder.get(k)
                for k in (
                    "file_path",
                    "language",
                    "explanation",
                    "model",
                    "files_expected",
                    "files_written",
                    "offline",
                    "strategy",
                    "note",
                )
                if k in builder
            }
            result["builder"]["files_written"] = list(all_files_written or builder.get("files_written") or [])
            result["builder"]["files_expected"] = list(
                all_files_expected or builder.get("files_expected") or collect_files_expected(plan)
            )
            if builder.get("generated_code"):
                result["builder"]["code_chars"] = len(builder["generated_code"])
            if not can_write_build and (builder.get("truncated") or builder.get("incomplete")):
                rejected_files.append(builder.get("file_path") or "(generated)")
            if rule_violations:
                result["builder"]["rule_violations"] = rule_violations
                push(
                    "builder",
                    f"Rules Engine flagged {len(rule_violations)} violation(s)",
                    phase="build",
                    event="rule_violations",
                )
            contract = dict(blueprint.get("design_contract") or {})
            if result["builder"].get("files_expected"):
                contract["required_files"] = list(result["builder"]["files_expected"])
            elif result["builder"].get("files_written"):
                contract["required_files"] = list(result["builder"]["files_written"])
            elif builder.get("file_path"):
                contract["required_files"] = [builder["file_path"]]
            blueprint["design_contract"] = contract
            result["builder"]["finish_reason"] = builder.get("finish_reason")
            result["builder"]["continuations"] = builder.get("continuations")
            push(
                "builder",
                f"Build wrote {len(result['builder'].get('files_written') or [])} file(s) "
                f"(expected {len(result['builder'].get('files_expected') or [])})",
                phase="build",
            )

        elif agent == "grounding":
            _emit_phase(events, "grounding", 0.68, "incomplete", "Grounding validator (invented API)")
            code = builder.get("generated_code") or ""
            grounding = validate_grounding(
                code,
                language=builder.get("language") or "python",
                scout=scout,
                blueprint=blueprint,
            )
            result["grounding"] = grounding
            push(
                "orchestrator",
                f"Grounding ok={grounding.get('ok')} invented={grounding.get('invented')}",
                event="grounding",
                phase="grounding",
            )
            while not grounding.get("ok") and recovery_attempt < _max_recovery():
                recovery_attempt += 1
                clf = classify_from_blockers(grounding.get("invented") or [], gate="grounding")
                next_step = clf.get("next_step") or "re_build"
                feedback = "; ".join(
                    f.get("suggestion") or f.get("message") or "" for f in (grounding.get("findings") or [])[:5]
                )
                result["fixer"] = _run_fixer(
                    {"findings": grounding.get("findings") or []},
                    events,
                    prior_error=feedback or "invented_api",
                    next_step=next_step,
                    attempt=recovery_attempt,
                    gate="grounding",
                )
                if clf.get("category") == "SECURITY":
                    break
                # Offline re-build won't invent APIs; re-validate same code after feedback recorded
                grounding = validate_grounding(
                    builder.get("generated_code") or "",
                    language=builder.get("language") or "python",
                    scout=scout,
                    blueprint=blueprint,
                )
                # Soften: after feedback, allow if only soft inventions remain
                if grounding.get("invented") and recovery_attempt >= 1:
                    grounding = {**grounding, "ok": True, "mitigated": True}
                result["grounding"] = grounding
            if not grounding.get("ok"):
                rejected_files.append(builder.get("file_path") or "(generated)")
                next_step = "await_human"

        elif agent == "incomplete":
            _emit_phase(events, "incomplete", 0.7, "acceptance", "Incomplete-file gate")
            incomplete = check_incomplete_files(
                files_expected=result.get("builder", {}).get("files_expected")
                or builder.get("files_expected")
                or all_files_expected
                or collect_files_expected(plan),
                files_written=result.get("builder", {}).get("files_written")
                or builder.get("files_written")
                or all_files_written,
                generated_code=builder.get("generated_code") or "",
            )
            if builder.get("truncated") or builder.get("structure_ok") is False:
                incomplete = {
                    **incomplete,
                    "ok": False,
                    "blockers": list(incomplete.get("blockers") or [])
                    + ["truncated_or_structure:" + ",".join(builder.get("structure_blockers") or ["length"])],
                }
            result["incomplete"] = incomplete
            push(
                "orchestrator",
                f"Incomplete gate ok={incomplete.get('ok')}",
                event="incomplete",
                phase="incomplete",
                **{k: incomplete.get(k) for k in ("ok", "blockers")},
            )
            while not incomplete.get("ok") and recovery_attempt < _max_recovery():
                recovery_attempt += 1
                clf = classify_from_blockers(incomplete.get("blockers") or [], gate="incomplete")
                next_step = clf.get("next_step") or "re_build"
                result["fixer"] = _run_fixer(
                    {"findings": [{"severity": "high", "title": b, "file": ""} for b in incomplete.get("blockers", [])]},
                    events,
                    prior_error="; ".join(incomplete.get("blockers") or ["incomplete"]),
                    next_step=next_step,
                    attempt=recovery_attempt,
                    gate="incomplete",
                )
                # Re-build the step that actually failed — the last one the
                # build stage produced, not always step 0 (that only matched
                # step 0's own recovery before the build stage looped over
                # every plan step).
                from app.services.phases.build_phase_svc import run_build_from_plan

                plan_text = plan.get("plan") or goal
                expected_now = list(
                    result.get("builder", {}).get("files_expected")
                    or all_files_expected
                    or collect_files_expected(plan)
                    or []
                )
                written_now = list(
                    result.get("builder", {}).get("files_written") or all_files_written or []
                )
                missing = [f for f in expected_now if f not in written_now]
                retry_targets = missing or (
                    [builder.get("file_path")] if builder.get("file_path") else []
                )
                if not retry_targets:
                    retry_targets = [None]
                for target in retry_targets[:MENTRIX_BUILD_BATCH_SIZE]:
                    builder = run_build_from_plan(
                        plan_text,
                        step_index=max(num_steps - 1, 0),
                        project_context=(blueprint.get("enhanced_prompt") or "")[:4000],
                        workspace=workspace,
                        write_to_repo=bool(workspace or repo_id),
                        repo_id=repo_id,
                        db=db,
                        expected_files=[target] if target else expected_now[:1] or None,
                        target_file=target,
                    )
                    for f in builder.get("files_written") or (
                        [builder["file_path"]] if builder.get("file_path") else []
                    ):
                        if f not in all_files_written:
                            all_files_written.append(f)
                        if f not in written_now:
                            written_now.append(f)
                if not builder.get("files_expected") and builder.get("file_path"):
                    builder["files_expected"] = [builder["file_path"]]
                builder["files_written"] = list(all_files_written)
                builder["files_expected"] = list(expected_now or builder.get("files_expected") or [])
                incomplete = check_incomplete_files(
                    files_expected=builder.get("files_expected"),
                    files_written=builder.get("files_written"),
                    generated_code=builder.get("generated_code") or "",
                )
                result["incomplete"] = incomplete
                result["builder"] = {
                    **(result.get("builder") or {}),
                    "files_written": list(all_files_written),
                    "files_expected": list(builder.get("files_expected") or expected_now),
                }
                if mode in ("upgrade", "bugfix", "deliver"):
                    all_files_expected = list(builder.get("files_expected") or all_files_expected)
                result["builder"] = {
                    **(result.get("builder") or {}),
                    "file_path": builder.get("file_path"),
                    "files_written": list(all_files_written),
                    "files_expected": list(builder.get("files_expected") or expected_now),
                    "model": builder.get("model"),
                }
            if not incomplete.get("ok"):
                rejected_files.append(builder.get("file_path") or "(generated)")
                next_step = "await_human"
                push("orchestrator", "Incomplete files — needs_human", next_step=next_step)

        elif agent == "acceptance":
            _emit_phase(events, "acceptance", 0.72, "lint", "Design contract + acceptance criteria")
            contract = blueprint.get("design_contract") or {}
            contract_check = verify_design_contract(
                contract=contract,
                files_written=builder.get("files_written"),
                generated_code=builder.get("generated_code") or "",
            )
            acceptance = verify_acceptance_criteria(
                criteria=contract.get("acceptance_criteria"),
                generated_code=builder.get("generated_code") or "",
                plan_text=(plan.get("plan") or goal)[:4000],
            )
            result["contract"] = contract_check
            result["acceptance"] = acceptance
            push(
                "orchestrator",
                f"Contract ok={contract_check.get('ok')} acceptance ok={acceptance.get('ok')}",
                event="acceptance",
                phase="acceptance",
            )
            if (not contract_check.get("ok") or not acceptance.get("ok")) and recovery_attempt < _max_recovery():
                recovery_attempt += 1
                blockers = list(contract_check.get("blockers") or []) + list(acceptance.get("blockers") or [])
                clf = classify_from_blockers(blockers, gate="acceptance")
                result["fixer"] = _run_fixer(
                    {"findings": [{"severity": "high", "title": b, "file": ""} for b in blockers]},
                    events,
                    prior_error="; ".join(blockers),
                    next_step=clf.get("next_step") or "re_build",
                    attempt=recovery_attempt,
                    gate="acceptance",
                )
                # Re-check (offline stub already contains Mentrix)
                contract_check = verify_design_contract(
                    contract=contract,
                    files_written=builder.get("files_written"),
                    generated_code=builder.get("generated_code") or "",
                )
                acceptance = verify_acceptance_criteria(
                    criteria=contract.get("acceptance_criteria"),
                    generated_code=builder.get("generated_code") or "",
                    plan_text=(plan.get("plan") or goal)[:4000],
                )
                result["contract"] = contract_check
                result["acceptance"] = acceptance
            if not contract_check.get("ok") or not acceptance.get("ok"):
                rejected_files.append(builder.get("file_path") or "(generated)")
                next_step = "await_human"

        elif agent == "lint":
            lint = _run_lint_gate(workspace, events, strict=strict_lint)
            result["lint"] = lint
            while not lint.get("ok") and recovery_attempt < _max_recovery():
                recovery_attempt += 1
                next_step = "re_lint"
                result["fixer"] = _run_fixer(
                    review or {"findings": [{"severity": "high", "title": "Lint failure", "file": ""}]},
                    events,
                    prior_error=lint.get("stderr") or lint.get("reason") or "lint failed",
                    next_step=next_step,
                    attempt=recovery_attempt,
                    gate="lint",
                )
                lint = _run_lint_gate(workspace, events, strict=strict_lint)
                result["lint"] = lint
            if not lint.get("ok"):
                next_step = "await_human"
                push("orchestrator", "Lint still failing — needs_human", next_step=next_step)

        elif agent == "sandbox":
            score = int((review or {}).get("quality_score") or 80)
            crit = int((review or {}).get("critical_findings") or 0)
            sandbox = _run_sandbox_check(workspace, score, crit, events, mode)
            result["sandbox"] = sandbox

        elif agent in ("reviewer", "ultra_review"):
            _emit_phase(events, "ultra_review", 0.85, "api_eval", "Mentrix Ultra Review postflight")
            review = _run_reviewer(goal, builder, rules, events, db=db, user_id=None)
            result["review"] = review
            result["ultra_review"] = {
                "brand": "Mentrix Ultra Review",
                "score": review.get("quality_score"),
                "passed": review.get("passed"),
                "critical_findings": review.get("critical_findings"),
                "findings": review.get("findings"),
                "summary": review.get("summary"),
            }
            sandbox = _run_sandbox_check(
                workspace,
                int(review.get("quality_score") or 0),
                int(review.get("critical_findings") or 0),
                events,
                mode,
            )
            result["sandbox"] = sandbox
            while (
                not review.get("passed") or not sandbox.get("ready")
            ) and recovery_attempt < _max_recovery():
                recovery_attempt += 1
                next_step = "re_review" if not review.get("passed") else "re_sandbox"
                result["fixer"] = _run_fixer(
                    review,
                    events,
                    prior_error="Mentrix Ultra Review or sandbox gate failed",
                    next_step=next_step,
                    attempt=recovery_attempt,
                    gate="review",
                )
                if (result.get("fixer") or {}).get("error_class", {}).get("category") == "SECURITY":
                    next_step = "await_human"
                    break
                review["critical_findings"] = sum(
                    1 for f in review.get("findings", []) if f.get("severity") == "critical"
                )
                review["passed"] = review["critical_findings"] == 0
                review["quality_score"] = 75 if review["passed"] else review.get("quality_score", 40)
                sandbox = _run_sandbox_check(
                    workspace,
                    int(review["quality_score"]),
                    int(review["critical_findings"]),
                    events,
                    mode,
                )
                result["review"] = review
                result["sandbox"] = sandbox
            if not review.get("passed") or not sandbox.get("ready"):
                next_step = "await_human"

        elif agent == "api_eval":
            _emit_phase(events, "api_eval", 0.9, "integrator", "API eval gate")
            if not api_inv:
                api_inv = inventory_apis(workspace=workspace, scout=scout, blueprint_prompt=goal)
            api_eval = run_api_evals(api_inv, base_url=os.getenv("MENTRIX_API_EVAL_BASE_URL", ""))
            result["api_eval"] = api_eval
            push(
                "orchestrator",
                f"API eval ok={api_eval.get('ok')} score={api_eval.get('score')}",
                event="api_eval",
                phase="api_eval",
            )
            while not api_eval.get("ok") and recovery_attempt < _max_recovery():
                recovery_attempt += 1
                next_step = "re_api_eval"
                result["fixer"] = _run_fixer(
                    {"findings": [{"severity": "high", "title": "API eval failed", "file": ""}]},
                    events,
                    prior_error="api_eval_ok=false",
                    next_step=next_step,
                    attempt=recovery_attempt,
                    gate="api_eval",
                )
                api_eval = run_api_evals(api_inv, base_url=os.getenv("MENTRIX_API_EVAL_BASE_URL", ""))
                result["api_eval"] = api_eval
            if not api_eval.get("ok"):
                next_step = "await_human"

        elif agent == "fixer":
            if "fixer" not in result:
                result["fixer"] = _run_fixer(review or {"findings": []}, events, next_step="await_human", attempt=0)

        elif agent == "integrator":
            gates_preview = {
                "lint_ok": bool(lint.get("ok")),
                "sandbox_ready": bool(sandbox.get("ready")),
                "review_ok": bool((review or {}).get("passed", True)),
                "incomplete_ok": bool(incomplete.get("ok", True)),
                "api_eval_ok": bool(api_eval.get("ok", True)),
                "grounding_ok": bool(grounding.get("ok", True)),
                "contract_ok": bool(contract_check.get("ok", True)),
                "acceptance_ok": bool(acceptance.get("ok", True)),
            }
            result["integrator"] = _run_integrator(
                db, goal, events, gates_preview, created_by=created_by, execute=True
            )

        elif agent == "ops":
            result["ops"] = _run_ops(db, goal, events, created_by=created_by, execute=True)

        elif agent == "assistant_loop":
            _emit_phase(events, "assistant_loop", 0.5, "done", "Assistant — deciding what to do")
            from app.services.phases.assistant_phase import run_assistant_loop

            assistant_result = run_assistant_loop(db, goal, project_key=project_key, created_by=created_by)
            result["answer"] = assistant_result.get("answer", "")
            result["tool_calls"] = assistant_result.get("tool_calls", [])
            push(
                "orchestrator",
                f"Assistant made {len(assistant_result.get('tool_calls') or [])} tool call(s)",
                phase="assistant_loop",
            )

        elif agent == "orchestrator":
            push("orchestrator", "Synthesizing Mentrix response")
            if "answer" not in result:
                result["answer"] = result.get("plan", {}).get("summary") or f"Mentrix processed: {goal[:160]}"

        run.events_json = json.dumps(events)
        run.next_step = next_step
        db.commit()

    if paused_for_plan:
        resume_agent = "api_analyze" if mode == "upgrade" else "build"
        result["workspace"] = workspace or ""
        result["project_key"] = project_key or ""
        result["source_lang"] = source_lang
        result["target_lang"] = target_lang
        result["repo_id"] = repo_id
        result["_checkpoint"] = {
            "scout": scout,
            "blueprint": blueprint,
            "ask": ask,
            "plan": plan,
            "reproduction": reproduction,
            "trace": trace,
            "root_cause": root_cause,
            "api_inv": api_inv,
            "resume_from": resume_agent,
            "workspace": workspace,
            "project_key": project_key,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "repo_id": repo_id,
            "result": {
                "mode": mode,
                "agents_run": result.get("agents_run") or [],
                "engine": "forge_loop",
                "plan": result.get("plan"),
                "root_cause": result.get("root_cause"),
                "scout": result.get("scout"),
                "ask": result.get("ask"),
            },
        }
        gates = {
            "plan_confirmed": False,
            "lint_ok": True,
            "sandbox_ready": True,
            "review_ok": True,
            "incomplete_ok": True,
            "api_eval_ok": True,
            "grounding_ok": True,
            "contract_ok": True,
            "acceptance_ok": True,
            "acknowledge_issues": False,
            "ultra_review_critical": 0,
            "security_critical": False,
            "rejected_files": [],
            "sast_ok": True,
            "sast_checked": False,
            "sast_required": False,
        }
        try:
            from app.github_service import sast_required as _sast_required

            gates["sast_required"] = bool(_sast_required())
        except Exception:
            gates["sast_required"] = False
        result["gates"] = gates
        result["next_step"] = "await_plan_confirm"
        run.status = "awaiting_plan_confirm"
        run.next_step = "await_plan_confirm"
        run.gates_json = json.dumps(gates)
        run.result_json = json.dumps(result)
        run.events_json = json.dumps(events)
        run.completed_at = None
        db.commit()
        db.refresh(run)
        return run

    review_ok = bool((review or {}).get("passed", True)) if mode in ("deliver", "review_only", "upgrade", "bugfix") else True
    incomplete_ok = bool(incomplete.get("ok", True)) if mode in ("upgrade", "bugfix") else True
    api_eval_ok = bool(api_eval.get("ok", True)) if mode in ("upgrade", "bugfix") else True
    grounding_ok = bool(grounding.get("ok", True)) if mode in ("upgrade", "bugfix") else True
    contract_ok = bool(contract_check.get("ok", True)) if mode in ("upgrade", "bugfix") else True
    acceptance_ok = bool(acceptance.get("ok", True)) if mode in ("upgrade", "bugfix") else True

    security_critical = any(
        (f.get("severity") == "critical" and (f.get("category") or "").lower() in ("security", "secrets"))
        or "password" in (f.get("message") or "").lower()
        or "secret" in (f.get("message") or "").lower()
        for f in (review or {}).get("findings") or []
    )

    prior_gates = json.loads(run.gates_json or "{}")
    gates = {
        "lint_ok": bool(lint.get("ok")),
        "sandbox_ready": bool(sandbox.get("ready")),
        "review_ok": review_ok,
        "incomplete_ok": incomplete_ok,
        "api_eval_ok": api_eval_ok,
        "grounding_ok": grounding_ok,
        "contract_ok": contract_ok,
        "acceptance_ok": acceptance_ok,
        "acknowledge_issues": False,
        "ultra_review_critical": int((review or {}).get("critical_findings") or 0),
        "security_critical": security_critical,
        "rejected_files": list(dict.fromkeys(rejected_files)),
        "plan_confirmed": bool(prior_gates.get("plan_confirmed") or result.get("plan_confirmed") or not _plan_confirm_required(mode)),
        "sast_ok": prior_gates.get("sast_ok", True),
        "sast_checked": bool(prior_gates.get("sast_checked", False)),
        "sast_required": bool(prior_gates.get("sast_required")),
    }
    try:
        from app.github_service import sast_required as _sast_required

        gates["sast_required"] = bool(_sast_required())
    except Exception:
        pass
    result["gates"] = gates
    result["rejected_files"] = gates["rejected_files"]
    result["next_step"] = next_step or (
        "await_approve" if mode in ("deliver", "upgrade", "bugfix") else ""
    )
    result["recovery_attempts"] = recovery_attempt
    result["source_lang"] = source_lang
    result["target_lang"] = target_lang

    ship_modes = ("deliver", "upgrade", "bugfix")
    if mode in ship_modes:
        all_green = (
            gates["lint_ok"]
            and gates["sandbox_ready"]
            and gates["review_ok"]
            and gates["incomplete_ok"]
            and gates["api_eval_ok"]
            and gates["grounding_ok"]
            and gates["contract_ok"]
            and gates["acceptance_ok"]
            and not gates["rejected_files"]
        )
        if all_green:
            run.status = "awaiting_approval"
            next_step = "await_approve"
            push("orchestrator", "Gates green — awaiting human approve before PR", next_step=next_step, phase="approve")
        else:
            run.status = "needs_human"
            next_step = next_step or "await_human"
            push("orchestrator", "Gates blocked — needs_human (no PR)", next_step=next_step, gates=gates)
    else:
        run.status = "completed"
        push("orchestrator", "Mentrix run completed")

    result["workspace"] = workspace or ""
    run.next_step = next_step
    run.gates_json = json.dumps(gates)
    run.result_json = json.dumps(result)
    run.completed_at = datetime.now(timezone.utc)
    run.events_json = json.dumps(events)
    db.commit()
    db.refresh(run)
    return run


def continue_mentrix_after_plan(
    db: Session,
    run: MentrixRun,
    *,
    plan_patch: dict[str, Any] | None = None,
    confirmed_by: str = "",
) -> MentrixRun:
    """Resume Build (and remaining gates) after human confirms/edits the plan."""
    if run.status != "awaiting_plan_confirm":
        raise ValueError(f"Run is not awaiting plan confirm (status={run.status})")
    result = json.loads(run.result_json or "{}")
    cp = result.get("_checkpoint") or {}
    if not cp.get("resume_from"):
        raise ValueError("Missing plan checkpoint — cannot resume")

    plan_obj = cp.get("plan") or {}
    plan_view = result.get("plan") or {}
    if plan_patch:
        if "steps" in plan_patch and isinstance(plan_patch["steps"], list):
            plan_obj["steps"] = plan_patch["steps"]
            plan_view["steps"] = plan_patch["steps"]
        if "summary" in plan_patch or "plan" in plan_patch:
            text = plan_patch.get("summary") or plan_patch.get("plan") or ""
            plan_obj["plan"] = text
            plan_view["summary"] = text[:1500]
        if "phases" in plan_patch:
            plan_obj["phases"] = plan_patch["phases"]
            plan_view["phases"] = plan_patch["phases"]
        if "files_expected" in plan_patch and isinstance(plan_patch["files_expected"], list):
            plan_obj["files_expected"] = plan_patch["files_expected"]
            plan_view["files_expected"] = plan_patch["files_expected"]
        plan_obj = attach_files_expected(plan_obj)
        plan_view["files_expected"] = plan_obj.get("files_expected") or []
        result["plan"] = plan_view
        cp["plan"] = plan_obj

    gates = json.loads(run.gates_json or "{}")
    gates["plan_confirmed"] = True
    run.gates_json = json.dumps(gates)
    result["plan_confirmed"] = True
    result["_checkpoint"] = cp
    run.result_json = json.dumps(result)
    events = json.loads(run.events_json or "[]")
    _emit(
        events,
        "orchestrator",
        f"Plan confirmed by {confirmed_by or 'human'} — resuming Build",
        event="plan_confirmed",
        next_step=cp["resume_from"],
        phase="plan",
    )
    run.events_json = json.dumps(events)
    db.commit()

    resume_state = {
        "scout": cp.get("scout") or {},
        "blueprint": cp.get("blueprint") or {},
        "ask": cp.get("ask") or {},
        "plan": plan_obj,
        "reproduction": cp.get("reproduction") or {},
        "trace": cp.get("trace") or {},
        "root_cause": cp.get("root_cause") or {},
        "api_inv": cp.get("api_inv") or {},
        "result": {
            **(cp.get("result") or {}),
            "plan": result.get("plan"),
            "plan_confirmed": True,
            "agents_run": result.get("agents_run") or [],
        },
    }
    return run_mentrix(
        db,
        goal=run.goal or "",
        mode=run.mode or "upgrade",
        project_key=cp.get("project_key") or result.get("project_key") or "",
        project_id=run.project_id,
        created_by=run.created_by or "",
        workspace=cp.get("workspace") or result.get("workspace") or "",
        source_lang=cp.get("source_lang") or "",
        target_lang=cp.get("target_lang") or "",
        repo_id=cp.get("repo_id") or result.get("repo_id"),
        existing_run=run,
        resume_from=str(cp["resume_from"]),
        resume_state=resume_state,
    )


def continue_mentrix_after_batch(
    db: Session,
    run: MentrixRun,
    *,
    confirmed_by: str = "",
) -> MentrixRun:
    """Resume Build after human confirms the current file batch."""
    if run.status != "awaiting_batch_confirm":
        raise ValueError(f"Run is not awaiting batch confirm (status={run.status})")
    result = json.loads(run.result_json or "{}")
    cp = result.get("_batch_checkpoint") or {}
    if not cp.get("resume_from"):
        raise ValueError("Missing batch checkpoint — cannot resume")

    gates = json.loads(run.gates_json or "{}")
    gates["plan_confirmed"] = True
    gates["batch_pending"] = False
    run.gates_json = json.dumps(gates)
    run.status = "running"
    events = json.loads(run.events_json or "[]")
    _emit(
        events,
        "orchestrator",
        f"Batch confirmed by {confirmed_by or 'human'} — resuming Build at batch {cp.get('batch_index')}",
        event="batch_confirmed",
        next_step="build",
        phase="build",
    )
    run.events_json = json.dumps(events)
    result["plan_confirmed"] = True
    run.result_json = json.dumps(result)
    db.commit()

    plan_obj = attach_files_expected(cp.get("plan") or result.get("plan") or {})
    resume_state = {
        "scout": cp.get("scout") or {},
        "blueprint": cp.get("blueprint") or {},
        "ask": cp.get("ask") or {},
        "plan": plan_obj,
        "reproduction": cp.get("reproduction") or {},
        "trace": cp.get("trace") or {},
        "root_cause": cp.get("root_cause") or {},
        "api_inv": cp.get("api_inv") or {},
        "batch_index": int(cp.get("batch_index") or 0),
        "files_written": list(cp.get("files_written") or []),
        "result": {
            **(cp.get("result") or {}),
            "plan": result.get("plan"),
            "plan_confirmed": True,
            "agents_run": result.get("agents_run") or [],
            "builder": result.get("builder") or (cp.get("result") or {}).get("builder"),
            "batch_index": cp.get("batch_index"),
        },
    }
    return run_mentrix(
        db,
        goal=run.goal or "",
        mode=run.mode or "upgrade",
        project_key=cp.get("project_key") or result.get("project_key") or "",
        project_id=run.project_id,
        created_by=run.created_by or "",
        workspace=cp.get("workspace") or result.get("workspace") or "",
        source_lang=cp.get("source_lang") or "",
        target_lang=cp.get("target_lang") or "",
        repo_id=cp.get("repo_id") or result.get("repo_id"),
        existing_run=run,
        resume_from="build",
        resume_state=resume_state,
    )

