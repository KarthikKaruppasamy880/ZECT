# ZECT Present S2 Acceptance — Template Intelligence + PresentationProvider

**Date:** 2026-08-14  
**Branch:** `feat/present-s2-template-provider`  
**Base:** `develop` `98e19e64045543ea306d7e1ff003e9df9992d9ef`  
**Scope:** S2 only. Presenton remains the **default** generate engine. Native PPTX generate is **not** claimed.

## Verdict

**S2_PASS** — provider ABC, TemplateDefinition importer, architecture isolation, and Presenton-default generate path landed. Native generate remains a 501 stub (S3–S4).

Final tranche verdict is **not** `ZECT_NATIVE_PRESENTATION_COMPLETE`. This file covers S2 only.

## What shipped

| Item | Status |
|------|--------|
| `PresentationService → PresentationProvider → PresentonProvider \| ZectNativePresentationProvider` | PASS — default `ZECT_PRESENTATION_PROVIDER=presenton` |
| Domain routes no longer import `presenton_client` | PASS — Mentrix `/presenton/*` and companion integrations go through `PresentationService` |
| `TemplateDefinition` JSON beside registry | PASS — SHA, theme, masters, layouts, placeholders, geometry, preview, `ready` |
| Secure PPTX importer | PASS — zip bomb / traversal / symlink / size limits; in-memory ZipFile only |
| User/org upload → native TemplateDefinition | PASS — valid OOXML with theme+master+layout is gallery `READY` |
| Admin Zinnia/org master import | PASS — `POST /api/mentrix/presentation/templates/import-master` (admin) |
| Native generate | **Not in S2** — `native_generate_not_implemented` HTTP 501; does **not** call Presenton |
| Presenton default generate | Unchanged contract — still requires registry mapping for `zinnia_verified`; never silent `modern` |
| Presenton removed | **No** |

Honest split: gallery `READY` from a native TemplateDefinition does **not** set Presenton `zinnia_verified`. Presenton generate still 409 `TEMPLATE_NOT_READY` until a real provider master is mapped.

## Tests

| Suite | Result |
|-------|--------|
| Architecture (`test_presentation_architecture`) | PASS — `app/domains` has no `presenton_client` import; `ZectPresent.tsx` has no Presenton client/types |
| Importer security (`test_template_importer`) | PASS — theme/master parse, zip-slip, zip-bomb, symlink attr |
| Service (`test_presentation_service`) | PASS — default Presenton; native 501; Presenton generate not called |
| Registry (`test_present_template_registry`) | PASS — including isolation of `ZINNIA_PRESENTON_TEMPLATE_ID` |
| Presenton client (`test_presenton_client`) | PASS |
| Frozen subset + S2 (packaging, registry, multi-repo, voice clone, editor hygiene, S2 new) | **82 passed, 1 skipped** |
| Frontend vitest | **62 passed** |
| Headed `core-ux-hygiene.spec.ts` + `present-editor-export.spec.ts` | **PASS** (3 passed / 1.1m, chromium headed, `VITE_API_URL=http://127.0.0.1:8000`) |

## Mentrix Ultra Review (branch-introduced)

| ID | Sev | Finding | Classification | Disposition |
|----|-----|---------|----------------|-------------|
| UR-S2-1 | Major | Domain imported Presenton client | ALREADY_FIXED | Routes use PresentationService |
| UR-S2-2 | Major | Zip bomb / zip-slip on template upload | ALREADY_FIXED | Importer rejects; upload deletes bytes on `UnsafePptxError` |
| UR-S2-3 | Major | Native READY implying Presenton zinnia_verified | ALREADY_FIXED | `resolve_presenton_template_id` unchanged; test proves split |
| UR-S2-4 | Minor | Provider UUID in public definition | ALREADY_FIXED | `public_definition` hides bindings; upload response strips `path` |
| UR-S2-5 | Minor | `ZectPresent` user copy named Presenton | ALREADY_FIXED | Copy no longer mentions Presenton UI |

No unresolved Critical/Major on this PR.

## Security negatives exercised

- Malicious/non-zip PPTX rejected (`unsafe_or_invalid_pptx`)
- `../` zip member rejected
- Claimed huge member / compression ratio rejected
- Symlink `external_attr` rejected
- Cross-user: user templates still not listed for another user_id
- Provider UUID not in preview payload
- Native generate stub never calls `generate_presentation`

## Not in S2 (do not claim)

- Native PPTX renderer / python-pptx (S4)
- PresentationPlan / Model Gateway planner (S3)
- Editor document model (S5)
- Voice parity (S6)
- Parity benchmark (S7)
- Default switch or Presenton removal (S8C/D)

## Next

S3 `PresentationPlan` on a focused PR after this branch merges to `develop`. Keep Presenton default.
