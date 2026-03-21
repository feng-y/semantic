---
name: commit-semantic-generate
description: Generate semantic fields for a semantic case
deprecated: true
replacement: /commit-semantic --stage generate
---

> **DEPRECATED**: This skill is deprecated and will be removed in a future version.
> Use `/commit-semantic --stage generate` instead, which provides the same functionality in a unified interface.

# commit-semantic-generate

## Purpose

对单个 `semantic_case` 生成最终语义样本：

- `commit_log`
- `rules`
- `invariants`
- `issue_text`
- `development_type`
- `split_suggestion`

## 调用方式

在 Claude Code 对话框中直接调用，无需任何参数：

```
/commit-semantic-generate
```

默认读取 `data/semantic_case_inputs/`，即 collect 的输出目录。Claude 会自动处理所有待生成的 case，并在对话中汇报成功/失败数量及失败原因。

## Input

```yaml
case_id: ...
commit_id: ...
module: ...
files: []
diff_chunks: []
related_tests: []

bugfix_evidence:
  weak: []
  medium: []
  strong: []

split_hints:
  too_many_files: false
  too_many_diff_themes: false
  mixed_feature_and_bugfix: false
  unrelated_objects_detected: false
```

## Output

```yaml
case_id: ...
commit_id: ...
module: ...

commit_log: ...
issue_text: ...
development_type: ...

rules: []
invariants: []

split_suggestion:
  needs_split: false
  split_reasons: []
```

## Internal Structure

内部固定使用 3 个 prompt：

1. generate_commit_log
2. generate_rules_invariants
3. generate_issue_text

## Core Rules

### 1. commit_log

只表达"改了什么"，是代码修改主动作表达。

### 2. rules / invariants

必须是围绕当前修改对象的语义约束与保持项，不是通用开发规范。

### 3. issue_text

是主语义压缩句，必须短、单句、单主体。

### 4. development_type

只能是：

- feature
- bugfix
- refactor
- migration
- optimize

### 5. split_suggestion

是 issue_text 压缩溢出的结果，不是先验猜测。

### 6. bugfix 是组合证据判断

不得由单个代码模式直接下结论。

## Validation

### Required fields

- case_id
- commit_id
- module
- commit_log
- issue_text
- development_type
- rules
- invariants
- split_suggestion

### Consistency checks

- issue_text 前缀与 development_type 一致
- needs_split=false 时 split_reasons 为空
- commit_log 不得 requirement 化
- rules/invariants 不得退化为通用开发规范

## Non-goals

本 skill 不负责：

- git 扫描
- semantic_case 归并
- 最终导出

## Failure Handling

- YAML parse 失败：进入 invalid bucket
- development_type 非法：进入 invalid bucket
- issue_text 不合法：进入 invalid bucket
- rules/invariants 退化为通用开发规范：进入 invalid bucket

## Example

### commit_log

在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。

### rules

- legacy syntax compatibility must be preserved during repair

### invariants

- historical inputs remain parseable

### issue_text

bugfix：修复旧DSL写法边界检查
