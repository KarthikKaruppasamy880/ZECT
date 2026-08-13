# ZECT Present R2.5 — Zinnia registry (no env for normal users)

**Branch:** `feat/r2.5-present-zinnia-registry`  
**Date:** 2026-08-13  
**Spec:** Next roadmap §R2.5  
**Base:** R2 Present reliability (`ZECT_PRESENT_R2_ACCEPTANCE.md`)

## Verdict

**PARTIAL** when Presenton is down or unreachable (`PROVIDER_UNAVAILABLE` / `BLOCKED_EXTERNAL`).  
Full PPTX PASS still requires a live Presenton instance **and** a ZECT registry mapping for the canonical template — not an env var on the normal-user path.

## What R2.5 changes

Canonical ZECT id **`zinnia-executive-v1`** (aliases `zinnia-exec`, `zinnia-executive`) is the product default. Delivery/risk stay `*-v1` as well.

Provider masters are bound in the **ZECT template registry** (`.zect/present-templates/canonical-mapping.json`, overridable via `ZECT_PRESENT_TEMPLATE_ROOT`). The UI sends the gallery id; the API resolves through the registry and returns honest `template_sent`, `zinnia_verified`, `lifecycle`, and `blocked_external`.

`ZINNIA_PRESENTON_TEMPLATE_ID` is **admin seed only**: it may copy a real Presenton master into the registry once for `zinnia-executive-v1`. Normal users do not read that env var. One env id is not a PASS for delivery/risk or unmapped uploads.

## Lifecycle (UI + API)

| State | Meaning |
|---|---|
| `STARTING` | Presenton configured; reachability not yet known |
| `READY` | Provider reachable and selected template mapped |
| `TEMPLATE_NOT_READY` | Provider up, but no verified registry mapping (or upload unbound) |
| `PROVIDER_UNAVAILABLE` | Not configured or not reachable — `BLOCKED_EXTERNAL` |
| `GENERATION_FAILED` | Generate attempted and failed |

Product Present shows `data-testid="present-lifecycle-state"`. Gallery cards use `data-testid="zect-present-template-{template.id}"` from the templates API (so executive is `zect-present-template-zinnia-executive-v1`). PPTX upload may optionally register under organization scope (`zect-present-upload-org-scope`; admin-only on the API).

## Classification

| Capability | Status |
|---|---|
| Canonical `zinnia-executive-v1` default + gallery id from API | **VISIBLE_AND_WORKING** |
| Registry mapping → `zinnia_verified` (no user env) | **VISIBLE_AND_WORKING** (false until mapped) |
| Env seed of executive-v1 into registry (admin bootstrap) | **VISIBLE_AND_WORKING** (not the user path) |
| Lifecycle badge `STARTING\|READY\|TEMPLATE_NOT_READY\|PROVIDER_UNAVAILABLE\|GENERATION_FAILED` | **VISIBLE_AND_WORKING** |
| User/org PPTX upload into ZECT registry | **VISIBLE_AND_WORKING** (local register; Presenton bind still PARTIAL) |
| Prompt → editable PPTX | **PARTIAL / BLOCKED_EXTERNAL** without Presenton |
| Headed e2e `template_sent` / `zinnia_verified` / `blocked_external` | **VISIBLE_AND_WORKING** (attempt recorded even if blocked) |
| Packaged Presenton | **BLOCKED_EXTERNAL** |

## Proofs

```text
cd backend
py -3.12 -m pytest tests/fixes_and_phases/test_present_template_registry.py tests/fixes_and_phases/test_presenton_client.py tests/fixes_and_phases/test_local_auth_admin.py --noconftest -q --tb=short
# PYTHONPATH=backend (from repo root) or PYTHONPATH=. (from backend/)

npx playwright test e2e/present-product.spec.ts --headed
# evidence.json note: PPTX PASS requires Presenton + registry mapping, not env
```

## Stop

Do not claim Present complete. Do not treat `ZINNIA_PRESENTON_TEMPLATE_ID` as the normal-user mapping path. Proceed to later roadmap items after merge.
