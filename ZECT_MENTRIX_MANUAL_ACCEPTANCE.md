# Mentrix Companion — manual / headed acceptance

Use Electron + `./zect.ps1 restart`. Voicebox only if clone Present is in scope.

| Check | Pass if |
|---|---|
| Active project / repo | Companion HUD shows the authorized clone, not a guessed path |
| Lattice provenance | A question about the repo cites indexed files or STALE + re-index, never fabricated files |
| WorkItem → Developer | Opening a WorkItem lands in `/workspace` with the same id |
| Coding progress | Mission phase/tests appear in Developer; Companion does not edit |
| Present handoff | Deck path / prompt can open Present; Present All waits for full audio |
| No duplicate Delivery | Prepare PR twice for the same WorkItem+mission returns duplicate_delivery_run / 409 |

Do not claim 100%. Record BLOCKED_EXTERNAL if Jira/Camunda/Voicebox/Presenton is down.
