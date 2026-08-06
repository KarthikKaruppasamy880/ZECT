# Backup and Disaster Recovery

## What to back up

| Path / store | Contents |
|---|---|
| Database (`zect.db` or Postgres URL) | Projects, memory, schedules, audit, secrets refs |
| `backend/data/` | Voice samples, lattice artifacts, local caches |
| Electron user data | Window state / local flags (optional) |
| `.env` (secure vault only) | Never commit; restore via Secrets Manager |

## Backup procedure

1. Stop write-heavy workers if possible.
2. Snapshot the database (file copy for SQLite; `pg_dump` for Postgres).
3. Archive `backend/data/` excluding temp caches if desired.
4. Store off-host with encryption at rest.

## Restore procedure

1. Restore database file / import dump.
2. Restore `backend/data/`.
3. Re-inject secrets via Secrets Manager (do not restore raw `.env` into git).
4. Start API + frontend; run smoke: login, Mentrix health, `/api/schedules`, `/api/memory/types`.

## RTO / RPO (targets)

Define organizational targets here before GA. Default engineering target: RPO ≤ 24h, RTO ≤ 4h for single-operator installs.
