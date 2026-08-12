C plan approved with one mandatory addition: implement SSRF/network-boundary protection for all generic URL/browser retrieval. Deny localhost, loopback, link-local, private/internal network destinations, unsafe schemes and cloud metadata endpoints unless an explicitly trusted existing connector is authorized for that resource. Revalidate redirects/resolved destinations and enforce response-size, timeout and content-type limits.

Then execute C only on `feat/zect-web-intelligence-c` according to the reconciled plan.

Preserve:
- B Document Intelligence as MERGED/FROZEN
- Present A1–A8
- Phases 5–13
- existing Connector Gateway
- Permission Broker
- ContextEngine
- Model Gateway

All external content must remain `UNTRUSTED_EXTERNAL_CONTEXT`; webpage/RSS/GitHub content is data, never system/tool instructions.

Use existing ZECT scopes and provenance/versioning patterns. `PROJECT_SHARED` web intelligence must require project binding and authorization. USER_PRIVATE content must remain owner-isolated.

Prove prompt-injection containment with malicious external-content fixtures such as instructions to ignore policy, read secrets, access filesystem, execute commands, or exfiltrate repository content. These strings may be retrieved as data but must never become executable instructions.

Implement the approved MVP:
- approved URL retrieval
- RSS/Atom
- GitHub through existing supported connector/API path
- allowlisted browser snapshot with required confirmation
- ExternalContent artifacts/models
- provenance/freshness
- Knowledge/ContextEngine integration
- Attach URL in the shared AttachedContextPanel
- bounded ContextPack retrieval

Keep general web search, YouTube transcripts, Reddit and other broad-source adapters honestly PARTIAL unless already production-ready.

Run C tests plus all frozen regression smoke.

Produce `ZECT_WEB_INTELLIGENCE_ACCEPTANCE.md`.

STOP after C. Do not start D automatically.