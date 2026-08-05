# ZOAS + Present Deck Playwright demo (headed)

Recorded: 2026-07-29 (headed Chromium, slowMo 450ms, video+screenshot+trace on)

## PR
Merged into develop: https://github.com/KarthikKaruppasamy880/ZECT/pull/51

## How to re-run (visible browser)
```powershell
# backend on :8000 with ZECT_USERNAME / ZECT_PASSWORD
cd frontend
# load creds from backend/.env into env, then:
npx playwright test e2e/zoas-mentrix-full-delivery.spec.ts e2e/present-deck.spec.ts --config=playwright.demo.config.ts
```

## Artifacts
- `videos/` — one `.webm` per test (Present Deck + ZOAS full delivery + Ask/Plan handoff)
- `screenshots/` — stills from each test
- `test-results/` — raw Playwright output including `trace.zip` (open with `npx playwright show-trace`)

## Specs covered
1. Present Deck panel + Electron required hint
2. Present / Narrate Board + Chatterbox hint
3. Mocked Electron open_presentation
4. ZOAS Engage → Confirm plan → Approve → Create PR → SAST
5. Context pack 400 error
6. Ask → Plan → Mentrix handoff
