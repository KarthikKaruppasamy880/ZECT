# ADR: Mentrix Delivery orchestration stays ForgeLoop (not LangGraph)

- **Status:** Accepted  
- **Date:** 2026-08-06  
- **Deciders:** ZECT Mentrix product spine  

## Context

Mentrix Delivery (`/mentrix`) is a ship FSM: Scout → Plan → confirm → batched Build → gates → approve → PR. Operators need a deterministic, auditable state machine with explicit human confirm gates — not an open-ended graph experiment on the ship path.

LangGraph is useful for some research/agent prototypes, but adopting it for Mentrix Delivery would replace a working ForgeLoop orchestrator without a clear win on gates, batch confirm, or Workspace handoff.

## Decision

1. **ForgeLoop remains** the Mentrix Delivery FSM.
2. **Do not** migrate Mentrix Delivery to LangGraph.
3. If Companion needs richer branching later: extend the **custom tool planner** (max-steps, confirm gates, allowlists) — still not LangGraph unless a future ADR reverses this.
4. Ask / Plan / Build remain prep forms; Developer Workspace remains the IDE. Ship happens only in Mentrix Delivery.

## Consequences

- Roadmap Later tracks (Companion depth, mobile bridge, Computer Mode) build on ForgeLoop + custom tool loops.
- Docs and UI must never claim LangGraph powers Mentrix Delivery.
- A future ADR is required before any LangGraph ship-path migration.
