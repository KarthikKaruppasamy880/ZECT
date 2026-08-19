# ZECT Desktop Control Acceptance (D1–D2)

**Date:** 2026-08-19  
**Branch:** `feat/desktop-present-control`  
**Stop:** human merge only.

## Verdict

**ZECT_DESKTOP_CONTROL_PARTIAL**. Capability is the existing Computer Mode allowlist + audit — not a new agent. Live PowerPoint COM / Zoom share remain **BLOCKED_EXTERNAL** when the app is not installed. Skip ≠ PASS.

| Check | Result |
|-------|--------|
| Allowlist includes PowerPoint / Zoom / browsers | **PASS** unit |
| Native file dialog `zect-select-file` | **PASS** code |
| PPTX read only via Desktop/Documents/Downloads allowlist | **PASS** unit (reject outside) |
| Open presentation / cancel / Computer Mode off | **REUSE** existing Electron handlers |
| Wrong-window / unallowlisted app | **REUSE** `allowlisted` reject |
| Live mission: PPTX → PowerPoint when installed | **PARTIAL** — operator / BLOCKED_EXTERNAL if missing |

No secret extraction. No unrestricted automation.
