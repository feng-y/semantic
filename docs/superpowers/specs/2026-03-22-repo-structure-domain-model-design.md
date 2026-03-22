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

**前置条件:** `data/commit-extract/` 存在（commit-extract 已运行）—— 严格 upstream，缺失则报错，不自举。
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

**Pipeline 1 各步骤含义:****

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
**gsd 角色:** 上游分析器，不在 pipeline 内调用；`run.py` 只消费 `.planning/codebase/` 现有文件

**缺失输入报错:**

```
missing prerequisite: gsd codebase artifacts not found
expected files:
  - .planning/codebase/STRUCTURE.md
  - .planning/codebase/ARCHITECTURE.md
  - .planning/codebase/STACK.md
  - .planning/codebase/CONCERNS.md
action: run gsd map-codebase first
```

**输出:** `codebase_map.yaml`

```
code tree
    │
    ├── sample (gsd-guided + repo fallback)
    │   ├── STRUCTURE.md guided: Directory Layout + Key Files
    │   ├── ARCHITECTURE.md referenced files/symbols
    │   ├── CONCERNS.md referenced files
    │   └── repo fallback probe (if gsd files incomplete)
    │       ↓
    │   sample/manifest.yaml
    │
    └── extract (LLM worker, 按 section 切分再路由)
        ├── section: STRUCTURE.md / Directory Layout → locator: file_path
        ├── section: STRUCTURE.md / Key File Locations → locator: symbol
        ├── section: ARCHITECTURE.md / Layers → locator: ast_pattern
        ├── section: ARCHITECTURE.md / Key Abstractions → locator: symbol
        ├── section: ARCHITECTURE.md / Entry Points → locator: symbol
        ├── section: CONCERNS.md / Tech Debt → locator: file_path
        ├── section: CONCERNS.md / Fragile Areas → locator: file_path + test_case
        └── section: STACK.md / Technology Stack → locator: config_key
            ↓
        codebase_map.yaml
            (Code 视角: symbol / relationship / pattern / boundary)
```

**section 切分原则:**

- 不是按整文件分 batch，而是先 deterministic split section，再按 section 类型路由
- 每个 section 对应固定 `locator_type` 映射规则
- 输出单位不是 paragraph/summary，而是带 evidence binding 的 fact entry

**Pipeline 2 各步骤含义:**

| 步骤 | codebase pipeline |
|------|-----------------|
| **compare** | 对比多个相似文件的结构，确认一致性和差异 |
| **research** | 调研文件上下文（为什么这样组织、依赖关系来源） |
| **analyze** | 分析代码结构：模块职责、注册点、扩展点、依赖边界 |
| **evaluate** | 判断 fact 准确性：confirmed / uncertain / contradicted |
| **recommend** | 纳入 codebase_map / 需进一步验证 / 标记为 uncertain |

**extract worker prompt 核心指令:**

> Extract atomic fact entries from this section.
> Each fact must be explicitly supported by the section text.
> Prefer concrete module / file / symbol / rule facts over summaries.
> Attach an evidence locator using the section-to-locator mapping policy.
> Do not infer implementation details not stated in the section.
> Output unit is a fact entry with evidence binding, not a paragraph summary.

**extract 输出格式:**

```yaml
- fact_type:
  subject:
  predicate:
  object:
  confidence:
  evidence:
    source_doc:
    locator_type:  # 由 section 决定
    locator:
    stable_ref:
    rationale:
```

---

### Pipeline 3: architect augment pipeline (架构约束事实增强)

**前置条件:** `docs/ARCHITECTURE.md` 存在
**输出:** `architect_augment.yaml`

**缺失 archi docs 时:** augment 阶段输出空 `architect_augment.yaml`，pipeline 继续。

**两段式处理:**

```
archi docs (docs/ARCHITECTURE.md)
    │
    ├── Phase 1: Python evidence collection (deterministic)
    │   ├── grep / ripgrep 搜索 symbol
    │   ├── macro / registry pattern search
    │   ├── config key search
    │   └── test / assertion / comment search
    │       ↓
    │   candidate_evidence.json (候选证据集合)
    │
    └── Phase 2: LLM claim adjudication
        ├── 输入: architect claim + candidate_evidence.json + stable refs + search misses
        │       ↓
        └── architect_augment.yaml (evidence-backed claim + stable_ref)
```

**Phase 1 (Python) 适合:** 找证据候选（grep/search），确定性高
**Phase 2 (LLM) 适合:** 判断 claim 与 evidence 是否匹配，语义理解

**Pipeline 3 各步骤含义:**

| 步骤 | architect pipeline |
|------|--------------------|
| **compare** | Phase 1 Python: grep/search 找 evidence 候选；Phase 2 LLM: 对照 claim 判断匹配度 |
| **research** | 调研 claim 的上下文（这个约束从哪来、为何存在） |
| **analyze** | 分析文档声明与 repo 实现的对应关系 |
| **evaluate** | Phase 2 LLM 判断: evidence-backed / weakly-backed / gap / drift |
| **recommend** | Phase 2 LLM 输出: 接受 / 修正 / 补充 / 拒绝 |

**augment LLM prompt 核心:**

> Judge whether the architecture claim is supported by the provided repo evidence candidates.
> Prefer direct implementation evidence over comments.
> Mark as gap if no stable supporting evidence exists.
> Mark as drift if the repo contradicts the claim.
> Attach stable_ref from the most authoritative matched evidence.

**augment LLM 输出格式:**

```yaml
- claim_id:
  claim_text:
  status: evidence_backed|weakly_backed|gap|drift
  matched_evidence:
    - stable_ref:
      rationale:
  notes:
  recommendation: accept|modify|supplement|reject
```

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
Knowledge Views (整理层, derived from baseline)

| Map | 性质 | 说明 |
|-----|------|------|
| Domain Map | **derived knowledge view** | 从 facts.vN.yaml 整理得到 |
| Concept Map | **derived knowledge view** | 从 facts.vN.yaml 整理得到 |
| Rule Map | **derived knowledge view** | 从 facts.vN.yaml 整理得到 |

**`facts.vN.yaml` 是唯一 source-of-truth。** Domain / Concept / Rule Map 不得直接编辑，必须从 baseline facts 派生。Demand Matching、Demand Card 等运行时语义消费默认从 baseline facts 出发。
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
/repo-structure [run|step|resume|status|reset|check]
/repo-structure --stage <stage>
/repo-structure --gsd-root <path>
```

### Preflight

**原则: 先检查依赖图，再执行当前节点；不在节点内部隐式补跑上游。**

`/repo-structure check` 输出结构化报告：

```yaml
ok: true|false
stage: <target_stage>
missing:   # 缺失依赖
  - artifact: <path>
    producer: <upstream skill>
    suggestion: run <command>
invalid:   # 存在但不合法
  - artifact: <path>
    reason: empty|schema_invalid|stale
    artifact_commit: <commit>
    current_commit: <HEAD>
warnings:  # 可继续但有风险
  - artifact: <path>
    issue: stale_artifact|schema_version_mismatch
    detail: ...
```

**repo-structure requires:**

```yaml
requires:
  repo_root: true          # 当前目录是 git repo root
  git_repo: true           # 存在 .git/
  writable_dirs:
    - data/repo-structure/
  inputs:
    hotpath:
      - data/commit-extract/              # upstream: commit-extract
    gsd:
      - .planning/codebase/STRUCTURE.md     # upstream: gsd map-codebase
      - .planning/codebase/ARCHITECTURE.md
      - .planning/codebase/STACK.md
      - .planning/codebase/CONCERNS.md
```

**freshness check:**

- artifact 是否为空
- artifact schema 是否合法
- artifact 是否落后于当前 repo HEAD
- artifact 的 source version 是否兼容

**错误模式:**

| 模式 | 行为 |
|------|------|
| 严格 fail-fast（默认） | 缺失依赖直接报错，列出缺什么、谁生产、怎么补 |
| `--continue` | 警告但继续，只对 optional inputs 生效 |

**不做的:** 不在 stage 内部偷偷补跑上游依赖。控制流必须透明。

### Stages

| Stage | Description | Worker |
|-------|-------------|--------|
| `sample` | 从 gsd 输出提取 key files，生成 manifest | Python (deterministic) |
| `hotspot` | 检查 commit-extract 产物是否满足，执行 hotspot_map 生成；严格 upstream，缺失则报错 | Python + existing tools |
| `extract` | LLM worker 按 DocSectionTask 分批提取结构化 facts，生成 codebase_map | LLM worker (DocSectionTask batches) |
| `augment` | LLM worker 分析 archi docs + compare with repo，生成 architect_augment | LLM worker |
| `validate` | Schema + rule 校验，去重，冲突标记 | Python (deterministic) |
| `baseline` | 三源融合，按优先级仲裁，freeze facts.vN.yaml | Python (deterministic) |

### Output

```
data/repo-structure/
├── sample/
│   └── manifest.yaml           # gsd-guided + repo fallback sampling
├── maps/
│   ├── codebase_map.vN.yaml    # (codebase pipeline)
│   ├── hotspot_map.vN.yaml    # (commit pipeline)
│   └── architect_augment.vN.yaml # (architect pipeline)
├── facts/
│   └── validated.yaml          # post-validate fact entries
├── baseline/
│   ├── facts.vN.yaml           # fused, versioned baseline
│   └── snapshot.yaml           # source version combination
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
  "snapshot": {
    "version": "sf-YYYY-MM-DD.N",
    "sources": {
      "hotspot_map": "v0",
      "codebase_map": "v0",
      "architect_augment": "v0"
    }
  },
  "artifacts_written": []
}
```

**三个 map version 独立递增:** 每个 source 可单独重新运行，不强制联动。
**snapshot version:** 记录三者的输入版本组合，用于整体可追溯。

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
3. **同一 statement，commit 不同**: 优先当前 snapshot；旧 snapshot 仅保留为 lineage/history，不参与当前 baseline 覆盖
4. **无法仲裁时**: 两个 fact 都保留，由 architect 手工标记

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
├── extract_codebase.md      # extract: LLM, DocSectionTask batches
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
                        ├── STRUCTURE.md      ──→ extract (by DocSectionTask)
                        ├── ARCHITECTURE.md   ──→ extract (by DocSectionTask)
                        ├── CONCERNS.md       ──→ extract (by DocSectionTask)
                        └── STACK.md          ──→ extract (by DocSectionTask)
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
9. **gsd is upstream analyzer, not internal command** — `run.py` only consumes `.planning/codebase/`, does not invoke gsd internally
10. **extract by section, not by file** — deterministic section split, then route by section type; each section has fixed locator_type mapping
11. **augment is two-phase: Python collection + LLM adjudication** — Python finds evidence candidates, LLM judges claim-evidence match
12. **archi docs optional** — augment outputs empty yaml if docs missing, pipeline continues
13. **Three map versions independent + snapshot version** — each source can re-run without forcing others; snapshot records combination
14. **baseline version starts at v0, increments each run** — no manual acceptance gate
15. **commit-extract is strict upstream artifact** — hotspot checks `data/commit-extract/` exists; missing = error, no bootstrap
16. **sample is gsd-guided + repo fallback** — STRUCTURE.md as primary input, fallback probe if gsd files incomplete
17. **gsd missing input error is explicit** — lists expected files and recommended action
18. **extract output unit is fact entry with evidence binding** — not paragraph summary; includes locator_type, locator, stable_ref, rationale
19. **preflight before execution** — check dependencies, freshness, repo state before running; do not silently bootstrap upstream
