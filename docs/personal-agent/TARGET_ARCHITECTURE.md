# Personal Agent — Target Architecture (PA-0)

Target interfaces from DesktopControl (normalize existing code behind these; do not big-bang rewrite).

```text
MentrixOrchestrator
VoiceRuntime
DesktopAutomationRuntime
BrowserAutomationRuntime
FileOrganizationRuntime
EmailProvider / SlackProvider / CalendarProvider
PermissionService / ApprovalService / AuditService
```

---

## 1. Typed command flow

```mermaid
flowchart TD
  User[User_typed_input] --> Norm[Normalize_text]
  Norm --> Orch[MentrixOrchestrator]
  Orch --> Ctx[Context_retrieval]
  Ctx --> Intent[Intent_and_params]
  Intent --> Cap[Capability_policy]
  Cap -->|deny| AuditDeny[AuditService]
  Cap -->|needs_approval| Appr[ApprovalService]
  Appr -->|approved| Exec[Runtime_or_Provider]
  Cap -->|allow| Exec
  Exec --> Verify[Structured_verification]
  Verify --> Audit[AuditService]
  Audit --> UI[Visual_result]
```

---

## 2. Voice command flow

```mermaid
flowchart TD
  Mic[User_speech] --> STT[VoiceRuntime_STT]
  STT --> Norm[Normalize_transcript]
  Norm --> Orch[MentrixOrchestrator]
  Orch --> Cap[Capability_policy]
  Cap -->|needs_approval| Appr[ApprovalService]
  Appr --> Exec[Runtime_or_Provider]
  Cap -->|allow| Exec
  Exec --> Verify[Verify]
  Verify --> TTS[VoiceRuntime_TTS_clone]
  TTS --> Speak[Playback]
  Verify --> Audit[AuditService]
```

Spoken and typed commands **must** share MentrixOrchestrator + policy (PA-1, PA-7).

---

## 3. Email / Slack draft-and-send flow

```mermaid
flowchart TD
  Req[Read_thread] --> Draft[Draft_reply]
  Draft --> Preview[Immutable_approval_preview]
  Preview --> Appr[ApprovalService]
  Appr -->|expired_or_mismatch| Reject[Reject]
  Appr -->|approved| Send[Provider_send]
  Send --> Verify[Provider_message_ID]
  Verify --> Audit[AuditService]
```

No auto-send. Never delete/archive as spam without future explicit policy.

---

## 4. Desktop action flow

```mermaid
flowchart TD
  Cmd[Desktop_intent] --> Orch[MentrixOrchestrator]
  Orch --> Cap[App_window_allowlist]
  Cap --> Appr[Approval_if_required]
  Appr --> Desk[DesktopAutomationRuntime]
  Desk --> Prefer[A11y_or_native_API]
  Prefer -->|fallback| Keys[Keyboard_mouse]
  Desk --> Verify[Active_window_DOM_or_a11y_state]
  Verify --> Audit[AuditService]
  Desk -->|delete| Block[Hard_refuse]
```

Trusted process: Electron main (or future dedicated agent host) — not renderer.

---

## 5. File-organization and Undo flow

```mermaid
flowchart TD
  Scan[Scan_allowlisted_folders] --> Classify[Classify]
  Classify --> Proposal[Proposal_UI]
  Proposal --> Appr[ApprovalService]
  Appr --> Move[Move_or_rename]
  Move --> Hash[SHA256_before_after]
  Hash --> Manifest[Rollback_manifest]
  Manifest --> Undo[Undo_offer]
  Move -->|collision| Stop[Block_overwrite]
  Move -->|delete_requested| Refuse[Never_delete]
```

---

## 6. Permission and approval flow

```mermaid
flowchart TD
  Req[Requested_capability] --> PS[PermissionService]
  PS -->|deny| Audit1[Audit]
  PS -->|grant_or_rule_allow| Risk[Risk_class]
  Risk -->|high| AS[ApprovalService]
  Risk -->|low| Exec[Execute]
  AS -->|preview_hash_ok| Exec
  AS -->|timeout| Expire[Expire]
  Exec --> VS[Verification_status]
  VS --> Audit2[AuditService]
  Stop[Emergency_stop] --> PS
  Stop --> Cancel[Cancel_active_runs]
```

---

## Mapping from today → target

| Target | Current seed |
|--------|----------------|
| MentrixOrchestrator | `companion.py` + ForgeLoop (keep Delivery separate initially) |
| PermissionService | `domains/permissions` + `permission_broker.py` |
| ApprovalService | broker ALWAYS_CONFIRM + outbound_drafts + permissions approve |
| AuditService | `audit_trail.py` (+ fold Electron computerAuditLog) |
| DesktopAutomationRuntime | `electron/computer.js` |
| BrowserAutomationRuntime | `services/browser/runtime.py` |
| FileOrganizationRuntime | `file_organize.py` |
| VoiceRuntime | `realtime.py` + `voice_clone` + Voicebox |
| CalendarProvider | **new** (PA-2) |
