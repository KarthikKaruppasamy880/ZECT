# Personal Agent — Capability Matrix (updated after gap-close)

Status: `working` | `partial` | `placeholder` | `missing` | `unsafe`

| capability | status | notes |
|---|---|---|
| Mentrix Delivery | working | ForgeLoop unchanged — see [`CODING_READINESS.md`](./CODING_READINESS.md) for mock vs remote coding engine |
| Companion typed + orchestrator | working | PA-1 MentrixOrchestrator |
| Companion spoken / Realtime | working | Clone TTS when Voicebox online (higher latency) / PCM when offline; calendar/meeting + connector_architecture + coding_engine_status |
| Clone TTS / Voicebox | working | Native ZECT Voicebox; Present slide prefetch + ~500 char script cap |
| Electron Computer Mode | working | Allowlist includes Notepad++; FG wait before type; type max ~500; long notes via `desktop_write_note`; Zoom open/join only (no schedule); audit ingest |
| Desktop delete | working | Hard refuse |
| Mobile desktop bridge | partial→improved | Durable JSON spill; bridge flattens nested args |
| Browser automation | partial→improved | Password refuse; session contexts; DOM verify |
| Slack / email drafts | working | Hash + expiry + anti-dupe |
| Gmail list | partial→improved | Gmail API list when OAuth set; IMAP fallback |
| Calendar read/draft | working | `/api/calendar/*` + ICS/demo provider |
| File organize | working | Durable plans + UI `/file-organize` |
| Permissions / audit / emergency stop | working | Electron honors stop flag |
| Skills / schedules grants | working | Manifest + schedule grants |
| LiveKit | missing | Deferred |
| Notion | placeholder | Deferred |
| Zoom schedule meeting | missing | Open/join only — `capability_refuse` |
| Open any installed app | missing | Hard allowlist by design |

## Gap-close PR checklist

- [x] Calendar API
- [x] Gmail list_messages
- [x] File Organize UI
- [x] Desktop verify + emergency stop
- [x] Browser session isolation
- [x] Durable desktop bridge
- [x] Realtime TTS fallback
- [x] Blind coordinate click refuse
- [x] PA-5 desktop depth: foreground allowlist gate, bridge flatten, active target, estop sync, audit ingest
- [x] Notepad++ allowlist + long-note write path + Present prefetch + coding readiness doc
