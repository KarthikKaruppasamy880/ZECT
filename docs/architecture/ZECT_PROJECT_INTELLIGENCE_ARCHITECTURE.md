# ZECT Project Intelligence Architecture

## Target

Mentrix Project Intelligence = Lattice + Blueprint + Knowledge + Memory + Skills + Playbooks + Related Work + freshness.

## Current

| Layer | Storage | Consumers |
|-------|---------|-----------|
| Lattice | In-memory graph cache; structural blueprint in DB | Ask/Plan Lattice reload, Companion lattice_query, Coding Agent RAG |
| Blueprint | LatticeStructuralBlueprint + GeneratedOutput | ForgeLoop scout, Coding Agent snippet, /blueprint |
| Knowledge | Knowledge Base DB | Ask/Plan/Companion via retrieve_knowledge_for_context; not Ultra Review |
| Memory | TypedMemoryRecord + Lesson | Companion build_agent_context; not Ask/Plan directly |
| Skills | skill_definitions DB (not .zect/skills) | Context inject; script_body not auto-run |
| Playbooks | playbook_executor → Mentrix modes | Schedules; weak Coding Agent link |

## P0 ProjectIntelligenceService contract

```python
class ProjectIntelligenceSnapshot:
    lattice: dict          # status + optional hits
    blueprint: dict        # snippet + freshness
    knowledge: list        # curated truth (NEVER merge into memory)
    memory: list           # learned facts (separate key)
    related_work: list     # WorkItems / empty until history
    skill_selection: list  # may be [] until P1
    playbook_selection: list  # may be [] until P1
    freshness: dict        # per-source freshness flags
```

Knowledge and Memory remain semantically different stores.
