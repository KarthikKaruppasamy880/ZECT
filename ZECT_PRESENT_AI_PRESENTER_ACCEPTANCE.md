# Present AI Presenter — acceptance

READY means no known release-blocking Critical/High, not “100% / zero error.”

## Narration

- Present All uses Presenter Intelligence (`POST /api/mentrix/presentation/narrate-slides`) grounded in slide text, notes, and chart/table/diagram markers.
- No 500-character meaning cap (`PRESENT_SLIDE_SCRIPT_CAP` is a high ceiling only).
- Word budget: 220 words per slide. Numbers not on the slide are not invented.
- Wait for full audio. Empty/error/cancel does **not** send PowerPoint Right Arrow.
- Manual Narrate (talking points) stays separate from Present All.
- Rehearse is on the Edit | Quality | Rehearse | Export strip (`present-studio-phases`). Do not narrate from Generate.

## Gallery

- Delete is hidden for `zinnia-*`, `org-standard`, `org-delivery`.
- Raw `not_found` is replaced with a human sentence.
- **Delete all unmapped uploads** removes TEMPLATE_NOT_READY user/org uploads only — never canonical Zinnia ids.

## Out of scope

- Presenton community templates are not vendored.
- `electron.exe` is not added to WIN_APPS.
- Local vs Zoom share checkbox remains as shipped.
