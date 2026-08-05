# ZECT Commercial Release Notes (Phase 11 Stage A)

Placeholders for packaging, licensing, and operational readiness. **Phase 9 security monitoring remains ON HOLD.**

## Branding

Third-party engines (coding runtimes, editors, browser automation libraries, voice providers) run behind ZECT-owned adapters. Product UI, routes, and public APIs must not brand those vendors. Legal attribution lives in `THIRD_PARTY_NOTICES.md`.

## Self-host vs paid APIs

| Capability | Self-host option | Paid API option |
|---|---|---|
| LLM / Mentrix | Local model endpoint via env | Cloud LLM keys in Secrets Manager |
| Voice TTS | Local clone engine when configured | Cloud TTS fallback when key present |
| Browser automation | Local Chromium via Mentrix browser adapter | — |
| Coding engine | Mock / local sandbox | Optional remote Agent Server |

## Release checklist (gates)

- [ ] Dependency / license scan reflected in `THIRD_PARTY_NOTICES.md`
- [ ] Sample credentials removed from shipped configs
- [ ] Electron `appId` stable (`com.zinnia.zect`)
- [ ] Support bundle generated with secret redaction (`scripts/support_bundle.py`)
- [ ] EULA / privacy placeholders reviewed by legal
- [ ] Code signing / notarization (deferred Stage B)
- [ ] Secure auto-update channel (deferred Stage B)

## EULA / Privacy (placeholder)

ZECT is provided for authorized organizational use. Do not process regulated personal data without a documented DPA. Telemetry, if enabled later, requires explicit consent and redaction of secrets.

## Disaster recovery (placeholder)

Backup SQLite/Postgres data directories and `backend/data/` voice/artifact stores. Restore via documented ops runbook (to be expanded).

## Support bundle

Run `python scripts/support_bundle.py` to collect redacted diagnostics for support.
