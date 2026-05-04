# ZECT — Skill Template

## Template

Use this template when creating a new Skill for ZECT.

---

```markdown
# Skill: [Skill Name]

## Metadata
- **ID:** [unique-skill-id]
- **Version:** [1.0.0]
- **Category:** [analysis | blueprint | review | documentation | testing | refactoring | migration | analytics | workflow]
- **Type:** [markdown-only | code-backed | hybrid]
- **Trigger:** [manual | automated | scheduled | chained]
- **Status:** [draft | active | deprecated]

## Purpose

[One paragraph describing what this skill does and why it exists.]

## When to Use

- [Scenario 1 when this skill is appropriate]
- [Scenario 2]
- [Scenario 3]

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| [input_name] | [string/number/array/object] | [Yes/No] | [What this input is] |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| [output_name] | [string/number/array/object] | [What this output contains] |

## Steps

1. [Step 1 — what to do first]
2. [Step 2 — next action]
3. [Step 3 — continue until complete]
4. [Step N — final step]

## Constraints

- [Constraint 1 — what this skill must NOT do]
- [Constraint 2 — limits or boundaries]
- [Constraint 3 — safety rules]

## Dependencies

- [Other skills or services this depends on]
- [API keys or access required]

## Example

### Input
```json
{
  "input_name": "example_value"
}
```

### Output
```json
{
  "output_name": "example_result"
}
```

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| [Error type] | [What causes it] | [How to fix it] |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | YYYY-MM-DD | Initial release |
```

---

## Example: Code Review Skill

```markdown
# Skill: PR Code Review

## Metadata
- **ID:** code-review-pr
- **Version:** 1.0.0
- **Category:** review
- **Type:** code-backed
- **Trigger:** manual
- **Status:** active

## Purpose

Analyze a GitHub pull request using AI to identify bugs, security vulnerabilities, performance issues, and architectural problems. Generates a fix prompt that can be sent to any AI coding tool.

## When to Use

- Before merging a PR
- When reviewing complex changes
- For security-sensitive code changes
- When short on reviewer time

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| owner | string | Yes | GitHub repo owner |
| repo | string | Yes | Repository name |
| pr_number | integer | Yes | Pull request number |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| findings | array | List of issues found with severity |
| fix_prompt | string | Copy-paste prompt for AI coding tools |
| summary | string | Executive summary of review |

## Steps

1. Fetch PR metadata from GitHub (title, description, author)
2. Fetch PR diff (changed files and line-by-line changes)
3. Build context (file contents, dependencies)
4. Send to AI for analysis (system prompt + diff + context)
5. Parse AI response into structured findings
6. Generate fix prompt from findings
7. Log token usage
8. Return results to user

## Constraints

- Must NOT auto-merge or approve the PR
- Must NOT modify the code
- Must log all token usage
- Must work without OpenAI key (returns 503 gracefully)

## Dependencies

- GitHub API access (GITHUB_TOKEN)
- OpenAI API access (OPENAI_API_KEY)
- Token tracker service

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| 503 Service Unavailable | No API key configured | Show configuration instructions |
| 404 Not Found | Invalid repo/PR | Show error with correct format |
| 429 Rate Limited | Too many requests | Queue and retry with backoff |
```
