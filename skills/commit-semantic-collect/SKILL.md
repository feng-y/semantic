---
name: commit-semantic-collect
description: Extract semantic cases from git history
deprecated: true
replacement: /commit-extract --stage collect
---

> **DEPRECATED**: This skill is deprecated and will be removed in a future version.
> Use `/commit-extract --stage collect` instead, which provides the same functionality in a unified interface.

# commit-semantic-collect

## Purpose

从仓库历史 commit 中提取原始变更，构造细粒度 `change_group`，再归并为可独立成立的 `semantic_case`，并补充 bugfix 证据与 split hints。

## 调用方式

在 Claude Code 对话框中用自然语言描述范围，Claude 自动解析为参数并调用。

**示例：**
```
/commit-semantic-collect 最近 10 个 commit
/commit-semantic-collect 最近一个月的 commit
/commit-semantic-collect 2026-01-01 到 2026-03-01 的 commit
/commit-semantic-collect 张三提交的最近 50 个 commit
/commit-semantic-collect 最近 10 个 commit，增量模式
```

**自然语言 → 参数映射规则：**

| 用户描述 | 转换参数 |
|---------|---------|
| 最近 N 个 commit | `commit_range="HEAD~N..HEAD"` |
| 最近一周 / 一个月 / N 天 | `since="N days ago"` / `since="1 week ago"` / `since="1 month ago"` |
| YYYY-MM-DD 到 YYYY-MM-DD | `since="YYYY-MM-DD"`, `until="YYYY-MM-DD"` |
| 某人的 commit | `author="姓名"` |
| 增量模式 | `incremental=True` |
| 排除 X 目录 / 不分析 X 目录 / 忽略 X 目录 | `exclude_paths=["X/"]` |
| 排除 X 和 Y 目录 | `exclude_paths=["X/", "Y/"]` |

`repo_path` 默认为当前工作目录，无需用户指定。

**排除目录示例：**
```
/commit-semantic-collect 最近 10 个 commit，排除 config 目录
/commit-semantic-collect 最近一个月，不分析 deploy 和 infra 目录
/commit-semantic-collect 最近 50 个 commit，忽略 scripts、docs 目录
```

## Input

- repo_path（默认当前目录）
- commit_range 或 since/until 时间窗口
- 可选 author
- 可选 incremental

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
