# ZECT Release Scope and Deferred Epics

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Acceptance:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md) — **RELEASE_READY**  
**Merge:** PR #128 → `develop` @ `f80fda4` (acceptance finalize `bdd0b35`)

## Shipped (P0–P3 consolidation)

- WorkItem + WorkItemEvent + ArtifactStore PLAN ownership  
- MentrixDeveloperService ASK/PLAN/AGENT + resume/checkpoints  
- ContextEngine provenance ContextPack  
- Project Intelligence live facets + Jira/Camunda ingest path  
- Fabric handoff + close-loop dry_run  
- Mentrix Coding Agent / ForgeLoop fail-closed native path  
- EvidenceVerifier gates on READY_TO_SHIP / DONE  
- Ultra Review 3-lane merger (no second LLM)  
- P2 sidebar / Work Items / PI / System Health / Context Used  
- Skills FS dual-read + **bidirectional** DB↔FS sync  
- SecurityScanner interface over Security Agent findings  
- Model readiness + local-AI matrix (`claim_fully_local: false`)  
- Desktop readiness surface (not advanced automation)  
- Core Playwright CI green  

## Explicit future epics only

Per acceptance — **do not** expand this list into new architecture phases in-docs:

1. **ZECT-native malware engine** — deep scanner / daemon rewrite beyond Security Agent findings adapter  
2. **Advanced Computer Mode** — desktop automation rewrite beyond existing Electron bridge + readiness  
3. **Deeper fully-local AI** — raise PARTIAL/CLOUD_ONLY surfaces (especially Ultra Review LLM + Embeddings) to verified local without claiming success until tested  

## Non-goals (still forbidden)

- Duplicate agents, context engines, memory systems, model gateways, or plan systems  
- Foreign bot branding / parallel coding or review engines  
- Claiming fully local AI (`claim_fully_local` remains false until proven)  
- Inventing P4/P5 consolidation phases as architecture debt cover  

## Test / acceptance pointer

Authoritative pass/fail tables live only in [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md). Architecture docs must not outrun that evidence.
