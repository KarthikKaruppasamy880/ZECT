# Personal Agent — Safety Policy (PA-0)

Normative product policy for Mentrix personal-agent work. Enforce in **server-side or trusted-process** code (backend, Electron main). UI hiding is not sufficient.

---

## READ (allowed with allowlists)

- Approved email mailboxes / digests  
- Approved Slack workspaces and channels  
- Approved calendar data (when CalendarProvider exists)  
- User-selected folders under FS allowlist  
- Approved visible applications / windows (Computer Mode allowlist)  
- Approved repository workspaces (`ZECT_WORKSPACE_ROOT` / Mentrix workspace)

Fetch **minimum** content needed for the task.

---

## DRAFT (no external side effects)

- Email / Slack replies  
- Meeting notes and summaries  
- File-organization proposals  
- Dictation: keep verbatim transcript separate from polished draft; show diff  

Drafts must cite sources and label assumptions / unresolved questions.

---

## WRITE WITH APPROVAL

Immediately before side effects:

- Send email  
- Send Slack messages  
- Create/update calendar events  
- Move/rename approved files  
- Type into approved applications  
- Browser fill/click on non-read-only flows  

Approvals need: destination, body/preview hash, expiry, actor, correlation id.

---

## NEVER ALLOW

Enforce with hard refuse (examples already present for desktop delete):

- File deletion; Trash emptying  
- Email deletion; Slack message deletion; calendar event deletion  
- Destructive shell / admin commands  
- Disabling security controls  
- Reading password stores; exposing secrets to renderer/browser  
- Unrestricted access to full home directory  
- Password scraping from pages  

Do not “delete original after failed move” as a workaround.

---

## Verification

Never claim success only because a key or click was sent. Prefer:

- Provider object ID (message id, issue key)  
- DOM / a11y read-back  
- Filesystem SHA-256 before/after  
- Active-window identity  
- Screenshot only when structured verification unavailable  

---

## Voice

- Spoken and typed commands use **identical** permissions  
- No silent continuous recording without explicit session consent  
- Voice must not bypass approval  
- Clone TTS stays local (ZECT Voicebox); no shipping weights in git  

---

## Secrets

- Resolve only in backend / Electron main vault  
- Never put raw secrets in React state, logs, or MCP client payloads beyond need-to-use  

---

## Emergency stop

- Global stop cancels interactive tools and scheduled executions  
- Desktop automation must honor stop (PA-1/PA-5 wire-up)  

---

## Priority of automation methods

Email/Slack/calendar: official API → MCP → browser DOM → a11y → key/mouse last.  
Browser: semantic locator → a11y → vision → key/mouse.  
Native desktop: native API → a11y → app adapter → vision → key/mouse.
