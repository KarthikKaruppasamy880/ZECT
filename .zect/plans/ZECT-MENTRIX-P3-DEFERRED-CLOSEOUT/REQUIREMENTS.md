# Mentrix P3 deferred closeout

## Goal
Close remaining deferred items after P0–P2 merge without inventing parallel engines.

## Scope
1. Playwright nav labels restored for Companion / Incident / Labs / Architecture
2. Skills FS → SkillDefinition sync (`POST /api/system/skills-fs/sync`)
3. SecurityScanner reads live SecurityFinding / SecurityIncident
4. Model readiness optimization hints
5. Desktop readiness over existing Electron / Computer Mode

## Out of scope
- Full Playwright suite green (classify remaining as PRE_EXISTING)
- Foreign AV / new coding / ask / review engines
- Full desktop automation rewrite
