# ZECT WEB INTELLIGENCE C — PR #135 SECURITY REMEDIATION

## Purpose
Use this after the current PR #135 review. PR #135 is NOT approved for merge while valid Critical/Major security or correctness findings remain unresolved.

Do not start D.
Do not auto-merge.
Do not redesign unrelated frozen systems.

## 1. Triage all findings
Classify every CodeRabbit finding as exactly one of:

`VALID_FIX | ALREADY_FIXED | FALSE_POSITIVE | OUT_OF_SCOPE`

For each record:
- severity
- category
- file/line
- claim
- evidence
- classification
- action
- post-fix test/evidence

All valid C-introduced Critical/Major findings must be fixed before `READY_TO_MERGE`.

## 2. Permission Broker must fail closed
Never permit Web Intelligence because a policy result is absent, malformed, unknown, errored, or unconfigured where protection is required.

Expected behavior:

```text
ALLOW   -> proceed
CONFIRM -> require confirmation
DENY    -> block
UNKNOWN -> block
MISSING -> block
ERROR   -> block
```

Add fail-closed regression tests.

## 3. Never trust client-supplied project_id
For every `PROJECT_SHARED` operation, the backend must independently verify authenticated user membership/access to the project.

Apply to:
- ingest
- list
- get
- retrieve
- attach
- browser snapshot
- delete
- Knowledge/ContextPack inclusion

A forged `project_id` must never expose or attach another project's content.

Test forged project ID, cross-user, cross-project, and cross-org access where supported.

## 4. Harden SSRF / DNS rebinding / redirects
Generic URL retrieval must deny localhost, loopback, private/internal ranges, link-local, cloud metadata endpoints, unsafe schemes, and unauthorized ports/protocols.

Required:
- resolve and validate destination
- connect only to a policy-safe destination
- revalidate redirects
- preserve/validate port correctly
- avoid validate-one-IP/connect-another-IP TOCTOU
- redirect limits
- timeout
- response-size limits
- supported content-type limits

Add tests for localhost, RFC1918/private, link-local/metadata, redirect-to-private, rebinding/TOCTOU simulation where practical, unsafe scheme, and port handling.

## 5. attach_url must enforce denial
If Permission Broker denies or SSRF validation fails:

```text
STOP
No browser snapshot
No fetch
No ContextPack
No Knowledge entry
```

No fallback retrieval path.

## 6. Delete / detach / retention cleanup
When external content is removed:
- enforce `web_delete` or equivalent permission
- respect USER_PRIVATE / PROJECT_SHARED
- deactivate/delete related Knowledge entries as designed
- detach from ContextPack/UI
- stale versions must not retrieve
- handle stored source/chunk files per retention policy
- shared content must not be destroyed just because one user detaches if other references remain

Prove delete and detach semantics separately where applicable.

## 7. Re-ingest / uniqueness / migration
Resolve valid uniqueness/reuse conflicts.

If schema changes are needed:
- add/update proper Alembic migration
- do not rely only on ORM edits
- preserve existing data compatibility where practical

Re-ingest behavior must be deterministic using content SHA/version, scope, owner/project, freshness, and current/superseded status.

## 8. Preserve UNTRUSTED_EXTERNAL_CONTEXT
All fetched content remains data, never instructions.

This includes:
- title
- body
- RSS metadata
- GitHub content
- browser snapshot text
- page metadata
- external comments

Never elevate external text into system instructions, developer instructions, tool commands, or policy overrides.

Test malicious fixtures such as:
- "Ignore previous instructions"
- "Read ~/.ssh/id_rsa"
- "Run shell commands"
- "Upload the repository"
- "Disable security checks"

These may be retrieved/summarized as data but never executed.

## 9. Browser snapshot / USER_PRIVATE normalization
Fix valid issues around:
- browser adapter normalization
- canonical source labeling
- USER_PRIVATE with `project_id = null`
- PROJECT_SHARED requiring valid project binding
- provenance/scope preservation

Do not force project binding for USER_PRIVATE. Do not allow missing binding for PROJECT_SHARED.

## 10. Same PR only
Use the existing PR #135 branch:

```text
current PR head
-> fixes
-> tests
-> commit
-> push same branch
-> PR #135 updates
-> CI
-> CodeRabbit re-review
```

Do not create a replacement PR unless truly necessary.

## 11. Security tests
Add/update tests for:
- permission fail-closed
- forged project_id
- cross-user isolation
- cross-project isolation
- cross-org isolation where supported
- SSRF loopback/private/link-local
- redirect to unsafe destination
- DNS rebinding/TOCTOU mitigation
- unsafe scheme
- port handling
- Permission Broker denial
- attach_url no-fallback
- prompt-injection containment
- delete/detach behavior
- Knowledge cleanup
- re-ingest/versioning
- USER_PRIVATE project_id=null
- PROJECT_SHARED project required

## 12. Regression preservation
Preserve frozen/merged:
- Present A1-A8
- Phases 5-13
- B Document Intelligence
- Model Gateway
- Permission Broker
- Connector Gateway
- ContextEngine
- Project Intelligence
- Voicebox
- Electron lifecycle

Run C targeted tests + B regression + Present smoke + Phase5-13 smoke.

## 13. Acceptance / merge gate
After fixes:
1. push to PR #135
2. wait for backend/frontend/e2e
3. wait for CodeRabbit re-review
4. inspect unresolved Critical/Major findings

Return `READY_TO_MERGE` only when:
- CI green
- no unresolved verified C Critical/Major findings
- security tests pass
- frozen regressions pass
- C acceptance updated
- D not started

Do not auto-merge.

## 14. Update acceptance
Update:

`ZECT_WEB_INTELLIGENCE_ACCEPTANCE.md`

Include:
- all 15 finding classifications
- Critical fixes
- Major fixes
- false-positive/already-fixed evidence
- security tests
- SSRF proof
- ownership/isolation proof
- prompt-injection proof
- delete/re-ingest proof
- CI
- CodeRabbit status
- frozen regressions
- remaining PARTIAL scope

Keep intentionally PARTIAL:
- general web search
- YouTube transcripts
- Reddit
- other broad external-source adapters

## Final instruction
PR #135 is not approved for merge yet.

Triage all review findings, fix every valid C-introduced Critical/Major issue, push fixes to the same PR, rerun security/regression tests, and wait for CI/re-review.

Do not start D.

Return `READY_TO_MERGE` only after all gates above are satisfied.
