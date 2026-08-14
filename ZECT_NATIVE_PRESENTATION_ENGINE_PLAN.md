# ZECT Native Presentation Engine Plan (reconciled S1)

**Date:** 2026-08-14  
**Against:** `develop` `98e19e64045543ea306d7e1ff003e9df9992d9ef`  
**Audit:** `ZECT_DEPENDENCY_SOVEREIGNTY_AUDIT.md`  
**Roadmap source:** `prompts/ZECT_OSS_SOVEREIGNTY_NATIVE_ENGINES_PLAN.md` S2–S8  
**S1 recommendation:** **GO**  
**Presenton:** keep as default provider until S8 C/D. **Do not remove.**

This file replaces assumptions in the original prompt with what the tree actually does.

---

## 1. Current architecture (as-built)

S2 introduces `PresentationService` + `PresentationProvider`. Generate on `develop` `98e19e6` was a direct HTTP client; S2 wraps it. Presenton stays default:

```text
ZECT Present UI  (/present, PresentDeckPanel)
        │
        ▼
Mentrix routes  /api/mentrix/presenton/status|templates|generate
                /api/mentrix/present/*  (parse, save-notes, pptx download)
        │
        ├── template_registry.py     ZECT canonical ids + local PPTX bytes
        ├── presenton_client.py      HTTP to PRESENTON_BASE_URL
        ├── pptx_parse.py            zip/XML text+notes
        └── pptx_paths.py            allowlist + notes sidecar
```

Presenton (operator Docker `ghcr.io/presenton/presenton:latest`) owns **prompt → PPTX file**.  
ZECT already owns **gallery UX, editor UX, notes persistence, export download, voice selectors, audience/claims/sensitivity helpers**.

### Already ZECT-native (do not rebuild)

| Piece | Location | Keep |
|-------|----------|------|
| Product UI / steps / gallery cards | `ZectPresent.tsx` | Yes |
| Editor thumbs, notes, save, UI export | `PresentEditor.tsx` | Yes — evolve model in S5, do not replace with Presenton UI |
| Deck panel generate + voice | `PresentDeckPanel.tsx` | Yes |
| Canonical Zinnia/org/user ids | `template_registry.py` | Yes — extend to TemplateDefinition |
| Local PPTX template storage | `.zect/present-templates/` | Yes |
| Sensitivity / audience / claims | `presentation/sensitivity.py`, `audience.py`, `claims.py` | Yes — feed S3 PresentationPlan |
| Zip/XML parse of slide text+notes | `pptx_parse.py` | Yes until S4 renderer owns round-trip |
| Allowlisted download + notes sidecar | `pptx_paths.py` | Yes |
| Voice clone / stock / none + audio_owner | Voicebox + Present Deck | S6 reuses; PPTX must not depend on TTS |

### Presenton wire surface (only these)

| Method | Path | ZectNative replacement |
|--------|------|------------------------|
| POST | `/api/v1/auth/login` | None (in-process provider) |
| GET | `/api/v1/ppt/template/all` | Registry list of TemplateDefinitions |
| POST | `/api/v1/ppt/presentation/generate` | Native pipeline S3–S4 |
| GET | generate `path` / `edit_path` | ArtifactStore + allowlisted write |

Not used, not in S2–S8 parity unless later scoped: Presenton admin UI, editor chrome, streaming internals, image generation (runbook sets `DISABLE_IMAGE_GENERATION=true`), Presenton Cloud.

---

## 2. Target boundary (introduce in S2, first production PR)

```text
PresentationService  (ZECT)
    └── PresentationProvider   (new ABC)
            ├── PresentonProvider      (wrap presenton_client; default)
            └── ZectNativePresentationProvider  (experimental)
```

Rules:

- Mentrix `/presenton/generate` becomes `PresentationService.generate(...)` choosing provider by config (`ZECT_PRESENTATION_PROVIDER=presenton|zect_native`, default `presenton`).
- Domain code and React **must not** import `presenton_client`.
- Architecture test: `app/domains` and `frontend/src/pages/ZectPresent.tsx` do not reference Presenton types.
- Canonical artifacts: ZECT template id, ZECT presentation id, local PPTX path, notes sidecar. Never require `presentation_id` / Presenton UUID for save/export/editor.
- LLM calls go through existing Model Gateway / `openai_compat` only. **Forbidden:** Presenton container `LLM=` / `OPENAI_API_KEY` as the native path.

Reuse: Model Gateway, ContextEngine, Document/Web/Project Intelligence, Permission Broker, ArtifactStore (allowlisted paths), template registry, EvidenceVerifier, Voicebox, current Present UI. **No** second RAG, gateway, or registry.

---

## 3. What ZectNative must replace (parity object)

From live generate payload:

```text
content, n_slides (3–20), language=English, template=<provider or mapped id>,
export_as=pptx, optional instructions
→ PPTX bytes + local path under Documents/Desktop
```

| Capability | Presenton today | ZectNative |
|------------|-----------------|------------|
| Prompt understanding | Inside engine + its LLM | Prompt/Intent Planner via Model Gateway + audience/sensitivity already in-tree |
| Slide count / language | Payload fields | PresentationPlan schema |
| Outline + slide bodies | Opaque engine | Outline Planner + Slide Planner (structured JSON, not free prose) |
| Template apply | Presenton master UUID or built-in name | TemplateDefinition (theme, masters, layouts, placeholders, fonts, colors, geometry) |
| Zinnia fidelity | Registry maps `zinnia-*-v1` → provider UUID | Same ZECT ids; importer fills TemplateDefinition from org PPTX; `zinnia_verified` iff definition ready — **never** silent `modern` |
| Org/user uploaded PPTX | Stored locally, often **unbound** | S2 importer: bytes already on disk → TemplateDefinition → READY without Presenton |
| Images/charts/tables | Engine (images disabled in runbook) | S4/S5: supported subset only; honest PARTIAL until proven |
| Notes | May exist in generated PPTX; ZECT sidecar is source of truth after edit | Notes Generator + sidecar + OOXML notes |
| Validation | Implicit | Explicit PPTX zip/XML validate before `ok: true` |
| Export | File download of generated path | Same allowlisted FileResponse |
| Failures | 428/401/502/timeout mapped to lifecycle | Same lifecycle enum; `PROVIDER_UNAVAILABLE` only for PresentonProvider |

Lifecycle enum **stays**: `STARTING | READY | TEMPLATE_NOT_READY | PROVIDER_UNAVAILABLE | GENERATION_FAILED`.

---

## 4. Sequence (unchanged intent, corrected entry)

| Stage | Name | Exit criteria | Presenton |
|-------|------|---------------|-----------|
| **S2** | Template Intelligence + provider ABC | `PresentonProvider` default; `ZectNative` can import PPTX → TemplateDefinition → preview → registry READY for Zinnia/org/user; mapping file no longer **required** for native generate | Keep |
| **S3** | PresentationPlan | Structured plan from prompt + audience + count + template + authorized context + sensitivity; schema validated | Keep |
| **S4** | Layout + native PPTX renderer | Commodity OOXML library (**candidate: python-pptx 1.x MIT**, not in tree yet — add here, not S1). Preserve master/layout, text, notes, order; validate zip | Keep |
| **S5** | Provider-neutral editor model | Editor state = ZECT presentation document (slides, blocks, notes), not Presenton objects. Thumbs, select, text, notes, rewrite/shorten/executive/regenerate, add/delete/reorder as implemented; charts/images/tables honest | Keep |
| **S6** | Voice + Zinnia/user-template live parity | NarrationRouter unchanged; generate independent of TTS; headed clone/stock/none still on ZECT UI | Keep |
| **S7** | Parity benchmark | Same prompts/templates/slide counts through both providers; write `ZECT_NATIVE_PRESENTATION_PARITY_ACCEPTANCE.md` | Keep |
| **S8** | Switch gates | A default Presenton / native experimental → B both + opt-in → C native default + Presenton fallback → D remove Presenton runtime **only after sustained proof** | D only |

S9 Process / S10 Voice provider hardening are **out of this tranche** except reuse.

---

## 5. S2 design (next implementation PR — not this session)

### 5.1 TemplateDefinition (canonical)

Persist beside today’s registry (JSON + source PPTX SHA), not as Presenton UUID:

- `id` (ZECT), `version`, `scope` (`ZINNIA` / `ORG` / `USER`)
- `source_pptx_sha256`, `parser_version`
- slide size, theme colors/fonts, master/layout names, placeholder geometry, content regions, preview text/image
- `ready: bool` — READY only when parse succeeded and required layouts exist
- `provider_bindings: { presenton?: string }` optional, adapter-only

Zinnia cards `zinnia-executive-v1` / `delivery` / `risk` remain the user-facing ids.

### 5.2 Importer

`PPTX bytes → unzip → theme/slideMasters/slideLayouts → TemplateDefinition`.

Start from files **already** written by `register_user_pptx`. Admin can register a Zinnia master PPTX into the same root without Presenton UI.

### 5.3 Provider ABC (minimal)

```text
status() -> configured, reachable, lifecycle
list_engine_templates() -> optional adapter extras (Presenton only)
generate(PresentationGenerateRequest) -> path, bytes, zinnia_verified, lifecycle, provider
```

`PresentonProvider.generate` = current `generate_presentation` + existing resolve mapping (so default path does not regress).

`ZectNativePresentationProvider.generate` in S2 may return `TEMPLATE_NOT_READY` / experimental stub **only if** flagged experimental; do not switch default. Prefer S2 ending with importer + registry READY even if generate still Presenton.

**Honest split:** S2 can land ABC + importer without native generate. Native generate is S3–S4. Do not claim native PPTX until S4 validation passes.

---

## 6. S4 library choice (pre-decided candidate, add later)

Ownership does **not** require rewriting ZIP/XML primitives.

| Candidate | License evidence | Use |
|-----------|------------------|-----|
| **python-pptx** | MIT (PyPI 1.0.2) | Default candidate for create/update PPTX |
| stdlib zipfile/xml | PSF | Keep for parse/validate/hygiene |

Do **not** vendor Presenton renderer. Do **not** add python-pptx in S1.

---

## 7. Editor (S5) vs generate (S3–S4)

Today the editor:

- Parses text+notes only
- Saves notes sidecar (not always rewriting OOXML)
- Exports the **original** allowlisted PPTX file

Native generate must produce a real PPTX. S5 should round-trip notes into OOXML when the renderer exists. Until then, sidecar remains valid persistence (already headed-proven). Charts/images/tables stay PARTIAL until implemented.

---

## 8. Voice (S6)

```text
Presentation → notes/script → NarrationRouter
    → user clone | ZECT/local voice | approved provider | none
```

Reuse Voicebox, profiles, permissions, `audio_owner`, Disconnect FSM. **Generate/export must succeed if narration fails.**

---

## 9. Migration gates (do not skip)

| Gate | Default generate | Native available | Presenton |
|------|------------------|------------------|-----------|
| A | Presenton | Experimental / internal | Required |
| B | Presenton | Opt-in + parity tests | Required |
| C | Native | Yes | Fallback |
| D | Native | Yes | Removed from runtime; notices retained if any past distribution included it |

Never switch default merely because native code runs.

---

## 10. Tests / headed / security (each production PR)

- Unit: registry importer, schema, path allowlist, no Presenton import from domain
- Headed: existing `present-editor-export.spec.ts` + `core-ux-hygiene.spec.ts` must stay green on Presenton default
- Native generate headed only after S4
- Security: no provider UUID in UI; no secrets in PPTX paths; Model Gateway only; untrusted context tagged
- CI → Ultra Review → fix C/M on same PR → merge `develop` → sync → smoke

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Presenton `:latest` drift | Pin operator image in `PRESENTON_LOCAL.md` when convenient; unrelated to native code |
| Unmapped Zinnia silently used `modern` historically | Keep `TEMPLATE_NOT_READY`; native must not revive that lie |
| Dual poetry vs requirements.txt | When adding python-pptx, add to **both** or collapse manifests |
| TemplateDefinition incomplete vs Presenton masters | Parity benchmark S7; stay on Presenton default |
| LLM quality vs Presenton | Same Model Gateway models; measure in S7, do not swap default on a demo |

---

## 12. Out of scope for S2–S8

- Removing Presenton
- Graphify, OCR/XLSX, broader Web, new agents, KV cache
- Rewriting Electron/Playwright/Git
- Shipping ClamAV or Chatterbox weights as “native Present”
- Camunda/Jira rebuild (S9)

---

## S2 status (2026-08-14)

Implemented on `feat/present-s2-template-provider`. See `ZECT_PRESENT_S2_ACCEPTANCE.md`.

- Presenton remains default (`ZECT_PRESENTATION_PROVIDER=presenton`).
- Native generate is a 501 stub and does not call Presenton.
- TemplateDefinition importer is live for Zinnia/org/user PPTX.
- Do not remove Presenton. Next focused PR is S3 PresentationPlan.
