# Phase 5 Execution Plan — Permissions, Secrets, Auditing

Companion to `Upgrade.md` Phase 5. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

Reuse existing engines: `PermissionRule` + broker, Fernet vault, `AuditLog` / `log_audit`, `allowed_paths`, Mentrix cancel / Rules kill-switch / `Setting`. Do **not** invent a second RBAC, vault, or audit store.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unify `log_audit`; auth-gate open permission endpoints; sync threat docs to fixed findings 3–6 | **Done** (#98) |
| B | Temporary capability grants (`expires_at`) + map Upgrade capability names onto existing rules/broker | **Done** (#99) |
| C | Secret references (no plaintext for agents) + systemic log redaction + permission diagnostics UI | **Done** (this PR) |
| D | Global emergency-stop + audit integrity hash chain | **Done** (this PR) |

## Stage C/D files

- `backend/app/security/redact.py` — systemic redaction
- `backend/app/security/emergency_stop.py` — Setting-backed global halt
- `backend/app/domains/permissions/secrets_manager.py` — `/resolve` reference endpoints
- `backend/app/domains/audit/audit_trail.py` — redact + `prev_hash`/`entry_hash`
- `backend/app/domains/permissions/permissions.py` — `/diagnostics`, `/emergency-stop`
- Gates: Mentrix `start_run`, App Runner execute/start, GitHub webhook auto-review
- `frontend/src/pages/Permissions.tsx` — Diagnostics tab + emergency-stop control
- `backend/tests/fixes_and_phases/test_phase5_cd_security.py`

## Phase 5 complete

Upgrade.md Phase 5 implement items 1–12 covered by A–D. **Stop after Phase 5** per Upgrade.md — next phase is 6 only when requested. Phase 9 remains ON HOLD.
