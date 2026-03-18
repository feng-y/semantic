# Commit Semantic Extraction - Implementation Summary

## 概述

commit-semantic 是 semantic-harness 的一个子功能，用于从 git 历史中提取语义化的代码变更样本。

## 目录结构

```
semantic-harness/
├── src/
│   ├── commit_semantic/              # commit-semantic 子模块
│   │   ├── __init__.py
│   │   ├── git_utils.py              # Git 操作
│   │   ├── grouping.py               # 变更分组
│   │   ├── semantic_case_builder.py  # 语义 case 构建
│   │   └── prompt_runner.py          # Prompt 执行器
│   ├── types.py                      # 共享数据结构
│   ├── validators.py                 # 共享校验逻辑
│   └── io_utils.py                   # 共享 IO 工具
│
├── prompts/
│   └── commit-semantic/              # commit-semantic prompts
│       ├── generate_commit_log.md
│       ├── generate_rules_invariants.md
│       └── generate_issue_text.md
│
├── skills/
│   ├── commit-semantic-collect/      # 收集 semantic cases
│   │   ├── SKILL.md
│   │   └── run.py
│   ├── commit-semantic-generate/     # 生成语义字段
│   │   ├── SKILL.md
│   │   └── run.py
│   └── commit-semantic-export/       # 导出和统计
│       ├── SKILL.md
│       └── run.py
│
└── data/                             # 数据目录（运行时生成）
    ├── semantic_case_inputs/
    ├── semantic_cases/
    ├── invalid_cases/
    └── exports/
```

## 命名规范

遵循 semantic-harness 的命名风格：

- **Skills**: `commit-semantic-{action}` (使用连字符)
- **模块**: `src/commit_semantic/` (使用下划线)
- **Prompts**: `prompts/commit-semantic/`

## 三个 Skills

### 1. commit-semantic-collect

从 git 历史提取 semantic case 输入。

```bash
python skills/commit-semantic-collect/run.py /path/to/repo \
  --commit-range HEAD~10..HEAD
```

### 2. commit-semantic-generate

使用 Claude prompts 生成语义字段。

```bash
python skills/commit-semantic-generate/run.py
```

**注意**: 需要实现 `src/commit_semantic/prompt_runner.py` 中的 Claude API 集成。

### 3. commit-semantic-export

导出 JSONL 和统计信息。

```bash
python skills/commit-semantic-export/run.py
```

## 数据流

```
Git History
    ↓
commit-semantic-collect
    ↓
data/semantic_case_inputs/*.yaml
    ↓
commit-semantic-generate (调用 3 个 prompts)
    ↓
data/semantic_cases/*.yaml (valid)
data/invalid_cases/*.yaml (invalid)
    ↓
commit-semantic-export
    ↓
data/exports/cases.jsonl
data/exports/summary.json
```

## 输出格式

每个 semantic case 包含：

- `commit_log` - 代码修改主动作
- `rules` - 对象语义约束
- `invariants` - 对象语义保持项
- `issue_text` - 压缩需求句
- `development_type` - 开发类型 (feature/bugfix/refactor/migration/optimize)
- `split_suggestion` - 拆分建议

## 待完成

### Executor 集成

`src/commit_semantic/prompt_runner.py` 已实现，使用 `executor` 参数接收 host 提供的执行函数：

```python
def run_prompt_with_claude(
    prompt_template: str,
    input_data: Dict[str, Any],
    executor: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """
    executor 由 Claude Code 环境提供，接收 prompt 字符串，返回响应字符串。
    """
```

**Executor 接口**:
- 输入: prompt 字符串（包含模板 + YAML 输入）
- 输出: YAML 格式的响应字符串
- 响应会被自动解析为 Python dict

**使用方式**:
1. 从 Claude Code skill 调用时，host 环境会自动注入 executor
2. 独立运行时，需要提供自定义 executor 函数

**注意**: HostExecutor 的具体实现和验证由后续完成。

### 可选增强

- [ ] 更智能的文件分组逻辑
- [ ] 更精确的 bugfix 证据检测
- [ ] 并行处理支持

## 与 semantic-harness 的关系

commit-semantic 是一个独立的子功能：

- 使用独立的命名空间 (`commit-semantic-*`)
- 使用独立的模块目录 (`src/commit_semantic/`)
- 使用独立的 prompts 目录 (`prompts/commit-semantic/`)
- 使用独立的数据目录 (`data/`)
- 不影响现有的 semantic-* skills 和 pipelines

## 文档

- 详细规范：`docs/plan/git-sematic-readme.md`
- Prompt 规范：`docs/plan/git-semantic-skill.md`
- 本文档：`docs/plan/COMMIT_SEMANTIC_SUMMARY.md`
