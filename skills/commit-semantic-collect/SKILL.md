---
name: commit-semantic-collect
description: Extract semantic cases from git history
---

# commit-semantic-collect

## Purpose

从仓库历史 commit 中提取原始变更，构造细粒度 `change_group`，再归并为可独立成立的 `semantic_case`，并补充 bugfix 证据与 split hints。

## Input

- repo_path
- commit_range 或 commit_list
- 可选 path include/exclude
- 可选 author / time window

## Output

输出 `semantic_case` 输入数据：

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

## Core Rules

### 1. commit 不是 issue 单位

不要把一个 commit 直接映射为一个 issue_text。

### 2. 小改动块不是 issue 单位

不要把每个细粒度改动块直接映射为一个 issue_text。

### 3. semantic_case 才是最终单位

只有能够共同压缩为一个短的、单主体 issue_text 的改动包，才能成为一个 semantic_case。

### 4. 测试 / 配置 / 开关默认是附带属性

它们默认挂靠主改动动作，不单独形成主体。

### 5. change_group 规则

- 同对象优先归一组
- 主逻辑 + 测试归一组
- config / flag / wiring / registration 默认挂主组
- cleanup 默认挂主组
- 只有独立主动作才新开组

### 6. semantic_case 归并规则

若多个 change_group 能共同压缩成一个短的、单主体 issue_text，则合并；否则分开。

### 7. bugfix_evidence 是证据池，不是最终结论

这里只注入证据，不直接判定最终 development_type。

## Non-goals

本 skill 不负责：

- 生成 commit_log
- 生成 rules
- 生成 invariants
- 生成 issue_text
- 生成 development_type

## Failure Handling

- 无法抽取 diff 时，记录 invalid raw commit
- 无法稳定归并 semantic_case 时，保守拆开而不是强行合并
- split_hints 只做提示，不做最终 split 结论

## Example

### Input

一个 commit，同时修改：
- parser 主逻辑
- 对应回归测试

### Output

一个 semantic_case，而不是两个独立 issue 单元。
