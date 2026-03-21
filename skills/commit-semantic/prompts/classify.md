# Classify Commit Unit

Classify a commit unit as **functional** or **non-functional**.

## Input Fields

- `commit_log`: The LLM-regenerated commit log (Chinese summary of what changed)
- `module`: The detected module (parser, server, db, etc.)
- `files`: Files changed in this commit
- `timestamp`: Commit timestamp

## Classification Rules

**functional** if the commit log describes:
- `feat` prefix: new feature or capability
- `bugfix` prefix: bug fix
- `optimize` prefix: performance improvement
- Any commit with `+` in prefix indicating multiple types

**non-functional** if the commit describes:
- `refactor`: code restructuring without behavior change
- `test`: adding or updating tests
- `config`: configuration, CI/CD, dependency updates
- `chore`/`cleanup`: housekeeping, dead code removal
- `docs`: documentation only
- Any commit where the description focuses on code quality over behavior

## Output Format

```yaml
classification: functional | non-functional
reason: One sentence explaining the classification
```

## Examples

```
Input:  commit_log: "在 parser 中新增 AST 解析函数"
Output:
  classification: functional
  reason: "Describes a new capability (new AST parsing function)"

Input:  commit_log: "重构 parser 代码结构"
Output:
  classification: non-functional
  reason: "Describes code restructuring without behavior change"
```
