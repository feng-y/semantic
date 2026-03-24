# Architecture

**Analysis Date:** 2026-03-24

## Overall Pattern

Semantic Harness uses a **layered, pipeline-oriented architecture** with declarative skills and deterministic orchestration. The codebase separates:

1. **Skill definitions** (declarative pipeline contracts in `skills/`)
2. **Prompt templates** (LLM interaction patterns in `prompts/`)
3. **Runtime orchestration** (deterministic execution in `src/`)
4. **Artifact versioning** (immutable outputs in `docs/fact/` and `data/`)

## Core Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│  CLI Entry (main.py) → Dispatcher → Skill Runner            │
├─────────────────────────────────────────────────────────────┤
│  Executors (discovery, refine, demand, semantic)            │
├─────────────────────────────────────────────────────────────┤
│  Context Builder → Prompt Loader → Host Executor            │
├─────────────────────────────────────────────────────────────┤
│  Artifact Writer → Validation → Versioning → Baseline       │
└─────────────────────────────────────────────────────────────┘
```

## Entry Points

| Entry | File | Purpose |
|-------|------|---------|
| CLI | `src/main.py` | Main entry for `semantic-harness` command |
| Dispatcher | `src/dispatcher.py` | Routes commands: init, discover, refine, status, reset |
| Plugin | `.claude-plugin/plugin.json` | Claude Code plugin registration |

## Major Modules

### Top-Level Orchestration (`src/`)

| Module | Responsibility |
|--------|---------------|
| `src/dispatcher.py` | Command routing to handlers |
| `src/discovery_executor.py` | FACT discovery pipeline execution |
| `src/refine_executor.py` | Artifact refinement with architect feedback |
| `src/skill_runner.py` | Base class for staged skills with state management |
| `src/skill_loader.py` | Parse `SKILL.md` definitions |
| `src/context_builder.py` | Build prompt context from repo + artifacts |
| `src/artifact_writer.py` | Versioned artifact persistence |
| `src/artifact_validation.py` | Structural validation of artifacts |
| `src/prompt_loader.py` | Prompt file resolution |
| `src/state_inspector.py` | Read state and recommend next action |
| `src/host_executor.py` | Host LLM execution protocol |

### Semantic Layer (`src/semantic/`)

Staged pipeline: signals → candidates → recommendations → review → finalize

| Module | Stage |
|--------|-------|
| `src/semantic/run.py` | Runner orchestration |
| `src/semantic/extract_signals.py` | Step 1: extract signals |
| `src/semantic/build_candidates.py` | Step 2: synthesize candidates |
| `src/semantic/score_recommend.py` | Step 3: score and recommend |
| `src/semantic/apply_review.py` | Step 4: review decisions |
| `src/semantic/finalize_assets.py` | Step 5: finalize assets |
| `src/semantic/stage_registry.py` | Stage sequencing |

### Demand Layer (`src/demand/`)

5-stage deterministic transformation: normalize → map → match → build → validate

| Module | Stage |
|--------|-------|
| `src/demand/run.py` | Pipeline runner |
| `src/demand/normalize_issue.py` | Normalize issue text |
| `src/demand/map_semantics.py` | Map to semantic assets |
| `src/demand/match_development_type.py` | Match development type |
| `src/demand/build_demand_card.py` | Build demand card |
| `src/demand/validate_demand_card.py` | Validate card schema |

### Commit-Semantic (`src/commit_semantic/`)

| Module | Purpose |
|--------|---------|
| `src/commit_semantic/git_utils.py` | Git CLI wrappers |
| `src/commit_semantic/domain_utils.py` | Domain assignment utilities |

## Data Flow

### FACT Pipeline Flow
```
CLI → dispatcher → run_discovery/run_refine
    → load skill definition
    → for each step:
        → load prompt
        → build context (repo tree + prior artifacts)
        → call host executor
        → validate output
        → write versioned artifact
    → prune old versions
    → update semantic snapshot
```

### Semantic Pipeline Flow
```
runner → stage_registry → per-stage modules
    → state stored in workspace YAML
    → finalize guarded by review/evidence conditions
    → outputs semantic assets for demand mapping
```

### Demand Pipeline Flow
```
normalize_issue → map_semantics → match_development_type
    → build_demand_card → validate_demand_card
    → optional write to YAML
```

## Key Abstractions

### Skill Definition Contract
Skills are declared in `skills/<name>/SKILL.md` with YAML frontmatter:
- `steps`: ordered list of prompt/apply/conditional actions
- `run.py`: optional custom runner extending `SkillRunner`

### Artifact Versioning
- Working artifacts: `docs/fact/discovery/name.vN.md`
- Baseline artifacts: `docs/fact/baseline/name.md` (unversioned, immutable)
- Version window: 3 versions retained by default

### State Management
- `HarnessState` dataclass tracks stage completion and artifacts
- Persisted to `.harness/` as YAML
- Supports step/resume/reset semantics

## Design Decisions

1. **Prompt-driven but code-controlled**: LLM generates content, but orchestration, validation, and versioning are deterministic code
2. **Executor injection**: Host LLM execution is injected via protocol, not direct SDK dependency
3. **Versioned artifacts**: All working outputs are versioned; baseline is immutable once accepted
4. **Structured status over exceptions**: Orchestration returns result dicts with explicit status fields

---

*Architecture analysis: 2026-03-24*
