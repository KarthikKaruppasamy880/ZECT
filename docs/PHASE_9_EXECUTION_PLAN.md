# Phase 9 Execution Plan — Security Monitoring & Incident Response

Companion to `Upgrade.md` Phase 9. **Previously ON HOLD — now unblocked.**

Mentrix coordinates security ops; detections come from adapters (not LLM malware inventing). Branding: ZECT-owned **Detection Provider / Endpoint Snapshot / Forensic Collection** surfaces only — vendor names only in adapter internals + `THIRD_PARTY_NOTICES.md`.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Detection spine: `SecurityFinding` persist, Detection Provider interface + audit adapter, scan API, fingerprints | **This PR** |
| B | IR packaging: draft incident → approval → Jira create → Slack allowlisted notify; harden ticket fields + redaction | **This PR** |
| C | External Detection Provider webhook (signature, immutable event, normalize, dedupe, rate limit) | **This PR** |
| D | Containment / enrichment / forensics stubs — **disabled by default**, never auto-execute | **This PR** |

## Non-goals (this PR)

- Automatic process kill / quarantine / network isolate / account disable
- LLM-generated arbitrary endpoint queries
- Uploading raw evidence to Slack
