# ZECT Security Scan

Local malware-scan daemon used by **ZECT Security Agent**.

## Start

```powershell
.\scripts\up.ps1
```

Configure backend:

```env
ZECT_MALWARE_SCAN_HOST=127.0.0.1
ZECT_MALWARE_SCAN_PORT=3310
ZECT_MALWARE_SCAN_WRITES=1
```

Operator status: `GET /api/security/malware/status` — provider `zect_security_agent`.

License attribution for the underlying open-source scan engine is listed only in the repo root `THIRD_PARTY_NOTICES.md`.
