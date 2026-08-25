# ZECT Present — Template Studio acceptance (E2 / E3)

## Required journey

`Templates → Built-in / Organization / My Templates → visual cards → Preview → Use (Generate) or Open in editor`.

| Action | Behavior |
|---|---|
| Single-click card | Select + PNG slide strip (`zect-present-template-preview`) |
| **Open in editor** / double-click card | `POST /api/mentrix/present/from-template` clones the master PPTX into the allowlisted dir and routes to `/present/d/:id/edit` |
| **Use this template** (`zect-present-continue-generate`) | Stays on Generate (PresentDeckPanel). Do not change this for present-product e2e |
| Upload PPTX | Zip-safe ingest → registry → select uploaded id. Org checkbox = ORG scope |
| Preview route | `/present/templates/:id` — slide PNG strip + Open in editor |

Built-in Zinnia ids: `zinnia-executive-v1`, `zinnia-delivery-v1`, `zinnia-risk-v1`. No Presenton Community packs.

## Remaining (not PASS)

- Template Edit mode vs Slide mode is not a separate document mode; Open in editor is **slide mode on a cloned master**.
- Upload inspects masters/layouts into `TemplateDefinition` JSON; it does not yet open a dedicated master editor.
- Headed proof that every Zinnia lockup matches PowerPoint pixels without COM is **BLOCKED_EXTERNAL** unless `ZECT_LIVE_PPT_COM=1`.
