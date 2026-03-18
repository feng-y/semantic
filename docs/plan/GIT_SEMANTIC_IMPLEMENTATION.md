# Git Semantic Extraction - Implementation Summary

## 概述

这是一个从 git 历史中提取语义 case 的独立子系统，用于生成结构化的代码变更语义样本。

## 已实现的组件

### 核心模块 (src/)

- **types.py** - 数据结构定义（RawCommit, ChangeGroup, SemanticCaseInput, SemanticCaseOutput）
- **git_utils.py** - Git 操作工具（提取 commit 列表和详情）
- **grouping.py** - 变更分组逻辑（将文件变更分组为 ChangeGroup）
- **semantic_case_builder.py** - 语义 case 构建（将 ChangeGroup 归并为 SemanticCase）
- **prompt_runner.py** - Prompt 执行器（调用 Claude API 的接口，待实现）
- **validators.py** - 校验逻辑（结构、类型、枚举、一致性校验）
- **io_utils.py** - IO 工具（YAML/JSON/JSONL 读写）

### Prompt 模板 (prompts/)

- **generate_commit_log.md** - 生成 commit_log 的 prompt
- **generate_rules_invariants.md** - 生成 rules/invariants 的 prompt
- **generate_issue_text.md** - 生成 issue_text/development_type/split_suggestion 的 prompt

### Skills (skills/)

- **collect_cases/** - 从 git 历史收集 semantic case 输入
  - SKILL.md - 技能定义
  - run.py - 可执行脚本

- **generate_case_semantics/** - 生成语义字段
  - SKILL.md - 技能定义
  - run.py - 可执行脚本

- **export_cases/** - 导出和统计
  - SKILL.md - 技能定义
  - run.py - 可执行脚本

### 数据目录 (data/)

```
data/
├── raw_commits/           # 原始 commit 数据
├── grouped_changes/       # 分组后的变更
├── semantic_case_inputs/  # semantic case 输入
├── semantic_cases/        # 验证通过的 semantic case
├── invalid_cases/         # 验证失败的 case
└── exports/              # 导出的 JSONL 和统计
```

## 工作流程

```
Git History
    ↓
collect_cases (提取 + 分组 + 归并)
    ↓
semantic_case_inputs/*.yaml
    ↓
generate_case_semantics (调用 3 个 prompt)
    ↓
semantic_cases/*.yaml (valid) + invalid_cases/*.yaml
    ↓
export_cases (JSONL + 统计)
    ↓
exports/cases.jsonl + exports/summary.json
```

## 待完成的工作

### 关键任务

1. **Claude API 集成** - 在 `src/prompt_runner.py` 中实现 `run_prompt_with_claude` 函数
   - 需要调用 Claude API
   - 解析 YAML 响应
   - 错误处理

### 可选增强

- 更智能的文件分组逻辑
- 更精确的 bugfix 证据检测
- 并行处理支持
- 增量处理支持

## 使用示例

```bash
# 1. 收集 semantic cases
python skills/collect_cases/run.py /path/to/repo \
  --commit-range HEAD~10..HEAD

# 2. 生成语义字段（需要先实现 Claude API 集成）
python skills/generate_case_semantics/run.py

# 3. 导出结果
python skills/export_cases/run.py
```

## 与 semantic-harness 的关系

这是一个独立的子功能，不影响现有的 semantic-harness 系统：

- 使用独立的 `data/` 目录
- 使用独立的 skills（collect_cases, generate_case_semantics, export_cases）
- 使用独立的 prompts（generate_commit_log, generate_rules_invariants, generate_issue_text）
- 不修改现有的 semantic-* skills 和 pipelines

## 文档位置

- 详细规范：`docs/plan/git-sematic-readme.md`
- Prompt 规范：`docs/plan/git-semantic-skill.md`
- 本文档：`docs/plan/GIT_SEMANTIC_IMPLEMENTATION.md`
