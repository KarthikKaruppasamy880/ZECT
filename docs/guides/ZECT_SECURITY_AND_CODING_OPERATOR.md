## Coding (no mock in product)

```env
ZECT_CODING_ENGINE=mentrix_native
```

## Mentrix Fabric

UI `/fabric` · API `/api/fabric/*` — classify → refuse → Coding Agent slices.
Companion: `fabric_classify`, `fabric_run`.

## Mentrix Process

```env
ZECT_CAMUNDA_BASE_URL=http://127.0.0.1:8080/engine-rest
ZECT_CAMUNDA_USER=
ZECT_CAMUNDA_PASSWORD=
ZECT_CAMUNDA_COCKPIT_URL=http://127.0.0.1:8080/camunda/app/cockpit/
```

Status: `GET /api/process/status`. Deploy / start / incidents via API or Companion.

## ZECT Security Agent

```powershell
services\zect-security-scan\scripts\up.ps1
```

Chain: Fabric classify → Coding Agent → optional Mentrix Process deploy/start.
