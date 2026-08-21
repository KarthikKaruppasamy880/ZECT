# Runtime Discovery / Run App — acceptance

- Start app is **not** hardcoded `npm run dev` at clone root.
- Recipes from authorized roots: nested `package.json`, Python backends, ZOAS `zinnia-modern`.
- ZOAS expected:
  - full: `zinnia-modern` → `npm run start:all`
  - frontend: `zinnia-modern/frontend` → `npm run dev` (:3000)
  - backend: `zinnia-modern/backend` → uvicorn :8000
  - tests: `zinnia-modern/backend` → `pytest -q`
- User confirms before execute. No secrets stored. Postgres is **not** started by ZECT.
- `cd` still does not persist; recipes encode `cwdRel`.
- Nested pytest is used by Coding Agent `run_repo_tests`.
- Threat: `..` and shell metacharacters in discovered commands are rejected.
