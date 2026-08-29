# ZECT Project Intelligence Flow

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)

## Owner

`ProjectIntelligenceService` — `backend/app/services/work_items/project_intelligence.py`

API: `GET /api/mentrix/developer/project-intelligence`  
UI: `/project-intelligence`

## Snapshot contract (shipped)

`snapshot()` returns distinct facets (Knowledge ≠ Memory):

| Facet | Role |
|-------|------|
| Lattice | Graph / ingest connectivity |
| Blueprint | Spec / enhance path |
| Knowledge | KB retrieval |
| Memory | Memory system (separate) |
| Skills | DB `SkillDefinition` + FS dual-read |
| Playbooks | Playbook selection / availability |
| Related work | Related WorkItems / context |
| Freshness | Staleness signals for Context Used |

## Skills DB ↔ filesystem (bidirectional)

**Execution SoT:** `SkillDefinition` (DB)  
**Portable packs:** `.zect/skills/<name>/SKILL.md` (primary write root)

Service: `backend/app/services/skills_fs.py`

| Direction | Function | HTTP |
|-----------|----------|------|
| FS → DB | `sync_filesystem_skills_to_db` | `POST /api/system/skills-fs/sync` `{direction:"fs_to_db"}` |
| DB → FS | `sync_db_skills_to_filesystem` | `{direction:"db_to_fs"}` |
| Both | `sync_skills_bidirectional` | default `{direction:"bidirectional"}` |
| List | `list_filesystem_skills` | `GET /api/system/skills-fs` |

Conflict policy: **local** DB provenance wins over FS import; then active DB skills export to primary FS root.

Acceptance: FS→DB / DB→FS / bidirectional **PASS**.

## Related Lattice / Blueprint APIs

- Lattice: `/api/lattice/*` (ingest, graph, query, RAG, blueprint)  
- Blueprint enhance: llm_phase / Agent Workspace Blueprint page  

PI does **not** invent a second Lattice or Memory engine; it composes existing stores.
