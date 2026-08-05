# Phase 5 Execution Plan — Permissions, Secrets, Auditing

Companion to `Upgrade.md` Phase 5. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

Reuse existing engines: `PermissionRule` + broker, Fernet vault, `AuditLog` / `log_audit`, `allowed_paths`, Mentrix cancel / Rules kill-switch. Do **not** invent a second RBAC, vault, or audit store.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unify `log_audit`; auth-gate open permission endpoints; sync threat docs to fixed findings 3–6 | **This PR** |
| B | Temporary capability grants (`expires_at`) + map Upgrade capability names onto existing rules/broker | Pending |
| C | Secret references (no plaintext reveal path for agents) + systemic log redaction + permission diagnostics UI | Pending |
| D | Global emergency-stop (halt agents/runners/webhooks) + optional audit integrity chain | Pending |

## Inventory (already present)

- RBAC roles + `@require_role` / `@require_authentication`
- Permissions rules CRUD + `/check` + approval audits + Mentrix `permission_broker`
- Secrets Manager (Fernet) + Secrets UI
- Audit Trail API + UI
- Path allowlist; App Runner / sandbox / webhook / CORS / auth `.env` hardening (code already fixed)

## Stage A files

- `backend/app/domains/audit/audit_trail.py` — canonical soft-fail `log_audit`
- `backend/app/infrastructure/auth/rbac.py` — delegate to canonical `log_audit`
- `backend/app/domains/permissions/permissions.py` — auth on list/check/audits GETs
- Docs: `PHASE_5_EXECUTION_PLAN.md`, `THREAT_MODEL.md`, `ROADMAP.md`, `FEATURE_INVENTORY.md`
- Tests: `test_permissions_auth.py`, existing `test_rbac.py`

## Risks (Stage A)

- Dual `log_audit` signatures — wrapper preserves rbac call shape
- Auth on `/check` may break unauthenticated clients — UI already uses `apiFetch` with token; broker is in-process
