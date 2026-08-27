# Browser test skill

ZECT-owned procedure for the Coding Agent to prove a change works in a real
browser, not just in unit tests. Uses ZECT's own `BrowserTool` (Playwright
primary, Playwright MCP optional interop layer) — never a separate,
unaudited browser automation path.

## When to use

- After an edit that touches a running app's frontend/UI behavior.
- Whenever the mission goal or Debugger loop needs visual/DOM/console/network
  proof that a fix actually works end-to-end, not just that a unit test
  passes.

## Steps

1. Resolve run profile — `start_app` with no args to use the confirmed/
   discovered recipe for this repo (`.zect/run-profiles/profile.json`); pass
   `recipe_id` explicitly if the repo is ambiguous.
2. Start services — `start_app` (whole workspace) or target one service.
3. Health — `health_check` against the service's port before touching the
   browser; do not navigate a browser at a service that isn't listening yet.
4. Browser — `browser_navigate` to the page under test.
5. Snapshot — `browser_snapshot` for a DOM/accessibility read before acting,
   so the next assertion has a known starting state.
6. Journey — `browser_click` / `browser_type` / `browser_select` /
   `browser_wait_for` to drive the actual user flow being verified.
7. Evidence — `browser_assert_text` / `browser_assert_visible` for the
   expected outcome, plus `browser_console_errors` / `browser_network_failures`
   to catch silent breakage the assertion alone would miss.
8. Screenshot — `browser_screenshot` for a durable artifact; it is written
   under the workspace's `.zect/evidence/screenshots/`, never inlined raw
   into the tool result.
9. On failure — treat it as a structured failure (which step, which
   assertion, what evidence), hand off to the Debugger role: search
   source/logs, patch, rerun tests, `restart_app` (pass the affected
   service's `process_id` to restart just that one process, not the whole
   workspace), then repeat this journey from step 4.
10. Stop owned processes (`stop_app`) when the verification is done, unless
    the mission needs the service left running for the human to inspect.

## Notes

- Never scrape or fill password fields — the underlying adapter refuses this
  by contract; do not try to work around it.
- Browser actions respect `MENTRIX_BROWSER_ALLOWED_ORIGINS` when set — a
  navigate to a disallowed origin is blocked before it ever reaches the
  browser, same governance regardless of which provider (native Playwright
  or Playwright MCP) is configured.
