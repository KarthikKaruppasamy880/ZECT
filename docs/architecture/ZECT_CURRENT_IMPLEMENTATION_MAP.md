# ZECT Current Implementation Map

| Capability | Implementation | File/Module | API | UI | Current Role | Duplicate? | Decision |
|---|---|---|---|---|---|---|---|
| Ask | LLM ask | domains/agent_run/llm.py | POST /api/llm/ask | /ask, Workspace inline | Read Q&A | Soft | KEEP+MERGE UX |
| Ask ForgeLoop | run_ask | services/phases/llm_phase.py | Mentrix stage | Delivery | Upgrade | Dual OpenAI path | ADAPT→gateway |
| Plan standalone | LLM plan | llm.py | POST /api/llm/plan | /plan | Ephemeral | vs MentrixRun | MERGE→ArtifactStore |
| Plan Delivery | result_json.plan | mentrix.py | /api/mentrix/runs/*/plan | /mentrix | Durable today | Compat | ADAPT dual-write |
| Build | build APIs | build_phase*.py | /api/build/* | /build | Codegen | vs Coding Agent | ADAPT→native |
| Coding Agent | mentrix_native | coding_engine_mentrix.py | /api/coding-agent/* | Workspace | Real executor | — | KEEP |
| ForgeLoop | MODE_PIPELINE | forge_loop/orchestrator.py | /api/mentrix/* | /mentrix | SDLC | — | KEEP |
| Fabric | surfaces/classify/run | domains/fabric/ | /api/fabric/* | /fabric | Multi-surface | Manual | KEEP |
| Assistant | tool loop | assistant_phase.py | mode=assistant | Delivery | Orchestrate | ≠ Coding Agent | KEEP |
| Ultra Review | review_service | review_service.py | /api/review* | /code-review | Quality | Many entrypoints | KEEP engine |
| Lattice | indexer cache | services/lattice/ | /api/lattice/* | /lattice | Graph | Ephemeral | ADAPT P1 |
| Blueprint | structural+LLM | lattice + llm_phase | lattice + enhance | /blueprint | Architecture | Multi gen | MERGE P1 |
| Knowledge | KB retrieve | knowledge_base.py | /api/knowledge* | Labs | Truth | — | KEEP |
| Memory | TypedMemory/Lesson | personal_agent/memory.py | /api/memory* | /memory | Learned | — | KEEP |
| Skills | DB SkillDefinition | skills_engine.py | /api/skills-engine/* | Labs | Procedures | — | ADAPT P1 |
| Playbooks | executor | playbook_executor.py | playbooks API | Labs | Multi-step | Weak CA | ADAPT P1 |
| Jira | adapters | jira routers | /api/jira/* | Integrations | Tickets | No WorkItem | ADAPT P1 |
| Camunda | process API | camunda_client, process/ | /api/process/* | Integrations | BPM | No WorkItem | ADAPT P1 |
| Security | Security Agent | detection_malware | /api/security/* | Security | Scan/IR | — | KEEP |
| Companion | companion+realtime | companion.py, realtime.py | companion APIs | /mentrix-home | Personal | Parallel Ask | KEEP front door |
| WorkItem | — | — | — | — | — | — | MISSING→P0 |
| MentrixDeveloperService | — | — | — | — | — | — | MISSING→P0 |
| ContextEngine | ad-hoc | agent_context, companion | scattered | — | — | — | MISSING→P0 |
| ArtifactStore | — | — | — | — | — | — | MISSING→P0 |
| EvidenceVerifier | — | — | — | — | — | — | MISSING→P0 |
