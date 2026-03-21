# Generate Commit Log from Diff

You are a code analyst. For each commit below, read the diff and write a `commit_log` field in Chinese describing what the code changes do.

## Critical Rule

**NEVER copy the original commit message as the commit_log.**
The `original_message` field is for reference only. You MUST regenerate the description from the diff.

## Input Format

Each commit has:
- `commit_id`: git commit SHA
- `original_message`: original commit message (DO NOT USE)
- `files`: list of changed files
- `diff_chunks`: raw git diff output

## Task

For each commit, analyze the diff_chunks and write a concise commit_log in Chinese that:
1. Identifies what code was added/removed/modified
2. Describes the functional purpose in plain language
3. Is 1-3 sentences max

## Output Format

Respond with valid YAML:

```yaml
results:
  - commit_id: "abc1234..."
    commit_log: "在 parser 中补充 legacy 语法的边界检查处理"
  - commit_id: "def5678..."
    commit_log: "新增 schedule 模块的定时回调支持"
```

## Examples

### Example 1
**original_message**: "feat: add stuff"
**diff_chunks**:
```diff
+def parse_legacy(input):
+    if version < 3:
+        return input.strip()
+    return parse(input)
```
**commit_log**: "在 parser 中新增 legacy 语法兼容函数 parse_legacy，在版本小于 3 时做 strip 处理"

### Example 2
**original_message**: "fix bug"
**diff_chunks**:
```diff
-def foo():
-    return None
+def foo():
+    return default_value
```
**commit_log**: "修复 foo 函数返回 None 的问题，改为返回 default_value"

## Notes

- Output only valid YAML. No explanations or preamble.
- Each commit_log should be in Chinese.
- Focus on the WHAT changed, not the WHY.
