# Fix #4: Per-User Rate Limiting & Token Budget Enforcement — IMPLEMENTATION COMPLETE

**Status:** ✅ **DONE**
**Date Completed:** July 23, 2026
**Files Created:** 2
**Files Modified:** 6
**Tests Added:** 29
**Effort:** Days 10-13 (4 days)

---

## What Was Fixed

Two separate but related gaps:

1. **Rate limiting was IP-keyed, not user-keyed, and one-size-fits-all.**
   `RateLimitMiddleware` bucketed on `request.client.host`. Multiple users behind
   one NAT/VPN shared a bucket; a single user could dodge the limit entirely by
   rotating source IPs. Every route — a cheap `GET /api/projects` and an expensive
   `POST /api/llm/ask` — shared the same limit, so there was no way to throttle
   LLM spend without throttling everything.

2. **Token budgets existed but enforced nothing.**
   `TokenBudget` (daily/monthly limits per user) and `check_token_limit()` were
   fully built as a dashboard feature, but nothing in the actual LLM code path
   (`llm.py`, `review_service.py`) ever called it. `enforce_limits=True` had zero
   effect. Worse: `log_tokens()` never accepted a `user_id`, so every `TokenLog`
   row was written with `user_id=NULL` — the per-user usage dashboards in
   `token_controls.py` were already built to expect this data and had none.

### Before (Vulnerable)

```python
# ❌ Keyed by IP, one bucket for every route
client_ip = request.client.host if request.client else "unknown"
allowed, headers = self.limiter.allow(client_ip)

# ❌ Ask endpoint — no budget check, no user_id on the log
@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest, db: Session = Depends(get_db)):
    ...
    log_tokens(action="ask_question", feature="ask_mode", ..., total_tokens=tokens)
    # TokenBudget.enforce_limits=True does nothing — this line never checked it
```

**Attack scenario:** A single user scripts 10,000 `/api/llm/ask` calls against
`gpt-4o-mini` in a loop. `ZECT_RATE_LIMIT_DISABLED` aside, even with rate
limiting on, the shared bucket only throttled by IP — a botnet or proxy rotation
bypassed it completely, and no budget ever kicked in to cap the resulting bill.

### After (Secure)

```python
# ✅ Keyed by authenticated user (AuthMiddleware runs first, sets request.state.user_id)
key, _ = _rate_limit_key(request)  # "user:42" or "ip:x.x.x.x" pre-auth
allowed, headers = self.limiter.allow(key)          # general tier
if _is_expensive(path):
    llm_allowed, _ = self.llm_limiter.allow(key)      # stricter LLM tier
    if not llm_allowed:
        return 429

# ✅ Ask endpoint — budget checked before spending, user_id on the log
@router.post("/ask", response_model=AskResponse)
def ask_question(
    req: AskRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),  # 429s if over budget
    db: Session = Depends(get_db),
):
    ...
    log_tokens(..., total_tokens=tokens, user_id=current_user.user_id)
```

---

## Files Created

### 1. `backend/app/core/budget.py` ✅

- `check_budget(db, user_id)` — computes daily/monthly usage against the
  user's `TokenBudget` row (falls back to the global default row), raises
  `BudgetExceeded` if over. No-op if no budget row exists or `enforce_limits`
  is `False` — budgets are opt-in, not a silent default-deny.
- `enforce_token_budget(...)` — FastAPI dependency wrapping `check_budget`,
  drop into any endpoint's signature as
  `current_user: CurrentUser = Depends(enforce_token_budget)`.
- `BudgetExceeded` — `HTTPException` subclass, status 429, `detail` includes
  `limit_type` (`daily_tokens` / `monthly_tokens` / `monthly_cost`).

### 2. `backend/tests/test_rate_limiting.py` ✅

29 tests: token-bucket isolation, per-user vs per-IP keying, expensive-path
detection, budget enforcement (no row / disabled / exceeded / within limits),
and `log_tokens()` persisting `user_id`.

---

## Files Modified

### 1. `backend/app/middleware/rate_limiter.py` — rewritten

- `_rate_limit_key(request)` — returns `("user:{id}", True)` when
  `request.state.user_id` is set (AuthMiddleware runs before this middleware —
  Starlette middleware order is LIFO, and `AuthMiddleware` is added after
  `RateLimitMiddleware` in `main.py`, making it outer/earlier), else falls
  back to `("ip:{host}", False)` for pre-auth routes (login, health).
- `_is_expensive(path)` — flags LLM-cost path prefixes: `/api/llm/`,
  `/api/code-review`, `/api/analysis/blueprint`, `/api/analysis/docs`,
  `/api/build`, `/api/review`, `/api/deploy`, `/api/dream-engine`,
  `/api/agent`, `/api/mentrix`.
- Two tiers per key: `general` (existing generous default, unchanged) and
  `llm` (new, strict default — 20 req/min, burst 10). A request must pass
  both. New env vars: `ZECT_RATE_LIMIT_LLM_RPM`, `ZECT_RATE_LIMIT_LLM_BURST`.

### 2. `backend/app/token_tracker.py`

`log_tokens()` gained a `user_id: int | None = None` parameter, persisted onto
`TokenLog.user_id`. Backward-compatible (defaults to `None`, same as before)
so existing call sites don't break — but every LLM-spending call site was
updated to pass it (see below).

### 3. `backend/app/routers/llm.py`

`ask_question`, `generate_plan`, `enhance_blueprint` now take
`current_user: CurrentUser = Depends(enforce_token_budget)` and pass
`current_user.user_id` into `log_tokens(...)`.

### 4. `backend/app/review_service.py`

`review_pr_diff`, `review_code_snippet`, `review_repo_files` gained a
`user_id: int | None = None` parameter, threaded into their `log_tokens(...)`
calls.

### 5. `backend/app/routers/code_review.py`

`review_pull_request`, `review_snippet`, `review_full_repo`, `auto_fix_loop`
now take `current_user: CurrentUser = Depends(enforce_token_budget)` and pass
`user_id=current_user.user_id` into the service calls. `auto_fix_loop` calls
`review_pull_request` as a direct Python function (not over HTTP) in its
retry loop — it now passes `current_user=current_user` explicitly so the
already-checked budget carries through instead of trying to re-resolve a
`Depends(...)` default at call time.

### 6. `backend/.env`

- Fixed a **pre-existing blocking bug**: `ENCRYPTION_KEY` was still the literal
  placeholder `b'XXXXXXX...'` left over from Fix #1's example text — the app
  could not start (`Fernet key must be 32 url-safe base64-encoded bytes`) and
  no test in the whole suite could run. Replaced with a real generated key.
- Added commented-out `ZECT_RATE_LIMIT_LLM_RPM` / `ZECT_RATE_LIMIT_LLM_BURST`
  alongside the existing rate-limit env vars.

---

## Why Two Tiers Instead of One

A single per-user bucket can't distinguish "checking project status 50
times/min" (free) from "50 code reviews/min" (real money). Splitting into a
generous `general` tier and a strict `llm` tier means normal UI polling never
trips the limiter, while LLM-cost paths get throttled independently — and the
`llm` tier is deliberately loose enough not to block a legitimate one-prompt
workflow (Ask → Plan → a few Build/Review calls) but tight enough to stop a
runaway script or compromised token from generating an unbounded bill.

## Why Budget Enforcement Is Separate From Rate Limiting

Rate limiting caps *request frequency*; token budgets cap *spend*. A user
could stay under 20 req/min and still burn through a $50/day budget with a
handful of large-context requests. `enforce_token_budget` is the dependency
that closes that gap — it's opt-in per `TokenBudget.enforce_limits`, so
orgs that haven't configured budgets see no behavior change, but once a budget
is set, it's now actually enforced instead of just displayed on a dashboard.

---

## Tests

```bash
cd backend
python -m pytest tests/test_rate_limiting.py -v
# 29 tests: bucket isolation, per-user keying, expensive-path detection,
# budget enforcement (no row / disabled / exceeded / within limits), log_tokens user_id
```

Regression-checked against Fixes #1–#3:

```bash
python -m pytest tests/test_encryption.py tests/test_cors.py tests/test_rbac.py tests/test_rate_limiting.py -v
# 94 passed, 6 failed
```

The 6 failures are pre-existing and unrelated to this fix: `test_rbac.py`'s
`@pytest.mark.asyncio` decorators need the `pytest-asyncio` plugin, which
isn't installed. Fixing that means adding a dependency to `requirements.txt`,
which needs your explicit approval per the global rule — flagging it here
rather than changing it silently.

---

## Deployment Checklist

### Pre-Deployment
- [ ] Decide per-user or per-team `TokenBudget` defaults before turning on `enforce_limits`
- [ ] Confirm `ZECT_RATE_LIMIT_LLM_RPM` / `ZECT_RATE_LIMIT_LLM_BURST` fit real usage patterns (defaults: 20 req/min, burst 10)

### Staging Deployment
- [ ] Set `ZECT_RATE_LIMIT_DISABLED=false` (currently `true` in `.env` for local/e2e — intentionally left as-is here since flipping it changes local dev/e2e behavior; production `.env` should not inherit this)
- [ ] Create a `TokenBudget` row with `enforce_limits=true` for a test user, verify `/api/llm/ask` returns 429 once the daily limit is hit
- [ ] Verify two users don't share a rate-limit bucket (fire concurrent requests as two accounts)
- [ ] Run `pytest tests/test_rate_limiting.py -v`

### Production Deployment
- [ ] Set `ZECT_RATE_LIMIT_DISABLED=false`
- [ ] Set real `ENCRYPTION_KEY` per-environment (never reuse the dev key committed here)
- [ ] Monitor 429 rates on `/api/llm/*`, `/api/review/*` — tune `ZECT_RATE_LIMIT_LLM_RPM` if legitimate traffic gets throttled
- [ ] Monitor `TokenLog.user_id IS NULL` rate — should drop to ~0 for the endpoints touched in this fix; any remaining nulls point at an LLM call site that still needs `user_id` threaded through (Build/Deploy/Dream Engine, once those backends exist)

---

## Security Improvements

| Vector | Before | After | Status |
|--------|--------|-------|--------|
| Rate limit bypass via IP rotation | Trivial (IP-only bucket) | Requires a new authenticated user per rotation | 🔴→🟢 HIGH |
| Shared bucket across users behind NAT | One user exhausts it for all | Per-user bucket | 🔴→🟢 MEDIUM |
| Unbounded LLM spend per user | No enforcement path existed | 429 at configured daily/monthly limit | 🔴→🟢 HIGH |
| Per-user usage attribution | Always `NULL` | Populated on every LLM-spending call touched | 🔴→🟢 MEDIUM |
| App startup broken (placeholder key) | Crashed on boot | Fixed | 🔴→🟢 CRITICAL |

---

## Remaining Gaps (Out of Scope for This Fix)

- `Build`, `Deploy`, `Dream Engine` routers don't call an LLM yet (confirmed
  UI-only in the earlier ZECT UX assessment) — nothing to wire budget
  enforcement into until those backends exist.
- `pytest-asyncio` missing from `requirements.txt` — blocks 6 pre-existing
  `test_rbac.py` async tests; needs your sign-off to add.
- `ZECT_RATE_LIMIT_DISABLED=true` remains in the local `.env` — intentional,
  matches the existing "local/e2e high defaults" comment in the middleware;
  production `.env` must set this to `false` explicitly.

---

## Summary

✅ **Fix #4 closes the loop between rate limiting, token budgets, and per-user attribution:**
- Rate limiter now keys on the authenticated user, with a stricter dedicated tier for LLM-cost paths
- `enforce_token_budget` dependency makes `TokenBudget.enforce_limits` actually block requests, not just display a dashboard number
- Every confirmed-working LLM call site (`Ask`, `Plan`, `Enhance Blueprint`, PR/snippet/repo code review, auto-fix loop) now attributes usage to `user_id`
- Fixed a blocking placeholder-key bug from Fix #1 that prevented the app — and the entire test suite — from starting at all
- 29 new tests, all passing; full regression pass on Fixes #1–#3 (94/100 passing, 6 pre-existing unrelated failures)

**All 4 Week 1 critical security fixes are now complete:** XOR→Fernet encryption, CORS hardening, RBAC enforcement, per-user rate limiting + token budgets.
