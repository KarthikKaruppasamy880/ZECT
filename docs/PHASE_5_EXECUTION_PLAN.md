# Phase 5 Execution Plan — Permissions, Secrets, Auditing

Companion to `Upgrade.md` Phase 5. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

Reuse existing engines: `PermissionRule` + broker, Fernet vault, `AuditLog` / `log_audit`, `allowed_paths`, Mentrix cancel / Rules kill-switch. Do **not** invent a second RBAC, vault, or audit store.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unify `log_audit`; auth-gate open permission endpoints; sync threat docs to fixed findings 3–6 | **Done** (#98) |
| B | Temporary capability grants (`expires_at`) + map Upgrade capability names onto existing rules/broker | **This PR** |
| C | Secret references (no plaintext reveal path for agents) + systemic log redaction + permission diagnostics UI | Pending |
| D | Global emergency-stop (halt agents/runners/webhooks) + optional audit integrity chain | Pending |

## Inventory (already present)

- RBAC roles + `@require_role` / `@require_authentication`
- Permissions rules CRUD + `/check` + approval audits + Mentrix `permission_broker`
- Secrets Manager (Fernet) + Secrets UI
- Audit Trail API + UI
- Path allowlist; App Runner / sandbox / webhook / CORS / auth `.env` hardening (code already fixed)

## Stage B files

- `backend/app/models.py` — `CapabilityGrant` table
- `backend/app/domains/permissions/capability_grants.py` — Upgrade aliases + grant evaluation
- `backend/app/domains/permissions/permissions.py` — `/grants`, `/capabilities`; `/check` applies grants
- `backend/app/services/mentrix/permission_broker.py` — grant override before confirm
- `frontend/src/pages/Permissions.tsx` — Grants tab
- `backend/tests/fixes_and_phases/test_capability_grants.py`

## Risks (Stage B)

- Empty `subject_id` on a user grant matches any authenticated user of that check — intentional for broad temp allows; prefer explicit ids in production
- Temporary `allow` can open actions whose baseline rule is `never` (admin-issued only)
