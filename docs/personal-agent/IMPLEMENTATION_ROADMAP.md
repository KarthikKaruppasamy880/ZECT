# Personal Agent — Implementation Roadmap (PA-0)

One PR per phase. **Do not start the next phase until the current PR is approved.**  
Branch pattern: `feature/personal-agent-pa-N-short-name`.

---

## PA-0 — Current-state audit (this PR)

**Deliverable:** docs only under `docs/personal-agent/`.  
**Status:** complete in this branch.

---

## PA-1 — Shared command and policy foundation

**Goal:** Unify typed + spoken companion tools behind one orchestration and policy path. **No new desktop automation features.**  
**Status:** implemented (`feature/personal-agent-pa-1-coding-desktop-spine`). Flag `MENTRIX_PA1_ORCHESTRATOR` (default on).

### Scope

- Stable command schema: actor, user, run/correlation id, intent, params, capability, target, risk, policy decision, approval, execution, verification, result  
- Normalize: `MentrixOrchestrator`, `PermissionService`, `ApprovalService`, `AuditService`  
- Emergency stop + cancellation + idempotency key  
- Server-side **no-delete** policy module (centralize existing refuses)  
- Optionally tighten `MENTRIX_BROWSER_ALLOWLIST` default away from `*`

### Expected files (illustrative)

- `backend/app/services/mentrix/orchestrator.py` (or `domains/personal_agent/command.py`)  
- `backend/app/services/mentrix/approval_service.py`  
- Thin wrappers around `permission_broker.py`, `domains/permissions/*`, `audit_trail.py`  
- Tests for schema + deny/approve paths  
- Docs update: CURRENT_REQUEST_FLOW → “PA-1 as-built”

### Migration

- Companion `_exec_tool` calls orchestrator; keep ForgeLoop Delivery unchanged  
- No DB migration required if decisions are structured logs first; optional table for approval records  

### Risks

- Dual-path regressions (companion still calling adapters directly)  
- Realtime tool confirm bypass if not routed  

### Rollback

Feature flag `MENTRIX_PA1_ORCHESTRATOR=0` to use legacy companion path.

---

## PA-2 — Email / Slack / Calendar read+draft

Provider interfaces; allowlists; drafts with citations; **no send**. CalendarProvider greenfield.

## PA-3 — Approved send/write

Immutable preview, hash match, provider IDs, anti-dupe, audit.

## PA-4 — Browser automation

DOM-first verify; kill default `*`; session isolation; no password scrape.

## PA-5 — Native desktop

A11y-first; allowlists; verify; emergency stop; keyboard/mouse fallback only.

## PA-6 — Safe file organization

Durable proposals, SHA-256, Undo, no delete, collision handling.

## PA-7 — Voice stabilization

Latency, barge-in, cancel; bind STT intents to PA-1 orchestrator.

## PA-8 — Meeting assistant

Calendar + email + Slack context; briefs; no auto-send; consent for recording.

## PA-9 — Skills and automations

Governed skill manifests; schedules with **separate** limited grants.

---

## Explicitly deferred

- Security monitoring / incident IR productization (DesktopControl)  
- LiveKit Agents  
- Seven TTS engines / Voicebox Tauri UI  

---

## PA-0 report checklist

| Item | Value |
|------|--------|
| Files created | See PR |
| Findings | See CURRENT_STATE_AUDIT |
| Test failures | Record in PR (docs-only; do not fix product) |
| Proposed PA-1 scope | Above |
| Migration | Orchestrator flag; optional approval table |
| Risks | Dual path; Realtime bypass; allowlist `*` |
| Rollback | Revert docs PR / PA-1 flag |
