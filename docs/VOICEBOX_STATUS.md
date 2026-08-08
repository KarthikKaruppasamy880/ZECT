# Voicebox status (ZECT)

## Did we build our own Voicebox?

**Yes.** ZECT Voicebox is a **native** FastAPI service under `services/zect-voicebox/` on
`http://127.0.0.1:17493`. It is **not** the jamiepine upstream UI or a `:17494` proxy.

| Piece | Owner |
|-------|--------|
| HTTP API `/health` `/profiles` `/generate` | ZECT native |
| Profile + sample store | ZECT (`profiles.json` + sample dirs) |
| Synth backend | Chatterbox ML in Docker (`ZECT_VOICEBOX_SYNTH=chatterbox`) or stub |
| Mentrix clone rows | ZECT DB (`cloned_voices.voice_id` + `external_voice_id`) |

Third-party product names must not appear in UI branding; engine health may report synth id.

## Dual IDs (common 404 cause)

- `voice_id` — ZECT stable id (what the UI sends)
- `external_voice_id` — Voicebox profile UUID used by `/generate`

If Voicebox data is wiped or `external_voice_id` was wrongly set equal to `voice_id`,
`/generate` returns **404 profile not found**. Speak now verifies the profile exists,
clears stale ids, and re-provisions from the stored sample.

## Fallback policy

| Surface | Behavior |
|---------|----------|
| Companion Speak replies | Prefer clone; **OpenAI / browser fallback** if Voicebox fails (`require_clone=false`) |
| Present / Test speak | **Strict clone** — fail loudly if Voicebox cannot synthesize |

## Where to manage voice

**Settings → Voice** (sidebar bottom account chip), not collapsed into Companion Chat.
Companion Voice tab keeps Present deck + link to Settings.
