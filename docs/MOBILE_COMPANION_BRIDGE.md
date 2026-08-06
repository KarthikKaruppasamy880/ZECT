# Mobile Companion + desktop bridge

Mobile is a **thin Companion client** (PWA/shell or `/m/companion`) talking to the same Mentrix API. Desktop work executes on the user’s **Electron agent**, not on the phone.

## Flow

```text
Mobile chat/voice  →  Mentrix API
Desktop action     →  POST /api/mentrix/companion/desktop-bridge/enqueue
Electron agent     →  heartbeat + poll + Computer Mode execute + ack
```

## Endpoints

| Method | Path | Role |
|---|---|---|
| GET | `/api/mentrix/companion/desktop-bridge/status` | Desktop online? |
| POST | `/api/mentrix/companion/desktop-bridge/heartbeat` | Electron keepalive |
| POST | `/api/mentrix/companion/desktop-bridge/enqueue` | Mobile queues command |
| GET | `/api/mentrix/companion/desktop-bridge/poll` | Electron pulls queue |
| POST | `/api/mentrix/companion/desktop-bridge/ack` | Electron completes |

Offline desktop → clear `desktop_offline` / 503 — no fake success.

## Non-goals

- Full unrestricted mobile OS control  
- Running Computer Mode on the phone  
