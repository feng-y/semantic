---
name: commit-semantic-export
description: Export validated semantic cases to disk
deprecated: true
replacement: /commit-semantic --stage export
---

> **DEPRECATED**: This skill is deprecated and will be removed in a future version.
> Use `/commit-semantic --stage export` instead, which provides the same functionality in a unified interface.

# commit-semantic-export

## Purpose

将通过校验的 semantic case 落盘、汇总，并输出基础统计与 invalid bucket。

## 调用方式

在 Claude Code 对话框中直接调用，无需任何参数：

```
/commit-semantic-export
```

默认读取 `data/semantic_cases/`，即 generate 的输出目录。支持增量模式：

```
/commit-semantic-export 增量模式
```

Claude 会在对话中汇报导出统计，包括 case 总数、development_type 分布、invalid 数量及告警。

## Input

validated semantic cases:

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

## Output

- 单 case YAML 文件
- 汇总 JSONL
- 基础统计结果
- invalid bucket / error bucket

## Core Rules

### 1. 只导出已校验 case

export 只接收 validated semantic cases。

### 2. 不在 export 阶段改语义

不得在 export 阶段重新改写：

- commit_log
- issue_text
- rules
- invariants
- development_type

### 3. 提供基础统计

至少输出：

- 总 case 数
- validation pass rate
- development_type 分布
- bugfix 占比
- needs_split 占比
- invalid reason top-N

## Non-goals

本 skill 不负责：

- 语义生成
- case 修复
- prompt 调用

## Failure Handling

- 落盘失败：记录 error bucket
- JSONL 汇总失败：保留单文件 YAML，不阻断全部流程
- 统计失败：不影响已有 case 文件输出

## Example

### Outputs

- data/semantic_cases/*.yaml
- data/exports/cases.jsonl
- data/exports/summary.json
- data/invalid_cases/*.yaml
