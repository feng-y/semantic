# Skill Status

Track implementation state of the 5 target skills.

## Completed

### 1. `commit-extract`
Git history → structured commit metadata (按月聚合)。

| Item | Status |
|------|--------|
| Skill | `skills/commit-extract/` |
| Stages | `collect` (1 步) |
| Output | `data/commit-extract/YYYY-MM.yaml` |
| Tests | 722 passed (full suite) |
| Lines | 313 |

```
/commit-extract run --last 50
```

---

### 2. `commit-semantic`
Git commit metadata → semantic cases → canonical patterns。

| Item | Status |
|------|--------|
| Skill | `skills/commit-semantic/` |
| Stages | `split` → `analyze` → `aggregate` → `distill` (4 步) |
| Output | `data/commit-semantic/` (patterns, distill) |
| Tests | 722 passed (full suite) |
| Lines | 393 |

```
/commit-semantic run
/commit-semantic run --stage analyze
```

---

### 3. `repo_structure`
Three-source fusion: git history + gsd dossier + arch docs → versioned fact baseline。

| Item | Status |
|------|--------|
| Skill | `skills/repo_structure/` |
| Stages | `sample` → `hotspot` → `extract` → `augment` → `validate` → `baseline` (6 步) |
| Sources | `commit-extract/commit-semantic` (hotspot) + gsd 7-file dossier (extract) + `docs/ARCHITECTURE.md` (augment) |
| Output | `data/repo-structure/baseline/facts.vN.yaml` |
| Features | Schema validation, source-aware arbitration (4 轴), conflict preservation, preflight checks, state management |
| Tests | 11 dedicated + 722 full suite passed |
| Lines | 992 |

```
/repo-structure check    # preflight
/repo-structure run      # full pipeline
/repo-structure run --stage extract
/repo-structure resume
/repo-structure status
```

---

## Pending

### 4. `semantic-pipeline`
Transform fact baseline into semantic assets: domain map, concept map, pipeline map。

| Item | Status |
|------|--------|
| Skill | `skills/semantic-pipeline/` + 6 individual steps |
| Stages | `signals` → `candidates` → `recommend` → `review` → `finalize` (5 步) |
| Depends on | `repo_structure` (fact baseline) |
| Status | 需要重构（设计已有，待实现） |

### 5. `demand-pipeline`
Issue text → demand card。

| Item | Status |
|------|--------|
| Skill | `skills/demand-pipeline/` |
| Status | 现有实现，待评审 |

---

## Removed

以下旧 fact skill 已被 `repo_structure` 覆盖并删除：

- `semantic-fact-pipeline/` — covered by `repo_structure` orchestration
- `semantic-fact/` — covered by `repo_structure/run.py`
- `semantic-init/` — covered by `repo_structure` preflight
- `semantic-status/` — covered by `repo_structure` state

以下旧 fact skill 有独特产出，暂时保留：
- `semantic-discover/` — `repo-understanding` / `knowledge-confidence` prose 产出
- `semantic-refine/` — human feedback patch loop
- `semantic-baseline/` — prose baseline synthesis

---

## 5 Target Skills Summary

| # | Capability | Skill | Stages | Output |
|---|-----------|-------|--------|--------|
| 1 | fact | `repo_structure` | 6 | `facts.vN.yaml` |
| 2 | semantic | `semantic-pipeline` (+ 6 steps) | 5 | domain/concept/pipeline maps |
| 3 | demand | `demand-pipeline` | 5 | demand card |
| 4 | commit | `commit-extract` | 1 | `YYYY-MM.yaml` |
| 5 | commit | `commit-semantic` | 4 | patterns + distill |
