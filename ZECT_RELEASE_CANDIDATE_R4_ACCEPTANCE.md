# ZECT Release Candidate R4 — Full Baseline E2E Acceptance

**Date:** 2026-08-13  
**Spec:** Next roadmap §R4 (stop before R5+)  
**Final `develop` SHA:** `2724fef9e71a8aee23e739b9f2c87654d68bfa25`  
**local == origin/develop:** YES (post-sync)

## Verdict

**BASELINE_ADVANCED — release candidate with documented PARTIALs.**  
R1–R4 roadmap tranches merged via CI (#142–#144). Not one-click / not full Presenton / not multi-PR ship complete.

## R1–R4 tranche summary

| Tranche | PR | Verdict | Evidence |
|---------|-----|---------|----------|
| R1 Packaging lifecycle | #142 | **PARTIAL** | single-instance, lifecycle, :8000 default; backend not bundled |
| R2 Present PPTX reliability | #143 | **PARTIAL** | ui_template_choice, zinnia_verified honesty, 502 retry; Presenton external |
| R3 Multi-repo ASK/PLAN | #144 | **PARTIAL (advanced)** | context_by_repository, manifest, verifier block; multi-PR ship deferred |
| R4 Full release E2E | — | **PASS (CI)** | GitHub CI green on `2724fef`; local roadmap unit subset green |

## Prior baseline (remediation)

| PR | Topic |
|----|-------|
| #139–#141 | Sidebar, Learning D, Present UI, multi-repo attach/switch |
| #133–#138 | Phases 9–13, Doc B, Web C, Repo UX, UR closed-loop |

## CI proof (develop @ merge)

- backend: PASS (#144 run)
- frontend: PASS
- e2e: PASS

## Local frozen subset (roadmap unit)

```text
test_desktop_packaging_honest_partial
test_service_lifecycle_exports_stop_and_single_instance_docs
test_presenton_client (full)
test_present_template_registry
test_multi_repo_developer
```

## Honest PARTIAL / BLOCKED (do not claim PASS)

| Item | Status |
|------|--------|
| Windows one-click Install→Ready | PARTIAL |
| Presenton full PPTX + zinnia_verified in all envs | BLOCKED_EXTERNAL without Presenton |
| Multi-repo multi-PR AGENT ship | PARTIAL |
| OCR/XLSX, Search/YT/Reddit, Graphify, KV cache | NOT_STARTED (R5+) |

## Security negatives (unchanged merged coverage)

- Learning D M1–M3, Doc/Web SSRF, UR mutating fix gated, packaging secrets out of installer

## Stop

R4 complete. **Do not start R5–R9** (KV cache, advanced Doc Intel, Web Intel expansion, Graphify, new agents).
