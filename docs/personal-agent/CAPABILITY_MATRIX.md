# Personal Agent — Capability Matrix (updated after gap-close)

Status: `working` | `partial` | `placeholder` | `missing` | `unsafe`

| capability | status | notes |
|---|---|---|
| Mentrix Delivery | working | ForgeLoop unchanged |
| Companion typed + orchestrator | working | PA-1 MentrixOrchestrator |
| Companion spoken / Realtime | working | Orchestrator + TTS `require_clone=false` fallback; calendar/meeting + connector_architecture tools |
| Clone TTS / Voicebox | working | Native ZECT Voicebox; profile re-provision |
| Electron Computer Mode | working | Allowlist gate on click/type; honest verify; active-target chip; emergency-stop Electron sync; audit ingest |
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
