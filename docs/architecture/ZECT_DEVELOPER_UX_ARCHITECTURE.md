# ZECT Developer UX Architecture

## Current sidebar (internals exposed)

Workflow: Companion, Agent Workspace (/ask), Mentrix Delivery, Fabric, Security Agent
Workspace: Dashboard, Projects, Repo Workspace, Developer Workspace
Understand: Lattice, Blueprint, Docs
Deliver: Orchestration (+ Agent Mode)
Quality: Ultra Review, Rules, Sandbox, CI, Git Ops
Enterprise / Labs: Integrations, Skills, Playbooks, KB, Schedules, â€¦

## Target (prompt) â€” P2 nav

MENTRIX (Home, Developer) Â· WORK (Projects, Work Items, Processes) Â· INTELLIGENCE Â· DELIVERY Â· SECURITY Â· OPERATIONS Â· SETTINGS

## P0 UX scope

- MentrixDeveloperService + API for ASK/PLAN/AGENT entry.
- Companion routing tools to MentrixDeveloperService.
- **Do not** redesign sidebar in P0 (P2).
- Developer Workspace keeps Coding Agent panel; Ask/Plan pages may dual-call service later.

## Mentrix Developer ideal layout (future)

LEFT files/search/SCM Â· CENTER editor Â· RIGHT Mentrix ASK/PLAN/AGENT + Context Used Â· BOTTOM terminal/tests/diff/events
