# Commit-Extract & Commit-Semantic Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement task-by-task with TDD.

**Goal:** Implement commit-extract and commit-semantic skills using Claude Code native **Team Agent** architecture.

---

## Architecture: SKILL.md + Prompt Templates + Task Tool

### How It Works

```
User triggers /commit-extract or /commit-semantic
    ↓
SKILL.md expands into main agent context (NOT a Python script)
    ↓
Main agent reads plan, prepares context, spawns workers via Task tool
    ↓
Workers execute with their prompt templates (isolated context)
    ↓
Workers return results to main agent
    ↓
Main agent aggregates and writes output files
```

### File Organization Pattern

```
skills/
├── commit-extract/
│   ├── SKILL.md              # Main agent instruction template
│   └── prompts/
│       └── generate_commit_log.md  # Worker agent prompt
├── commit-semantic/
│   ├── SKILL.md              # Main agent instruction template
│   └── prompts/
│       ├── classify.md       # Classification worker
│       ├── score.md          # Scoring worker
│       └── distill.md        # Distillation worker
```

### Key Principle

**SKILL.md is the main agent's instruction set, NOT a Python script.**
- SKILL.md defines WHAT the main agent should do (orchestrate workers)
- Prompt templates define WHAT workers should do (analyze commits)
- `run.py` is minimal — just prints SKILL.md content or delegates to skill system

Workers are spawned via Task tool:
```
Task tool (general-purpose):
  description: "Analyze commit batch"
  prompt: |
    [Injected from prompt template + batch context]
```

---

## Critical Constraints

### 1. COMMIT LOG IS REGENERATED FROM DIFF

**COMMIT LOG IS NEVER TAKEN FROM ORIGINAL COMMIT MESSAGE OR ISSUE TEXT.**

- Worker agents receive diff_chunks and regenerate commit_log from code changes
- Original message stored as `original_message` (reference only)
- The canonical field is `commit_log` (regenerated)

### 2. BATCH PROCESSING

- Commits split into batches (20-50 per worker)
- Each worker handles one batch
- Workers return structured results
- Main agent aggregates and writes output

---

## Output Schema

### commit-extract: data/commit-extract/YYYY-MM.yaml

```yaml
metadata:
  month: "2024-03"
  total_commits: 45

commits:
  - commit_id: "abc123"
    timestamp: "2024-03-15T10:30:00"
    author: "yan."
    original_message: "feat: add parser legacy support"
    files: ["src/parser.py"]
    diff_chunks: ["diff --git a/src/parser.py..."]
    commit_log: "在 parser 中补充 legacy 语法的边界检查处理"
```

### commit-semantic: data/commit-semantic/

```
units/all.yaml
functional/
├── high/units.yaml     # Score >= 8
├── medium/units.yaml   # Score 5-7
└── low/units.yaml     # Score < 5
non-functional/
└── all/units.yaml
patterns/
└── {module}.yaml
```

---

## Task 1: Re-implement commit-extract

**Files:**
- Rewrite: `skills/commit-extract/SKILL.md`
- Create: `skills/commit-extract/prompts/generate_commit_log.md`
- Minimal: `skills/commit-extract/run.py`
- Test: `tests/e2e/test_commit_extract.py`

### Step 1: Write failing test

```python
def test_commit_extract_regenerates_commit_log():
    """Worker agent receives diff, regenerates commit_log from code changes."""
    # Verify: commit_log != original_message
    # Verify: commit_log is action-oriented, in Chinese
    # Verify: grouped by month
```

### Step 2: Run test — expect FAIL

### Step 3: Write SKILL.md (main agent orchestration)

```markdown
---
name: commit-extract
description: Use when extracting commit logs from git history using team agents
---

# Commit Extract

Analyze git commits and regenerate commit_log from code diffs using team agents.

## How It Works

1. Read git commits (from --repo path)
2. Group by month
3. Batch commits (30 per batch)
4. Spawn worker agents (one per batch)
5. Workers regenerate commit_log from diff
6. Aggregate results by month
7. Write data/commit-extract/YYYY-MM.yaml

## Worker Agent: commit-log-generator

Each worker receives a batch of commits with their diffs.
Worker regenerates commit_log for each commit based on code changes.

Spawn workers via Task tool:
```
Task tool (general-purpose):
  description: "Regenerate commit logs from diff batch"
  prompt: |
    [Load from skills/commit-extract/prompts/generate_commit_log.md]
    [Inject batch context: list of commits with diff_chunks]
```

## Output Fields

| Field | Source | Purpose |
|-------|--------|---------|
| commit_id | git | Identifier |
| timestamp | git | Temporal grouping |
| author | git | Attribution |
| original_message | git | Reference only |
| files | git diff-tree | Change scope |
| diff_chunks | git show | Raw diff |
| commit_log | Worker agent | **Regenerated from diff** |
```

### Step 4: Write prompts/generate_commit_log.md (worker prompt)

```markdown
# Generate Commit Log

You are a commit-log-generator worker agent.
Given a batch of git commits, regenerate commit_log for each from its diff.

## Your Task

For each commit:
1. Read the diff_chunks
2. Based on the code changes, generate a commit_log
3. commit_log describes WHAT code changed and HOW

## Rules

- NEVER use the original commit message
- Generate from diff ONLY
- Use action verbs: 补充, 新增, 调整, 重构, 修正
- Keep under 50 characters
- Describe the code change, not the intent

## Output Format

Return YAML:
```yaml
results:
  - commit_id: "abc123"
    commit_log: "在 parser 中补充 legacy 语法的边界检查"
  - commit_id: "def456"
    commit_log: "新增 Redis client 的连接池配置"
```
```

### Step 5: Run tests — expect PASS

### Step 6: Commit

---

## Task 2: Re-implement commit-semantic

**Files:**
- Rewrite: `skills/commit-semantic/SKILL.md`
- Create: `skills/commit-semantic/prompts/classify.md`
- Create: `skills/commit-semantic/prompts/score.md`
- Create: `skills/commit-semantic/prompts/distill.md`
- Test: Update `tests/e2e/test_commit_semantic.py`

### Step 1: Write failing tests

```python
def test_semantic_reads_commit_log_not_message():
    """Reads commit_log field from extract output, NOT original_message."""
    pass

def test_classify_functional():
    """feat, bugfix, optimize = functional"""
    pass

def test_classify_non_functional():
    """refactor, test, config, cleanup = non-functional"""
    pass

def test_split_by_module():
    """Commits split into units by module detection."""
    pass

def test_score_functional():
    """Functional commits scored 0-10."""
    pass

def test_aggregate_patterns():
    """High-scored aggregated by module."""
    pass

def test_distill_demands():
    """Canonical demands extracted."""
    pass
```

### Step 2: Run tests — expect FAIL

### Step 3: Write SKILL.md (main agent orchestration)

```markdown
---
name: commit-semantic
description: Use when analyzing commit semantics with team agents
---

# Commit Semantic

Semantic analysis of commits: split, score, aggregate, distill.

## Prerequisites

Requires data/commit-extract/*.yaml with commit_log fields.

## Stages

### Stage 1: split
- Load data/commit-extract/*.yaml
- Read commit_log (NOT original_message)
- Detect modules from commit_log
- Split multi-module commits into separate units
- Save to data/commit-semantic/units/all.yaml

### Stage 2: analyze
- Load units
- Classify: functional vs non-functional by prefix
- Batch functional units (20 per worker)
- Workers score: clarity, domain, reusability (0-10)
- Save: functional/{high,medium,low}/, non-functional/all/

### Stage 3: aggregate
- Load high-scored units
- Group by module
- Extract patterns
- Save: patterns/{module}.yaml

### Stage 4: distill
- Load patterns
- Extract canonical demands
- Save: canonical-demands.yaml

## Worker Agents

Spawn via Task tool with prompts from skills/commit-semantic/prompts/

## Classification

| Prefix | Category | Scored |
|--------|----------|--------|
| feat: | functional | Yes |
| bugfix: | functional | Yes |
| optimize: | functional | Yes |
| refactor+bugfix: | functional | Yes |
| refactor: | non-functional | No |
| test: | non-functional | No |
| config: | non-functional | No |
| cleanup: | non-functional | No |
```

### Step 4: Write prompt templates

**prompts/classify.md** — classify commit as functional/non-functional
**prompts/score.md** — score functional commit on clarity/domain/reusability
**prompts/distill.md** — extract canonical demands from high-scored

### Step 5: Run tests — expect PASS

### Step 6: Commit

---

## Task 3: Update SKILL.md Documentation

Finalize both SKILL.md files with accurate architecture description.

---

## Task 4: Run Full E2E Test

1. Create temp git repo with sample commits (feat, bugfix, refactor, test, config)
2. Run commit-extract
3. Run commit-semantic
4. Verify:
   - data/commit-extract/YYYY-MM.yaml exists
   - commit_log regenerated (≠ original_message)
   - data/commit-semantic/functional/{high,medium,low}/ exists
   - data/commit-semantic/patterns/ exists

---

## Task 5: Deprecate Old Pipeline

Mark `src/commit_semantic/pipeline.py` as deprecated.

---

## Completion

All tasks complete. Skills use Team Agent architecture:
- SKILL.md = main agent orchestration (instruction template)
- prompts/*.md = worker agent instructions
- Task tool spawns isolated worker agents
- Main agent aggregates and writes files
