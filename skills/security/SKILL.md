# Security (Mentrix Reviewer / Fixer)

## Must flag
- Hardcoded secrets, tokens, passwords
- SQL injection / command injection
- Unsafe `eval` / `pickle.loads` of untrusted input
- Missing auth on new API routes

## Mentrix Integrator
- Never post secrets to Slack
- Respect Rules Engine allowlists for Jira projects and Slack channels
