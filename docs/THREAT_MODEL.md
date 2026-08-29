# ZECT — Threat Model / Security Findings (Phase 0 Audit → Phase 5)

Ranked by severity. Critical items were fixed out-of-band; High/Medium findings **3–6 are fixed in code** as of Phase 5 Stage A doc sync. Residual Phase 5 work is capability grants, secret references, diagnostics, and global emergency-stop (see `PHASE_5_EXECUTION_PLAN.md`).

## Critical — FIXED

### 1. ~~`app_runner.py` — arbitrary shell execution~~ — FIXED
Admin RBAC + path allowlist + audit on `/execute`, `/start`, `/configure`.

### 2. ~~`sandbox.py` — host fallback / injection~~ — FIXED
Docker argv + `shell=False`; modes `docker` / `local_unsandboxed` surfaced to callers.

## High — FIXED

### 3. ~~GitHub webhook signature opt-in~~ — FIXED
`POST /api/review/webhook/github` rejects when `webhook_secret` is empty; signature required when configured. Covered by `test_github_webhook_signature.py`.

### 4. ~~`auth.py` `.env` `override=True` on login~~ — FIXED
`load_dotenv(..., override=False)` so in-process / test credentials are not stomped. Covered by auth contract tests.

## Medium — FIXED

### 5. ~~CORS bypass on unhandled 500s~~ — FIXED
Global exception handler only reflects allowlisted `Origin`. Covered by `test_cors.py`.

### 6. ~~`diff_viewer.py` unrestricted `repo_path`~~ — FIXED
Uses `path_under_allowed_roots` before subprocess `cwd`.

## Residual / Phase 5 backlog (not findings 1–6)

- Capability grants with expiry + Upgrade.md capability taxonomy (Stage B)
- Secret references without plaintext reveal for agents; systemic log redaction (Stage C)
- Permission diagnostics page (Stage C)
- Global emergency-stop beyond review webhook kill-switch (Stage D)
- Dual historical `log_audit` entry points — Stage A unifies on `audit_trail.log_audit`
- Admin password remains in `.env` (informational; vault covers app-managed secrets)
- Windows-friendly default roots in `allowed_paths` when `ZECT_WORKSPACE_ROOT` unset (partially addressed)

## Not a finding

- No hardcoded secrets in source (env reads).
- Electron: `contextIsolation`, no `nodeIntegration`, sandboxed.
- File Explorer / Git Ops use path allowlist.
