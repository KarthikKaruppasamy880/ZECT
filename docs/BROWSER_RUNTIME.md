# BrowserRuntime (Mentrix)

Mentrix browser automation goes through **BrowserRuntime**, with **Playwright** as the primary provider.

```text
Mentrix Companion / MCP  →  BrowserRuntime  →  PlaywrightProvider  →  playwright_adapter
```

## Operators

- MCP server id remains `playwright` internally; UI label is **Browser automation** (no third-party product branding).
- Health: `GET /api/mentrix/companion/integrations` → `browser`, `browser_hint`, `browser_provider`.
- Install: `pip install playwright && playwright install chromium`
- Optional env: `MENTRIX_BROWSER_PROVIDER=playwright` (default). `reasoning` / `reasoning_stub` is reserved for Later and stays offline.

## API surface (provider)

`status` · `navigate` · `snapshot` · `click` · `fill`

## Non-goals

- No Browser Use (or similar) dependency in this phase.
- Reasoning browser provider is a stub only until a Later ADR enables it.
