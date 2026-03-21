# Commit Refinement Prompt

## Context

You are refining a git commit message into conventional commit format.

## Task

Analyze the original commit message and diff, then generate:
- **title**: Conventional commit title (type: short description)
- **body**: Detailed description of the change
- **commit_log**: Key changes as a list

## Types

- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- perf: Performance improvement
- docs: Documentation
- test: Tests
- chore: Maintenance

## Output Format

Return JSON:
```json
{
  "title": "feat: add user authentication",
  "body": "Detailed description...",
  "commit_log": ["line1", "line2"]
}
```
