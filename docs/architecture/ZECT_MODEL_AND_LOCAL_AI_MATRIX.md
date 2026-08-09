# ZECT Model and Local AI Matrix

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)  
**Live code:** `backend/app/adapters/llm/openai_compat.py`, `fallback_policy.py`, `local_model_matrix.py`  
**API:** `GET /api/system/model-readiness`

## Hard rule

**`claim_fully_local: false`** — do not claim a fully local AI stack. Acceptance matrix is authoritative.

## Gateway & fallback

| Item | Value |
|------|-------|
| Local gateway | `ZECT_LLM_BASE_URL` (+ `ZECT_LLM_API_KEY`, `ZECT_LLM_CHAT_MODEL` / `MENTRIX_COMPANION_MODEL`) |
| Cloud | `OPENAI_API_KEY` when no local base (and Anthropic for some ForgeLoop build paths) |
| Fallback policy | `ZECT_MODEL_FALLBACK_POLICY` = `never` \| `ask` \| `automatic` (**default `never`**) |
| `never` behavior | Blocked cloud context; no silent fallback (`test_fallback_policies_never_ask_automatic`) |

Ask/Plan/Blueprint (llm_phase) use `resolve_model_route` + openai_compat. Companion uses gateway but does **not** fully enforce the same route helper (accepted as PARTIAL).

## Accepted matrix (post-merge)

| Surface | Status | Notes |
|---------|--------|-------|
| Ask | **PARTIAL** | openai_compat + policy; live local needs gateway |
| Plan | **PARTIAL** | same |
| Companion | **PARTIAL** | gateway path; policy enforcement gap |
| Agent/Coding | **PARTIAL** | deterministic smoke verified in pytest; live LLM needs gateway |
| ForgeLoop | **PARTIAL** | Ask/Plan local-capable; Build often cloud unless mentrix_native |
| Ultra Review | **CLOUD_ONLY** | LLM review path; 3-lane merger is offline |
| Blueprint | **PARTIAL** | openai_compat + policy |
| Embeddings | **CLOUD_ONLY** | OpenAI embeddings; no local embedding gateway |

Statuses are computed at runtime by `build_local_model_matrix()` (`VERIFIED` \| `PARTIAL` \| `CLOUD_ONLY` \| `BLOCKED`).

## Visibility

Model route fields exposed on model-readiness: `provider`, `blocked`, `fallback_used`, `fallback_reason`, plus `optimizations[]` and embedded `matrix`.
