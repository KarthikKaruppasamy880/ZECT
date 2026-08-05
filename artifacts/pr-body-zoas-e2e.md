## Summary
- Mocked Playwright ZOAS Mentrix Delivery suite (Engage → Confirm plan → Approve → Create PR → Ultra Review SAST) plus Ask→Plan→Mentrix handoff
- Companion Present Deck: open prepared `.pptx` + Zoom via Electron, narrate talking points with Chatterbox; Present/Narrate Board-artifact hint
- Mentrix plan-confirm gate, GitHub Check Runs Semgrep/SAST panel, Chatterbox voice persistence, Lattice/operator docs (MSTF stays MinionBot-only)

## Test plan
- [x] `npx playwright test e2e/zoas-mentrix-full-delivery.spec.ts e2e/present-deck.spec.ts` (mocked, auth from `ZECT_*`)
- [ ] Manual Electron: Present Deck open PPTX + Zoom; Narrate with default clone
- [ ] Mentrix bugfix: Engage → Confirm plan → Approve → Create PR with workspace + Lattice key
- [ ] Ultra Review SAST panel refresh against a Semgrep-enabled ref
