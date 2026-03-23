# Commit-Extract Rewrite + Commit-Semantic Adaptation

> Date: 2026-03-22
> Status: Draft

## Problem

commit-extract 的产出质量差：
- heuristic 用正则从 diff 提取中文摘要，信息密度低
- Task agent 分支是 stub，从未真正启用
- 输出 YAML 格式笨重，不支持增量 append
- commit-semantic 依赖 `commit_log` 扁平字符串做关键词匹配，浪费了结构化潜力

## Solution

用 `docs/generate_commit.md` 调优的 prompt 替代 heuristic，输出改为 JSONL，commit-semantic 重写消费逻辑。

## Architecture

三角色单向数据流：

```
Main Agent (orchestrator)
  │
  ├─ git log → SHA list
  ├─ git show --stat → weight estimation
  ├─ adaptive batching (weight budget + count cap)
  │
  ├─► Worker Agent ×N (parallel, general-purpose Task agents)
  │     ├─ receives: SHA list + prompt (from docs/generate_commit.md)
  │     ├─ per SHA: git show → analyze patch → JSON object
  │     └─ writes: data/commit-extract/tmp/{batch_id}.jsonl
  │
  └─► Merge Agent (after all workers complete)
        ├─ reads: tmp/*.jsonl
        ├─ dedup by sha
        ├─ groups by date → YYYY-MM
        ├─ appends to: data/commit-extract/YYYY-MM.jsonl
        └─ cleans up tmp/
```

Main agent 的 context 只有 SHA 列表 + stat 数字 + worker 完成状态。不接触任何 patch 内容。

## Adaptive Batching

按 patch weight 而非固定 commit 数量分 batch：

- Main agent 对每个 SHA 跑 `git show --stat` 提取 `insertions + deletions` 作为 weight
- 解析 `--stat` 输出的 summary line（`N files changed, X insertions(+), Y deletions(-)`），缺失的 insertions 或 deletions 视为 0
- Binary 文件（`Bin X -> Y bytes`）每个计固定 weight 500
- 无 summary line（empty commit）使用默认 weight 0
- 约束：`weight_budget = 3000 lines`，`max_commits_per_batch = 15`
- 当前 batch 的 `accumulated_weight + next_weight > budget` 或 `count >= max` 时 flush
- 单个 commit 超过 budget → 独占一个 worker

小 commit 自然聚合，大 commit 自动隔离，无需人工调参。

## Edge Cases

- **零 commit**：SHA 列表为空时不创建任何输出文件，直接退出成功
- **Merge commits**：`git log` 使用 `--no-merges` 过滤，不处理 merge commits
- **Empty commits**（`--allow-empty`）：worker 产出 `"sections": [], "rules_invariants": []`
- **Binary-only commits**：worker 正常分析，`git show` 会显示 binary diff 标记，prompt 按实际内容处理

## Worker Agent

输入：
- 一组 SHA（最多 15 个，总 weight ≤ 3000 行）
- `docs/generate_commit.md` prompt 内容
- 输出路径：`data/commit-extract/tmp/{batch_id}.jsonl`

执行流程：
```
for sha in batch:
    1. git show --stat --summary {sha}
    2. git show {sha}
    3. 按 prompt 规则分析 → 生成 JSON object
    4. append JSON line 到 tmp/{batch_id}.jsonl
```

每个 SHA 处理完立即 append 写入，不在 context 里积累前面的 patch 内容。

Worker 逐个处理 SHA。对每个 SHA，独立执行 `git show` 并按 prompt 分析，产出一个 JSON object 后立即 append 写入。Prompt 不修改，只替换 `<SHA>` 占位符。

Worker prompt 直接使用 `docs/generate_commit.md`，不改动。前缀指令说明：逐个处理 SHA 列表，每个 JSON object append 到指定输出路径。

## Output Schema

`data/commit-extract/YYYY-MM.jsonl`，每行一个 JSON object：

```json
{
  "sha": "<SHA>",
  "author": "<author or empty string>",
  "date": "<ISO 8601: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD>",
  "is_large_aggregate": true,
  "is_mixed": true,
  "sections": [
    {
      "name": "<generic functional block name>",
      "theme": "<short change theme>",
      "importance": "<primary|secondary>",
      "summary": "<optional section summary>",
      "items": [
        {
          "op": "<feat|bugfix|optimize|config|refactor|compat|safety|docs|test|cleanup|other>",
          "summary": "<semantic summary>"
        }
      ]
    }
  ],
  "rules_invariants": [
    {
      "kind": "<lifecycle|ownership|boundary|failure_isolation|compatibility|ordering|alignment|idempotency|resource_limit|other>",
      "statement": "<rule or invariant>",
      "enforced_by_commit": true
    }
  ]
}
```

不存储 `original_message`、`files`、`diff_chunks` — 均可从 `sha` 通过 git 恢复。

## Merge Agent

所有 worker 完成后启动：

1. glob `data/commit-extract/tmp/*.jsonl`
2. 逐文件读取，每行 parse 为 JSON object
3. 按 `sha` 去重（后出现的覆盖先出现的）
4. 按 `date` 字段提取 YYYY-MM 分组
5. 对每个月份：已有 `YYYY-MM.jsonl` → 读取已有 sha 集合，只 append 新的
6. 删除 `tmp/` 目录

## Resume / Incremental

- 读已有 `YYYY-MM.jsonl` 提取已处理 SHA 集合
- 从 SHA 列表中排除已处理的
- 只对新 commit 跑 batching + worker
- tmp/ 文件存在 = 上次中断，merge agent 可直接处理

## commit-semantic 重写

现有 5 阶段（split → analyze → aggregate → distill → export）简化为 4 阶段：

### Stage 1: ingest

- 读 `data/commit-extract/YYYY-MM.jsonl`
- 每个 JSON object 的每个 section 展开为一个 semantic unit：
  ```json
  {"sha": "...", "date": "...", "author": "...", "section_name": "...", "theme": "...", "importance": "...", "op": "...", "summary": "...", "is_large_aggregate": true, "is_mixed": true}
  ```
- commit 级别的 `is_large_aggregate` 和 `is_mixed` 标记携带到每个展开的 unit，供下游 aggregate 阶段差异化加权
- `rules_invariants` 单独收集到 `data/commit-semantic/invariants.jsonl`
- 输出：`data/commit-semantic/units/all.jsonl`

### Stage 2: aggregate

- 主聚合键：`theme`（跨 commit 的语义主题）；同 theme 不同 `section_name` 合并
- 统计每个 theme 的 `op` 分布（feat/bugfix/refactor/... 各多少）和 `importance` 分布（primary/secondary 比例）
- 高频 pattern 定义：同一 theme 出现在 ≥ 3 个不同 commit 中
- 输出 pattern schema：
  ```json
  {"theme": "...", "count": N, "distinct_commits": N, "op_distribution": {"feat": N, "bugfix": N, ...}, "importance_ratio": {"primary": N, "secondary": N}, "representative_summaries": ["...", "..."]}
  ```
- 输出：`data/commit-semantic/patterns.jsonl`

### Stage 3: distill

- 从 patterns 提取 canonical demands
- 评分公式：`score = distinct_commits × importance_weight`，其中 `primary = 2, secondary = 1`，importance_weight 取该 pattern 的加权平均
- 平分时按 `distinct_commits` 降序，再按 `theme` 字母序
- `rules_invariants` 作为补充输入 — 跨 ≥ 3 个 commit 出现的 invariant 额外加权
- 输出：`data/commit-semantic/canonical-demands.jsonl`

### Stage 4: export

- 汇总统计：bugfix ratio、top patterns、活跃模块
- 输出 schema：
  ```json
  {"total_units": N, "total_patterns": N, "op_distribution": {...}, "top_patterns": [...], "bugfix_ratio": 0.xx, "invariant_count": N, "date_range": {"from": "...", "to": "..."}}
  ```
- 输出：`data/commit-semantic/summary.json`

### 砍掉的内容

- **split 阶段** — sections/items 已经是天然的 change units
- **analyze 阶段的关键词分类和评分** — `op` 和 `importance` 已由 worker 标注
- **`files`、`diff_chunks` 传递** — 不再需要

## Files Changed

### commit-extract（重写）

| File | Change |
|------|--------|
| `skills/commit-extract/run.py` | 重写：删除 heuristic，改为 orchestrator 逻辑（SHA 收集 + stat 估算 + batch 分配） |
| `skills/commit-extract/SKILL.md` | 更新架构描述、输出 schema、usage |
| `skills/commit-extract/prompts/generate_commit_log.md` | 删除（被 `docs/generate_commit.md` 替代） |
| `docs/generate_commit.md` | 不改动（已调优的 prompt，worker 直接使用） |
| `src/io_utils.py` | 新增 `append_jsonl(items, file_path)` — 以 `mode='a'` 逐行 append JSON objects 到文件，Worker 和 Merge Agent 均使用此函数 |

### commit-semantic（重写）

| File | Change |
|------|--------|
| `skills/commit-semantic/run.py` | 重写：4 阶段（ingest → aggregate → distill → export），消费 JSONL sections/items |
| `skills/commit-semantic/SKILL.md` | 更新阶段描述、输入输出 schema |

### 清理

| File | Change |
|------|--------|
| `data/commit-extract/*.yaml` | 删除旧 YAML 输出 |
| `data/commit-extract/state.json` | 删除（resume 改为基于 JSONL SHA 扫描，不再需要独立 state 文件） |
| `data/commit-semantic/units/*.yaml` | 删除旧 YAML 输出 |
| `data/commit-semantic/functional/` | 删除（不再有 tier 分类） |
| `data/commit-semantic/non-functional/` | 删除 |

## Partial Failure Handling

- Worker 逐 SHA append 写入 tmp 文件。如果 worker 中途失败，tmp 文件包含已完成的 SHA 的有效 JSON lines
- Merge Agent 按 sha 去重，天然处理部分写入：重跑 worker 产生的重复记录会被去重过滤
- 如果 worker 在写入某行 JSON 中途崩溃（truncated line），Merge Agent 在 parse 时跳过无效行并 log warning

## Implementation Phases

1. **Phase 1: commit-extract 重写 + 测试** — io_utils append_jsonl、run.py orchestrator、SKILL.md
2. **Phase 2: commit-semantic 重写 + 测试** — 4 阶段消费 JSONL、SKILL.md
3. **Phase 3: E2E 集成测试 + 清理** — 端到端验证、删除旧 YAML/state 文件

## Testing

- commit-extract：mock git show 输出 → 验证 batch 分配逻辑 + JSONL 写入格式
- commit-semantic：fixture JSONL → 验证 ingest 展开 + aggregate 聚合 + distill 排序
- E2E：小 repo → commit-extract → commit-semantic → 验证 summary 输出
- Schema 验证：worker JSON 输出必须包含 sha、date、sections 字段（LLM 信任边界）
- JSONL 容错：ingest 阶段跳过无效 JSON 行并 log warning（与 merge agent 一致）

## Eng Review Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | SkillRunner 与 Task Agent 边界 | 1A: SkillRunner + batch manifest |
| 2 | get_commit_list --no-merges | 2A: 加可选参数 |
| 3 | ExportSummary dataclass | 3A: 删除，直接写 dict |
| 4 | src/commit_semantic/ 死代码 | 4A: Phase 3 清理 |
| 5 | io_utils SemanticCase 转换函数 | 5A: 删除 |
| 6 | Worker 输出 schema 验证 | 6A: E2E 中加 schema 验证 |
| 7 | Ingest JSONL 容错 | 加入本次 PR |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 6 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |

- **VERDICT:** ENG CLEARED — ready to implement
