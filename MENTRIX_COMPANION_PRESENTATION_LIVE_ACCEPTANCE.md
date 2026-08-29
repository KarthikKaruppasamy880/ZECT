# MENTRIX_COMPANION_PRESENTATION_LIVE_ACCEPTANCE

**Date:** 2026-08-11  
**Branch:** `feat/companion-presentation-live-acceptance`  
**Base:** latest `develop` @ `02c0370` (pulled clean before work)  
**Login:** `karthik.karuppasamy@zinnia.com` (local `.env`; role **admin**)  
**Overall verdict:** **LIVE_VIABLE** (with exact blockers below — no fake PASS)

---

## Startup status

| Service | Port | Status |
|---------|------|--------|
| Backend uvicorn | `127.0.0.1:8000` | UP (clean shell; no `ZECT_PYTEST`) |
| Frontend Vite | `127.0.0.1:5173` | UP |
| Electron | desktop | UP (processes observed) |
| Presenton Docker | `127.0.0.1:5000` | UP after `LLM=openai` + admin auth + session login |
| ZECT Voicebox | `127.0.0.1:17493` | UP — `models_ready: true`, `synth: chatterbox-mtl` |

**Auth note:** Prior 401s were caused by leftover `ZECT_PYTEST=1` preserving `test@zect.local`. Interactive uvicorn now ignores stray pytest flags unless a real pytest runner is detected.

---

## Companion

| Check | Result | Evidence |
|-------|--------|----------|
| Local login (Zinnia admin) | **PASS** | `POST /api/auth/login` → 200; `users.role=admin` |
| Login UI hint | **PASS** | No longer implies only `admin@zect.local` |
| Companion integrations | **PASS** | `presenton=true`, `presenton_reachable=true`, `openai=true`, `jira=true`, `github=true`, `slack=false` |

---

## Personal Assistant

| Check | Result | Evidence |
|-------|--------|----------|
| Daily Brief | **PASS** | `POST /api/personal-actions/daily-brief` → `ok: true` |
| PersonalActions list | **PASS** | Endpoint reachable under auth |
| Connector health matrix | **PASS** (honest) | See Connectors |

---

## Connectors

| Connector | Result |
|-----------|--------|
| Jira | **PASS** (configured; env token present — live write not forced this run) |
| GitHub | **PASS** (configured) |
| Zoom | **PASS** (configured connector; join URL optional) |
| Filesystem / Browser | **PASS** (configured) |
| M365 / Graph | **BLOCKED_EXTERNAL** — `missing_creds` |
| Email IMAP/SMTP | **BLOCKED_EXTERNAL** — `missing_creds` |
| Slack | **BLOCKED_EXTERNAL** — `missing_creds` |

---

## Voice Clone

| Check | Result | Evidence |
|-------|--------|----------|
| Voicebox health + `models_ready` | **PASS** | `/health` → `ok`, `models_ready: true` |
| Per-user voice list | **PASS** | `GET /api/mentrix/voice/voices` → owner’s “Karthik” only; pytest isolation |
| Cross-user isolation | **PASS** | `test_voices_are_isolated_per_user` — foreign voice → 404 |
| Multi-sentence TTS (stock fallback) | **PASS** | `audio/mpeg` ~81KB (`x-mentrix-tts-engine: openai_tts_fallback`) |
| Clone TTS + WAV playback | **PASS** | `require_clone=true` → `audio/wav` 167084 bytes, engine `zect_voicebox` |
| Voicebox down honesty | **PASS** | When probe fails, Present/clone narrate disabled / 503 — not faked online |
| Cancel mid-speak | **PARTIAL** | UI Stop control present; not timed in this API probe |

---

## Existing Deck flow

| Step | Result | Evidence |
|------|--------|----------|
| Analyze notes → audience / sensitivity / claims | **PASS** | `POST .../analyze-deck` → `ok: true`, `PUBLIC`, claims extracted |
| Improved notes / rehearse_ready | **PASS** | Response includes `improved_notes`, `rehearse_ready`, `zoom_share_required: true` |
| Narration / slideshow (Electron F5) | **PARTIAL** | Electron up; share-approve checkbox retained; full F5 slideshow not automated this run |

---

## Prompt → Deck flow

| Step | Result | Evidence |
|------|--------|----------|
| Prepare prompt (audience, outline, claims) | **PASS** | `prepare-prompt` PUBLIC → `ok: true`, provider `cloud` |
| Approval / sensitivity gate | **PASS** | Flow B requires approval for unverified claims (UI) |
| Presenton generation | **PASS** | PPTX written: `C:\Users\karuppk\Documents\mentrix-live-accept.pptx` (305573 bytes) |
| `template_sent` on wire | **PASS** | Response: `template_sent: "modern"`, `presenton_request.template: "modern"` |

**Code fix enabling PUBLIC prepare:** `enforce_model_route` uses `policy="automatic"` for PUBLIC/INTERNAL so Companion Present is not blocked by coding-agent default `ZECT_MODEL_FALLBACK_POLICY=never`. RESTRICTED still forces `never`.

---

## Zinnia verification

| Check | Result | Evidence |
|-------|--------|----------|
| UI Zinnia preset alone | **NOT PASS** (honest) | `zinnia-exec` → wire id `modern`, `zinnia_verified: false` |
| Env/custom master ID | **BLOCKED** | `ZINNIA_PRESENTON_TEMPLATE_ID` unset; no uploaded Presenton master id in this run |
| Generate with proven id `modern` | **PASS** | Wire + saved PPTX (not a Zinnia brand PASS) |

---

## Zoom

| Check | Result | Evidence |
|-------|--------|----------|
| Open / join assist | **PARTIAL** | Connector configured; default join URL not set |
| Explicit screen-share approval | **PASS** | `shareApproved` checkbox required before Present-all on desktop; **no auto-share** |
| Scheduling / auto-share | **NOT CLAIMED** | Not implemented |

---

## Confidentiality

| Check | Result | Evidence |
|-------|--------|----------|
| Voice ownership isolation | **PASS** | Per-user list/default/delete; pytest A vs B |
| RESTRICTED cannot silent-cloud | **PASS** | `prepare-prompt` with `sensitivity_hint=RESTRICTED` → `ok: false`, `model_route.blocked: true`, `forbid_external_retrieval: true`, provider `none` |
| Desktop delete denied | **PASS** (code) | `electron/computer.js` → `delete_never_allowed` |

---

## Latency (approx, this run)

| Op | Note |
|----|------|
| Presenton generate (3 slides) | ~2–3 min wall clock including LLM |
| Clone speak (3 sentences) | ~2 min first cold; WAV 167KB |
| Stock TTS fallback | ~seconds; MPEG ~81KB |

---

## Tests

```text
pytest tests/fixes_and_phases/test_local_auth_admin.py \
       tests/fixes_and_phases/test_presenton_client.py \
       tests/fixes_and_phases/test_voice_cloning.py -k "voices_are_isolated or ..."
→ 9 passed (auth promote, Zinnia resolve honesty, Presenton client, voice isolation)
```

---

## Exact blockers

1. **Zinnia brand master PASS** — requires `ZINNIA_PRESENTON_TEMPLATE_ID` or Custom template id from Presenton Template Studio upload; UI preset alone must not be marked PASS.
2. **M365 / Slack / IMAP** — `BLOCKED_EXTERNAL` (`missing_creds`).
3. **Full Electron Present-all + Zoom join URL** — share-approve proven in UI code; end-to-end meeting share not executed in this probe.
4. **Presenton ops** — needs `LLM=<provider>`, admin `AUTH_USERNAME`/`AUTH_PASSWORD`, and Mentrix `PRESENTON_USERNAME`/`PRESENTON_PASSWORD` (session cookie auth). Misconfig → honest unreachable / generate fail (not faked).

---

## Fixes shipped in this acceptance branch (gap-only)

- Ignore stray `ZECT_PYTEST` outside real pytest; log local login identity.
- Promote configured local user to **admin** on login.
- Login hint no longer hardcodes only defaults.
- Presenton client: session-cookie auth; `items` template list; `template_sent` evidence; auth/setup → `blocked_external`.
- Integrations / Present Deck: `presentonReady` = configured **and** reachable.
- Zinnia resolve honesty + `ZINNIA_PRESENTON_TEMPLATE_ID` support.
- PUBLIC/INTERNAL presentation model route may use cloud; RESTRICTED stays never.
- Voice cross-user isolation test.

**No new Developer architecture.** Secrets / `.env` not committed.
