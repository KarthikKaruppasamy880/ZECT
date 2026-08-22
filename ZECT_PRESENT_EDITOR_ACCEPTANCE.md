# Present generate + native editor (PR2)

ZECT Present matches the Presenton operator flow on **Zinnia/org/user PPTX masters**. Community packs are not imported. No Presenton/Gamma branding in the UI.

## Generate + templates

- Prompt + attach + template pick → **Confirm outline** (`adapted_prompt`, slide count) → Generate
- Upload auto-selects the new master; gallery cover PNG renders even when `native_ready` is false
- Preview route `/present/templates/:id` shows a slide PNG strip of the master
- Fast-Basic requires an explicit **Draft without model** checkbox (never silent)

## Native editor

Palette tabs **AI | Blocks | Texts | Charts | Tables | Images | Elements** on Review.

- Charts: column/bar/line/pie/donut plus radar/area/stacked (python-pptx, SVG→PNG fallback)
- Elements: rect / ellipse / arrow (`MSO_SHAPE`)
- Native generate uses the uploaded master file whenever it exists (`used_master`) so Review is a filled PNG, not empty boxes
- Save still OOXML round-trip; export stays PPTX
