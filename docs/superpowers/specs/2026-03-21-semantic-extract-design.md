# Semantic Extract - 统一语义提取命令

**Date**: 2026-03-21
**Status**: Approved
**Author**: Claude

## Overview

统一语义提取命令，同时支持两个语义视角：
- **commit 视角**：功能语义表达（做什么功能/故事）
- **rules 视角**：工程化改进（优化、修复、约束）

基于 `rule.md` 规范，两者必须分离提取（different prompt），但可统一调用。

## Goals

1. 提供单一入口，同时提取 commit_log 和 rules/invariants
2. 复用现有 commit-refine 的 git 和 writer 模块
3. 支持灵活的模式选择（both/commit/rules）
4. 符合 rule.md 的"分离提取"要求

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    /semantic-extract                        │
├─────────────────────────────────────────────────────────────┤
│  参数: --last N | --since | --until | --range              │
│        --view both|commit|rules                             │
│        --dry-run                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  git_utils.get_commit_details(sha) ──► diff, title, body  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│  commit-refine prompt   │     │  rules-invariants       │
│  (功能语义视角)          │     │  prompt (工程约束视角)  │
└───────────┬─────────────┘     └───────────┬─────────────┘
            ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ commits_YYYY-MM.jsonl   │     │ rules_YYYY-MM.jsonl    │
│ title, body, commit_log │     │ rules, invariants      │
└─────────────────────────┘     └─────────────────────────┘
```

## Input

### CLI Parameters

| 参数 | 类型 | 说明 | 默认 |
|------|------|------|------|
| `--last N` | int | 最近 N 条 commit | 必选其一 |
| `--since YYYY-MM-DD` | string | 起始日期 | 可选 |
| `--until YYYY-MM-DD` | string | 截止日期 | 可选 |
| `--range SHA1..SHA2` | string | SHA 范围 | 可选 |
| `--view` | enum | 视角选择 | `both` |
| `--dry-run` | flag | 预览模式 | false |

### View Options

- `both`: 同时处理两个视角
- `commit`: 只生成 commit_log
- `rules`: 只生成 rules/invariants

## Output

### commit_refine JSONL Schema

```json
{
  "sha": "abc123...",
  "title": "feat: something",
  "body": "detailed description",
  "commit_log": ["line 1", "", "line 2"],
  "generated_at": "2026-03-21T10:30:00Z"
}
```

### rules_invariants JSONL Schema

```json
{
  "sha": "abc123...",
  "rules": [
    "修改此对象时必须保持与 X 子系统的兼容性边界",
    "修复此对象时必须保留与 Y 模块的对齐关系"
  ],
  "invariants": [
    "修改后必须保持 Z 行为不变",
    "修复后必须维持与 W 的映射一致性"
  ],
  "generated_at": "2026-03-21T10:30:00Z"
}
```

### Output Files

```
data/
├── commit_refine/
│   └── commits_YYYY-MM.jsonl
└── rules_invariants/
    └── rules_YYYY-MM.jsonl
```

## Deduplication

1. 扫描 `data/commit_refine/*.jsonl` 获取已处理 SHA（针对 commit 视角）
2. 扫描 `data/rules_invariants/*.jsonl` 获取已处理 SHA（针对 rules 视角）
3. 根据 `--view` 参数选择跳过已处理的 commit
4. Dry-run 模式下打印预览，不写入文件

## LLM Prompts

### commit-refine prompt

复用 `skills/commit-refine/prompts/refine.md`

### rules-invariants prompt

基于 rule.md 规范：

#### Rules Extraction（必须包含）

分析 diff，识别被修改对象周围的语义关系。回答：

- 修改此对象时，什么语义关系/边界不能被破坏？
- 什么对齐关系被恢复或保持？
- 什么兼容性边界需要维持？

**典型示例**：
- alignment constraints（对齐约束）
- compatibility boundaries（兼容性边界）
- boundedness requirements（边界要求）
- contract preservation（契约保持）
- mapping consistency（映射一致性）
- subsystem interaction rules（子系统交互规则）

#### Invariants Extraction（必须包含）

分析 diff 和代码变更，回答：

- 修改后，什么语义属性必须保持不变？
- 什么契约/协议必须继续满足？
- 什么外部可见的语义行为需要保持？

**典型示例**：
- preserved alignment（保持对齐）
- preserved compatibility（保持兼容）
- preserved boundedness（保持边界）
- preserved state consistency（保持状态一致性）
- preserved externally visible semantic behavior（保持外部语义行为）

#### 禁止生成

- 空检查建议
- 边界检查建议
- 异常处理建议
- 代码风格建议
- 代码动作的同义改写
- 通用正确性陈述（如"系统不应崩溃"、"代码应编译"）

## Module Structure

```
skills/
  └── semantic-extract/          # 新 skill
      ├── SKILL.md
      ├── run.py                  # 主入口
      └── prompts/
          ├── refine.md           # 复用 commit-refine 的 prompt
          └── extract.md          # 新 rules-invariants prompt

src/
  └── commit_refine/              # 复用并扩展现有模块
      ├── __init__.py
      ├── executor.py             # 复用，添加 rules 处理
      ├── git_utils.py           # 复用
      └── writer.py               # 扩展：添加 rules_invariants 写入
```

### Writer 模块扩展

需要在 `writer.py` 中添加以下函数：

```python
# 新增：rules_invariants 文件名
def get_rules_filename(commit_date: str) -> str:
    """生成 rules_YYYY-MM.jsonl 文件名"""
    ...

# 新增：加载已存在的 rules SHA 集合
def load_existing_rules_shas(output_dir: str = "data/rules_invariants") -> Set[str]:
    """扫描所有 rules_*.jsonl 文件，返回已处理的 SHA 集合"""
    ...

# 新增：写入 rules_invariants 记录
def append_rules_invariants(sha: str, rules: List[str], invariants: List[str], commit_date: str):
    """追加 rules_invariants 记录到 JSONL"""
    ...
```

## Error Handling

1. **JSON 解析失败**: 记录到 stderr，返回空结果，继续处理下一条
2. **Git 操作失败**: 跳过该 commit，记录错误
3. **LLM 调用失败**: 重试 1 次，失败则记录错误

### 部分失败处理（view=both 时）

当 `--view both` 模式下一个视角成功、另一个失败时：

- **commit 成功，rules 失败**: 该 commit 的 SHA 在 rules 文件中不被视为已处理，下次可重试
- **commit 失败，rules 成功**: 同理，commit 文件中不被视为已处理
- **日志记录**: 明确区分"完全成功"、"部分成功"、"完全失败"的 commit

### 输出文件命名一致性

统一使用下划线分隔：
- `commits_YYYY-MM.jsonl`
- `rules_YYYY-MM.jsonl`

## Stats Output

完成后打印：
- 总请求 commit 数
- commit 视角：处理数、跳过数（已存在）、成功数、失败数
- rules 视角：处理数、跳过数（已存在）、成功数、失败数
- 耗时

```
=== Semantic Extract Summary ===
Total commits requested: 10
Commit view: processed=8, skipped=2, errors=0
Rules view: processed=6, skipped=4, errors=0
Time elapsed: 45.2s
```

## Acceptance Criteria

1. ✅ 单一命令同时支持 commit 和 rules 两个视角
2. ✅ 参数与原有 commit-refine 完全兼容
3. ✅ 输出到独立的 JSONL 文件
4. ✅ 支持去重，避免重复处理
5. ✅ 支持 dry-run 预览
6. ✅ 复用现有 git_utils 和 writer 模块
7. ✅ 符合 rule.md 的分离提取要求

## Future Enhancements

- Quality score: LLM 对生成内容打分
- Validation: 第二轮 LLM 验证规则符合规范
- Compare: 对比同一 commit 的两个视角
