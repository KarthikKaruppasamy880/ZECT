# ZECT — Threat Model / Security Findings (Phase 0 Audit)

Ranked by severity. Phase 0 does not fix these — this is the input to Phase 5 (Permissions, Secrets, Auditing) and to any immediate out-of-band patch you choose to prioritize separately.

## Critical

### 1. `app_runner.py` — unauthenticated-scope arbitrary shell execution, no path restriction
`backend/app/routers/app_runner.py:174` (`/api/runner/execute`) and `:213` (`/api/runner/start`) run caller-supplied shell strings via `subprocess.run(req.command, shell=True, ...)` / `subprocess.Popen(req.command, shell=True, ...)`.
- No command allowlist or escaping.
- No RBAC decorator on either endpoint (confirmed via grep — no `require_role`/permission dependency in the file).
- `cwd` is only checked for existence (`os.path.isdir`), **not** run through the `path_under_allowed_roots` allowlist that `file_explorer.py`/`git_ops.py` use.
- **Impact:** any authenticated bearer-token holder gets full RCE as the backend process user, anywhere on the filesystem the process can reach.
- This is a single-user personal tool today, which lowers real-world exploitability, but it's worth a conscious decision: keep as-is because you trust your own auth boundary, or add the same RBAC + path-allowlist pattern already used elsewhere in the codebase.

### 2. `sandbox.py` — silent host fallback + command injection even with Docker
`backend/app/routers/sandbox.py` docstring claims Docker-isolated execution, but:
- `_run_local_sandbox` (line 75) runs directly on the host with `shell=True` whenever Docker isn't installed or `prefer_docker=False` (lines 115-123, 236-238) — **silent**, not surfaced as a degraded-mode warning to the caller.
- `_run_docker_sandbox` (lines 137-147) builds the `docker run` command via raw string concatenation of `req.image`/`req.command` into a `shell=True` string — unescaped, so shell metacharacters in those fields break out of the intended container isolation.
- **Impact:** the "safe sandbox" can silently not be a sandbox at all, and even when it is, its own invocation is injectable.

## High

### 3. GitHub webhook signature verification is opt-in, not mandatory
`backend/app/routers/code_review.py:599` (`POST /api/review/webhook/github`) only verifies `X-Hub-Signature-256` (lines 645-650) **if** an admin previously configured a `webhook_secret` for that owner/repo. Default is `""` (line 100) — unset. Any repo where the secret was never configured accepts unauthenticated POSTs that trigger a real code-review run under a synthetic `github-webhook` identity (line 677).
- **Impact:** anyone who discovers the webhook URL can trigger review runs for an unconfigured repo. Not a data-exfiltration path by itself, but an unauthenticated trigger for compute/LLM spend and noise.
- **Fix direction:** require `webhook_secret` to be set before the webhook endpoint accepts events for that repo, rather than defaulting to "accept anyway."

### 4. `auth.py` reloads `.env` with `override=True` on every login call
`backend/app/routers/auth.py:_auth_creds()` calls `load_dotenv(_ENV_FILE, override=True)` on every invocation, re-reading `backend/.env` and overwriting any in-process-set credential env vars each time.
- **Test-suite impact (confirmed):** this is why `test_auth_contract.py`, `test_enterprise_routers.py`, and `test_mentrix_platform.py` fail/error in this environment — `conftest.py` sets test credentials before importing the app, but the very next login call reloads the real `.env` values and stomps them.
- **Production impact:** any process that rewrites `.env` while the server is running takes effect on the *next* login call with no restart — likely intentional for ops convenience on a personal tool, but worth a conscious yes/no rather than an accidental side effect. Recommend gating the reload behind an explicit "reload credentials" action instead of doing it unconditionally on every call.

## Medium

### 5. CORS bypass on unhandled 500s
`backend/app/main.py`'s global exception handler (lines 98-123) echoes the request's `Origin` header directly into `Access-Control-Allow-Origin` with `allow-credentials: true` on unhandled exceptions (lines 110, 118), bypassing the otherwise-correct `CORSMiddleware` allowlist for that response class specifically. The normal-path CORS config itself is a proper allowlist (verified, no `*`), so this is scoped narrowly to the error-handler path — but it's the one place the allowlist doesn't apply.

### 6. `diff_viewer.py` accepts a caller-supplied `repo_path` as subprocess `cwd`
`backend/app/routers/diff_viewer.py:180-186` uses `repo_path` directly as `cwd` for a `subprocess.run` call; unlike `git_ops.py`, no `path_under_allowed_roots` check was found in this file in this audit pass. Needs a closer read to confirm whether it's constrained elsewhere (e.g. only reachable with an already-validated repo record) before treating as equally severe as findings 1-2.

## Low / informational

- **App's own admin credential is plaintext in `.env`** — standard for `.env` files, and distinct from the Fernet-vault-protected path used for *other* stored secrets (Jira/Slack tokens etc.). Not a finding against the vault itself, just worth noting the login credential isn't under the same protection.
- **Electron config is secure** — `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, no `webSecurity` override. No findings here.
- **File Explorer / Git Ops correctly allowlist paths** — both route through `path_under_allowed_roots`. Windows-specific note: the default allowed roots (`/home`, `/tmp`, `/var`, `/opt`) are POSIX paths that never match on Windows — file access only works today because `ZECT_WORKSPACE_ROOT` is explicitly set in `.env`. Worth adding a Windows-aware default so this isn't silently broken for a fresh install without that env var.

## Not a finding

- No hardcoded secrets found in source (all reads go through `os.getenv`).
- No `eval`/`exec` on request-controlled input found.
- Fixed-argument `subprocess.run` calls (git/lint tooling) are not shell-injectable — only the `shell=True` + free-text-command call sites above are.

## Recommended immediate action vs. Phase 5 backlog

Findings 1 and 2 (Critical) are the only ones I'd flag as worth a decision *now*, independent of the phase roadmap, since they're live RCE-class gaps on a running service — not because Phase 0 mandates a fix, but because severity warrants a conscious choice rather than sitting in a backlog unexamined. Everything else fits naturally into Phase 5's permissions/secrets/audit work.
