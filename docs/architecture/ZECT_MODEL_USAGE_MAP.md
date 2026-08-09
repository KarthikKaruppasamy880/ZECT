# ZECT Model Usage Map

Fallback policy env: `ZECT_MODEL_FALLBACK_POLICY=never|ask|automatic` (P0).
`never` must not send ContextPack / repo context to cloud.

| Feature | File | Provider | Model | Local? | Cloud? | Fallback? | Verified? |
|---|---|---|---|---|---|---|---|
| ASK API | domains/agent_run/llm.py | openai_compat | mentrix_llm_chat_model / OpenAI | Yes if gateway | Yes | Policy | PARTIALâ†’P0 |
| ASK ForgeLoop | services/phases/llm_phase.py | OpenAI SDK (pre-P0) | env | No | Yes | â€” | P0 unify |
| PLAN API | llm.py | openai_compat | same | Yes | Yes | Policy | PARTIALâ†’P0 |
| PLAN ForgeLoop | llm_phase.py | OpenAI (pre-P0) | â€” | No | Yes | â€” | P0 unify |
| Companion | companion.py | openai_compat | mentrix_llm_chat_model | Yes | Yes | Policy | PARTIALâ†’P0 |
| Coding Agent | coding_engine_mentrix.py | openai_compat | â€” | Yes | Yes | Policy | PARTIALâ†’P0 |
| ForgeLoop Build | build_phase_svc.py | Anthropic/OpenAI or Coding Agent | resolve_generation_model | Limited | Yes | Fail-closed native | P0 |
| Ultra Review | review_service.py + response_cache | OpenAI-class | â€” | Unlikely | Yes | cache | PARTIAL |
| Blueprint enhance | llm_phase / llm | OpenAI | â€” | Mixed | Yes | â€” | PARTIAL |
| Realtime | realtime.py | OpenAI Realtime | MENTRIX_REALTIME_MODEL | No | Yes | â€” | PARTIAL |
| Voice | voice_clone / Voicebox | local + OpenAI TTS | â€” | Yes | Yes | stock TTS | PARTIAL |
| Embeddings | build_intel/embeddings.py | OpenAI embeddings | â€” | No | Yes | â€” | PARTIAL |

Telemetry (P0): requested/actual provider+model, fallback_used, fallback_reason, latency_ms, work_item_id, agent_run_id, operation_id.
