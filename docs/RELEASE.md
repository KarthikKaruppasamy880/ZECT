# ZECT Commercial Release Notes (Phase 11)

Placeholders for packaging, licensing, and operational readiness.

## Branding

Third-party engines (coding runtimes, editors, browser automation libraries, voice providers) run behind ZECT-owned adapters. Product UI, routes, and public APIs must not brand those vendors (except the dedicated `/tool-comparison` planning page). Legal attribution lives in `THIRD_PARTY_NOTICES.md`.

## Self-host vs paid APIs

| Capability | Self-host option | Paid API option |
|---|---|---|
| LLM / Mentrix | Local model endpoint via env | Cloud LLM keys in Secrets Manager |
| Voice TTS | Local clone engine when configured | Cloud TTS fallback when key present |
| Browser automation | Local Chromium via Mentrix browser adapter | — |
| Coding engine | Mock / local sandbox | Optional remote Agent Server |

## Release checklist (gates)

- [x] Dependency / license scan reflected in `THIRD_PARTY_NOTICES.md`
- [x] Sample credentials removed from shipped configs (gitignore `.env*`)
- [x] Electron `appId` stable (`com.zinnia.zect`)
- [x] Support bundle generated with secret redaction (`scripts/support_bundle.py`)
- [x] EULA / privacy placeholders (`docs/EULA.md`, `docs/PRIVACY.md`) — legal review pending
- [x] Backup / DR runbook (`docs/BACKUP.md`)
- [x] Architecture + workflows (`docs/ARCHITECTURE_AND_WORKFLOWS.md`)
- [x] Electron production CSP header (Stage B)
- [ ] Code signing / notarization (deferred Stage C)
- [ ] Secure auto-update channel (deferred Stage C)

## Telemetry

Optional product telemetry must be off by default. Enable only after explicit user consent via Settings key `telemetry_consent=true`. Voice HUD latency marks are local diagnostics, not external telemetry.

## Support bundle

Run `python scripts/support_bundle.py` to collect redacted diagnostics for support.
