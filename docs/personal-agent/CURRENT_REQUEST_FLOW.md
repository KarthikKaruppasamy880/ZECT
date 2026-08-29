# Personal Agent — Current Request Flows (PA-0)

As-implemented flows today (not the target architecture).

---

## 1. Mentrix Delivery (typed upgrade / build)

```text
User (Mentrix.tsx)
  → POST /api/mentrix/runs
  → mentrix_worker.run_mentrix_in_background
  → forge_loop.orchestrator.run_mentrix (scout→plan→build→review→…)
  → gates / artifacts / optional approve + create PR
  → SSE / poll run status to UI
```

**Policy:** project-scoped auth; human Approve before PR.  
**Not used for:** Slack send, desktop click, calendar.

---

## 2. Companion typed chat

```text
User (MentrixCompanion)
  → POST /api/mentrix/companion/turn or /stream
  → companion.iter_companion_events
  → intent parse (regex + LLM planner)
  → MentrixOrchestrator (PA-1; MENTRIX_PA1_ORCHESTRATOR=0 → legacy)
       → PermissionService / ApprovalService
       → no_delete_policy + emergency_stop for mutating tools
       → _exec_tool (…)
       → structured verification stub + AuditService
  → assistant text (+ optional TTS via speak.ts / voice_clone)
```

Companion `start_delivery` creates a MentrixRun and enqueues `run_mentrix_in_background`
(same coding-engine slice path as POST `/api/mentrix/runs`).

---

## 3. Companion spoken (Realtime)

```text
User mic
  → mentrixRealtime.ts ↔ OpenAI Realtime (token from Mentrix API)
  → model proposes tools
  → confirmRealtimeTools → same companion/MCP tool path + broker
  → spoken response (Realtime audio and/or clone TTS)
```

**Risk:** tool path must not bypass ALWAYS_CONFIRM (currently shared confirm helpers).

---

## 4. Desktop / Computer Mode

```text
Companion tool computer_* / desktop_*
  → permission_broker (ALWAYS_CONFIRM for many)
  → response includes desktop action payload
  → frontend desktopBridge.applyDesktopToolOutput
  → Electron preload zectDesktop.mentrix.*
  → electron/main.js → computer.js (openApp, typeText, clickAt, …)
  → refuse DELETE_ACTIONS / blocked path fragments
  → optional computerAuditLog (local ring buffer)
```

Mobile path:

```text
MobileCompanion → desktop_bridge.enqueue → Electron poll/ack → computer.js
```

---

## 5. Browser tool

```text
Companion browser_* or MCP playwright
  → allowlist.host_allowed (default * is unsafe)
  → PlaywrightProvider / playwright_adapter.execute
  → navigate | snapshot | click | fill
  → return text/DOM snippet (verification optional)
```

---

## 6. Outbound Slack / email send

```text
Companion slack_send / email_send intent
  → outbound_drafts.create_outbound_draft (preview)
  → user confirms
  → adapter send (SMTP / Slack API)
  → return provider response (verification = API ack)
```

---

## 7. File organize (partial)

```text
API create_plan → in-memory plan
  → approve_plan → move/rename under allowlist
  → rollback_plan (best-effort)
```

Missing vs DesktopControl: SHA-256, durable manifest, Undo UX, collision policy productization.

---

## Gaps vs DesktopControl target

| Target step | Today |
|-------------|--------|
| Shared MentrixOrchestrator | **PA-1** companion path (Delivery ForgeLoop unchanged) |
| Capability-policy decision object | MentrixCommand + permission_broker |
| Structured verification | Stub on orchestrator results; desktop/browser deepen in PA-4/5 |
| Calendar | Missing (PA-2) |
| Audit one stream | API audit + Electron ring buffer (still split) |
| Browser allowlist | Curated default (not `*`); opt-in `*` |
