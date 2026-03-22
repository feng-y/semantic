# Repo-Structure & Domain-Model Design

**Date:** 2026-03-22
**Status:** Implementation-ready

---

## Semantic Foundation 定位

> **重点不是产出三张 Map，而是先有三条 fact extraction / augmentation pipeline。**
> Domain Map、Concept Map、Rule Map 只是这些流程沉淀后的知识载体，不是起点，也不是流程本身。

Semantic Foundation 关注的是**系统知识事实的提取、校准与沉淀**。

---

## 两条 pipeline

| Pipeline | Command | Input | Output |
|----------|---------|-------|--------|
| `repo-structure` | `/repo-structure` | git commits + gsd output + archi docs | `data/repo-structure/baseline/facts.vN.yaml` |
| `domain-model` | `/domain-model` | fact baseline | `data/domain-model/assets/` |

---

## 三条独立 fact extraction pipeline

每条 pipeline 都经过同一套 5 步框架：

```
compare (对比 repo 证据) → research (调研 claim 上下文)
       ↓                                    ↓
analyze (分析) ────────────────────────────→ evaluate (评价 claim 状态)
                                                    ↓
                                              recommend (推荐处置)
```

---

### Pipeline 1: commit pipeline (变更语义事实)

**前置条件:** `data/commit-extract/` 存在（commit-extract 已运行）
**输出:** `hotspot_map.yaml`

```
git commits
    │
    ├── commit-extract (git log + diff → 结构化变更记录)
    │       ↓
    │   data/commit-extract/monthly/*.yaml
    │       ↓
    ├── commit-semantic (语义聚类 → recurring change patterns)
    │       ↓
    │   data/commit-semantic/patterns/
    │       ↓
    └── hotspot_map.yaml
            (commit 视角: 热点模块、常见变更语义、领域演化高频区)
```

**如果 commit-extract 不存在:** hotspot 阶段先运行 commit-extract，再继续。

**Pipeline 1 各步骤含义:**

| 步骤 | commit pipeline |
|------|----------------|
| **compare** | 对比同一模块的多次 commit，确认 pattern 是否一致 |
| **research** | 调研高频变更的历史上下文（为什么这个模块反复变） |
| **analyze** | 分析 semantic patterns，识别 recurring change types |
| **evaluate** | 判断 pattern 真实性： recurring / isolated / noise |
| **recommend** | 纳入 hotspot_map / 标记为 isolated / 降权 |

**hotspot_map schema:** 复用 `commit-semantic` patterns 格式，按 module 聚合。

---

### Pipeline 2: codebase pipeline (代码结构事实)

**前置条件:** gsd 已预运行，`.planning/codebase/*.md` 已存在
**输出:** `codebase_map.yaml`

```
code tree
    │
    ├── sample (deterministic, Python)
    │   └── 读 gsd 输出文件，提取 key files
    │       → sample/manifest.yaml
    │
    └── extract (LLM worker, 按 section 分批)
        ├── batch 1: STRUCTURE.md → Directory Layout + Key File Locations
        ├── batch 2: ARCHITECTURE.md → Layers + Key Abstractions + Entry Points
        ├── batch 3: CONCERNS.md → Tech Debt + Known Bugs + Fragile Areas
        └── batch 4: STACK.md → Technology Stack (可选，优先级低)
            ↓
        codebase_map.yaml
            (Code 视角: symbol / relationship / pattern / boundary)
```

**sample 阶段:** 直接从 gsd STRUCTURE.md 提取 key files，不再独立遍历文件树。

**gsd 集成:**

- gsd 是外部预运行工具，不在 pipeline 内部调用
- gsd 输出路径: `{repo_root}/.planning/codebase/`
- 可通过 `--gsd-root` 参数覆盖
- 读取文件: `STRUCTURE.md`, `ARCHITECTURE.md`, `STACK.md`, `CONCERNS.md`
- extract 阶段只读现有文件，不运行 gsd

**Pipeline 2 各步骤含义:**

| 步骤 | codebase pipeline |
|------|-----------------|
| **compare** | 对比多个相似文件的结构，确认一致性和差异 |
| **research** | 调研文件上下文（为什么这样组织、依赖关系来源） |
| **analyze** | 分析代码结构：模块职责、注册点、扩展点、依赖边界 |
| **evaluate** | 判断 fact 准确性：confirmed / uncertain / contradicted |
| **recommend** | 纳入 codebase_map / 需进一步验证 / 标记为 uncertain |

**extract worker prompt 指令:**

- 从自然语言提取 fact entries，格式参照 Evidence Model
- STRUCTURE.md "Key Methods" → `symbol` locator
- CONCERNS.md "Files" → `file_path` + `locator`
- ARCHITECTURE.md "Key Abstractions" → `ast_pattern` locator

---

### Pipeline 3: architect augment pipeline (架构约束事实增强)

**前置条件:** `docs/ARCHITECTURE.md` 存在
**输出:** `architect_augment.yaml`

```
archi docs (docs/ARCHITECTURE.md)
    │
    ├── analyze (读文档，提取架构声明)
    │       ↓
    ├── compare with repo (LLM worker: 在 repo 中 grep/search 找 evidence)
    │       ↓
    └── architect_augment.yaml
            (evidence-backed claim + stable_ref)
```

**如果 archi docs 不存在:** augment 阶段输出空 `architect_augment.yaml`，pipeline 继续。

**Pipeline 3 各步骤含义:**

| 步骤 | architect pipeline |
|------|--------------------|
| **compare** | LLM worker 在代码中找对应实现的 evidence（类型定义、注册宏、配置项、调用链、guard code） |
| **research** | 调研 claim 的上下文（这个约束从哪来、为何存在） |
| **analyze** | 分析文档声明与 repo 实现的对应关系 |
| **evaluate** | 判断 claim 状态：evidence-backed / weakly-backed / gap / drift |
| **recommend** | 接受 / 修正 / 补充 / 拒绝 |

**Claim 状态定义:**

- **evidence-backed**: 代码中可找到明确证据
- **weakly-backed**: 只有间接证据，可信但不够强
- **gap**: 文档声称存在，但 repo 中未找到稳定证据
- **drift**: 文档与代码当前实现不一致

---

## Knowledge Consolidation

三条 pipeline 的输出在 `baseline` 阶段融合：

```
hotspot_map.yaml        (commit 视角)
codebase_map.yaml       (code 视角)
architect_augment.yaml  (archi 视角)
        │
        ↓ baseline (三源融合 + 冲突仲裁)
facts.vN.yaml
        ↓
Knowledge Views (整理层)
├── Domain Map
├── Concept Map
└── Rule Map
        ↓
Runtime Semantic Use
├── Demand Model Map
├── Demand Matching
└── Demand Card
```

---

## Repo-Structure Pipeline

### Command

```
/repo-structure [run|step|resume|status|reset]
/repo-structure --stage <stage>
/repo-structure --gsd-root <path>
```

### Stages

| Stage | Description | Worker |
|-------|-------------|--------|
| `sample` | 从 gsd 输出提取 key files，生成 manifest | Python (deterministic) |
| `hotspot` | 检查/运行 commit-extract + commit-semantic，生成 hotspot_map | Python + existing tools |
| `extract` | LLM worker 按 section 分批提取结构化 facts，生成 codebase_map | LLM worker (4 batches) |
| `augment` | LLM worker 分析 archi docs + compare with repo，生成 architect_augment | LLM worker |
| `validate` | Schema + rule 校验，去重，冲突标记 | Python (deterministic) |
| `baseline` | 三源融合，按优先级仲裁，freeze facts.vN.yaml | Python (deterministic) |

### Output

```
data/repo-structure/
├── sample/
│   └── manifest.yaml           # key files extracted from gsd
├── maps/
│   ├── codebase_map.vN.yaml    # (codebase pipeline)
│   ├── hotspot_map.vN.yaml     # (commit pipeline)
│   └── architect_augment.vN.yaml # (architect pipeline)
├── facts/
│   └── validated.yaml          # post-validate fact entries
├── baseline/
│   └── facts.vN.yaml           # fused, versioned baseline
└── state.json
```

### State

```json
{
  "version": "1.0",
  "stage": "baseline",
  "repo_path": "/path/to/repo",
  "repo_snapshot_commit": "<HEAD>",
  "gsd_root": "<path to .planning/codebase/>",
  "completed_stages": ["sample", "hotspot", "extract", "augment", "validate", "baseline"],
  "maps": {
    "codebase": "v0",
    "hotspot": "v0",
    "architect": "v0"
  },
  "artifacts_written": []
}
```

**三个 map version 独立递增**：每个 source 可单独重新运行，不强制联动。

### Data Schema: Fact Entry

```yaml
fact_id: <uuid>
domain: <problem domain>
category: domain | concept | rule | invariant
statement: <human-readable fact>
priority: P0 | P1 | P2
repo_snapshot_commit: <HEAD at run start>

evidence:
  - source_type: codebase | hotspot | architect
    file_path:
    locator_type: symbol | ast_pattern | config_key | test_case
    locator:
    stable_ref:
    rationale:

conflicts_with: [<fact_id>]  # If any
resolution_reason: <when override applied>

metadata:
  generated_at: <ISO timestamp>
  mapper_version: <tool version>
```

### Baseline Arbitration Rules

当同一 fact 出现多次时，按以下规则仲裁：

1. **优先级高的 evidence 胜出**: architect > hotspot > codebase
2. **同优先级时**: recurring > evidence-backed > isolated
3. **无法仲裁时**: 两个 fact 都保留，由 architect 手工标记

---

## Domain-Model Pipeline

### Command

```
/domain-model [run|step|resume|status|reset]
```

### Prerequisites

Requires `data/repo-structure/baseline/facts.vN.yaml`.

### Stages

| Stage | Description |
|-------|-------------|
| `signals` | Read fact baseline, extract domain signals |
| `candidates` | Worker agents generate domain candidates |
| `score` | Worker agents score candidates (clarity, boundary, reusability) |
| `aggregate` | Group by domain, extract patterns |
| `distill` | Synthesize canonical domain assets |

### Output

```
data/domain-model/
├── units/all.yaml          # All domain units
├── scored/                 # Scored candidates
│   └── units.yaml
├── patterns/                # Aggregated patterns per domain
│   └── {domain}.yaml
├── assets/                  # Canonical domain assets
│   └── {domain}-asset.yaml
└── state.json
```

**signals 阶段读的是 `facts.vN.yaml`**（融合后），maps 目录供人工 review。

**domain-model 与 semantic/ 的关系**: 完全替换；原 `semantic/` 目录废弃。

---

## Architecture (Team Agent Pattern)

Identical to commit-extract/commit-semantic:

```
SKILL.md expands into main agent context
    ↓
Main agent orchestrates via Task tool (batching, aggregation)
    ↓
Worker agents do isolated LLM analysis (fresh context, no token bloat)
    ↓
Workers return structured results (YAML/JSON)
    ↓
Main agent writes output files
```

### SKILL.md Structure

```markdown
---
name: repo-structure
description: Extract structured facts from codebase + git history
---

# Repo Structure

[Main agent orchestration steps]

## Worker Agents

[Describe each worker type and when spawned]

## Output

[Output format and location]
```

### Worker Prompt Templates

```
skills/repo-structure/prompts/
├── extract_codebase.md      # extract: LLM, 4 batches by gsd section
├── extract_hotspot.md       # (复用 commit-semantic, 或内部处理)
├── augment_architect.md      # augment: LLM, analyze + compare with repo
├── validate_facts.md        # validate: schema + rule validation
└── score_domain.md          # (domain-model 共享)
```

### run.py Structure

```python
class RepoStructureRunner(SkillRunner):
    STAGES = ["sample", "hotspot", "extract", "augment", "validate", "baseline"]
    PIPELINE = "repo-structure"

    # Team Agent hooks
    def _batch_units(self, units, batch_size=20): ...
    def _spawn_worker(self, batch, prompt_template): ...
    def _get_worker_prompt_template(self, name): ...

    # Stage implementations
    def _run_sample(self, state): ...
    def _run_hotspot(self, state): ...
    def _run_extract(self, state): ...
    def _run_augment(self, state): ...
    def _run_validate(self, state): ...
    def _run_baseline(self, state): ...
```

---

## Commands

| New Command | Old Command (Hard Cutoff) |
|-------------|---------------------------|
| `/repo-structure` | `/semantic-fact-pipeline` |
| `/domain-model` | `/semantic-pipeline` |

No aliases retained.

---

## Data Flow

```
gsd (预运行) → .planning/codebase/
                        │
                        ├── STRUCTURE.md      ──→ sample ──→ extract (batch 1)
                        ├── ARCHITECTURE.md   ──→ extract (batch 2)
                        ├── CONCERNS.md       ──→ extract (batch 3)
                        └── STACK.md          ──→ extract (batch 4)
                                                      ↓
git commits ──→ commit-extract ──→ commit-semantic ──→ hotspot_map ──┐
                                                                        │
archi docs ──→ augment (LLM: compare with repo) ──→ architect_augment ─┤
                                                                        │
                                                        baseline ───────┤
                                                                        │
                                               facts.vN.yaml ◄──────────┘
                                                        │
domain-model
  └── signals → candidates → score → aggregate → distill
        │
        ↓
data/domain-model/assets/
```

---

## Key Decisions

1. **Evidence model uses locator (not line_range/snippet)** — stable across formatting/reformatting
2. **Three independent source pipelines** — each with analyze/compare/research/evaluate/recommend framework
3. **hotspot_map from commit-extract + commit-semantic** — not raw git stats
4. **Architect augmentation is evidence-backed** — must have evidence + rationale + stable_ref
5. **Evidence priority: architect > rule-validated hotspot > codebase** — all sources are fact-based
6. **No aliases** — hard cutoff of old commands
7. **Team Agent architecture** — aligned with commit-extract/commit-semantic pattern
8. **Three Maps are result views, not starting point** — Domain/Concept/Rule Map are knowledge organization outputs, not the extraction process itself
9. **gsd is external, pre-run** — repo-structure reads existing `.planning/codebase/*.md`, does not invoke gsd internally
10. **extract by gsd section** — 4 batches matching STRUCTURE/ARCHITECTURE/CONCERNS/STACK
11. **augment uses LLM worker** — analyze + compare with repo, not simple script
12. **archi docs optional** — augment outputs empty yaml if docs missing, pipeline continues
13. **Three map versions independent** — each source can re-run without forcing others
14. **baseline version starts at v0, increments each run** — no manual acceptance gate
15. **commit-extract required for hotspot** — hotspot stage runs commit-extract if missing
