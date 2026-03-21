# Commit-Extract & Commit-Semantic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement commit-extract and commit-semantic skills based on approved design spec

**Architecture:** commit-extract aggregates raw commits by month; commit-semantic does cross-commit analysis, scoring, and pattern extraction

**Tech Stack:** Python, gitpython, YAML/JSON, LLM prompts

---

## File Structure

**New/Modified Files:**
- `skills/commit-extract/run.py` - Main skill implementation
- `skills/commit-extract/SKILL.md` - Skill documentation
- `skills/commit-semantic/run.py` - Main skill implementation
- `skills/commit-semantic/SKILL.md` - Skill documentation
- `tests/e2e/test_commit_extract.py` - E2E tests
- `tests/e2e/test_commit_semantic.py` - E2E tests

---

## Task 1: Update commit-extract Skill

**Files:**
- Modify: `skills/commit-extract/run.py`
- Test: `tests/e2e/test_commit_extract.py`

### Step 1: Write failing test

```python
def test_commit_extract_collects_by_month():
    """Test that commits are grouped by month."""
    from skills.commit_extract.run import CommitExtractRunner

    runner = CommitExtractRunner()
    # Should create month-based YAML files
    assert runner.STAGES == ["collect"]
```

### Step 2: Run test to verify it fails

```bash
pytest tests/e2e/test_commit_extract.py::test_commit_extract_collects_by_month -v
```
Expected: FAIL

### Step 3: Implement commit-extract collect stage

Update `skills/commit-extract/run.py`:
- Keep only `collect` stage
- Group commits by month (YYYY-MM)
- Output: `data/commit-extract/YYYY-MM.yaml`
- Include: commit_id, timestamp, author, commit_message, files, diff_chunks

### Step 4: Run test to verify it passes

```bash
pytest tests/e2e/test_commit_extract.py::test_commit_extract_collects_by_month -v
```
Expected: PASS

### Step 5: Commit

```bash
git add skills/commit-extract/run.py tests/e2e/test_commit_extract.py
git commit -m "feat: implement commit-extract collect stage"
```

---

## Task 2: Implement commit-semantic Classification

**Files:**
- Create: `tests/e2e/test_commit_semantic.py`
- Modify: `skills/commit-semantic/run.py`

### Step 1: Write failing test

```python
def test_classify_commit_type():
    """Test commit classification by prefix."""
    from skills.commit_semantic.run import CommitSemanticRunner

    runner = CommitSemanticRunner()

    assert runner._classify_type("feat: add parser") == "functional"
    assert runner._classify_type("bugfix: fix parser") == "functional"
    assert runner._classify_type("refactor: cleanup") == "non-functional"
    assert runner._classify_type("test: add tests") == "non-functional"
```

### Step 2: Run test to verify it fails

```bash
pytest tests/e2e/test_commit_semantic.py::test_classify_commit_type -v
```
Expected: FAIL

### Step 3: Implement classification

In `skills/commit-semantic/run.py`:
```python
def _classify_type(self, commit_message: str) -> str:
    """Classify commit by prefix."""
    prefix = commit_message.split(':')[0].lower()

    functional = ['feat', 'bugfix', 'optimize']
    if any(f in prefix for f in functional):
        return 'functional'

    # refactor+bugfix etc
    if '+' in prefix:
        return 'functional'

    return 'non-functional'
```

### Step 4: Run test to verify it passes

```bash
pytest tests/e2e/test_commit_semantic.py::test_classify_commit_type -v
```
Expected: PASS

### Step 5: Commit

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: implement commit classification by type"
```

---

## Task 3: Implement commit-semantic Split Stage

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: Update `tests/e2e/test_commit_semantic.py`

### Step 1: Write failing test

```python
def test_split_commits_by_module():
    """Test that commits are split by module."""
    from skills.commit_semantic.run import CommitSemanticRunner

    runner = CommitSemanticRunner()
    # After split stage, should have units grouped by module
    assert runner.STAGES[0] == "split"
```

### Step 2: Run test to verify it fails

```bash
pytest tests/e2e/test_commit_semantic.py::test_split_commits_by_module -v
```
Expected: FAIL

### Step 3: Implement split stage

In `skills/commit-semantic/run.py`:
- Parse commit_message to detect module
- Split multi-module commits into units
- Save to `data/commit-semantic/units/all.yaml`

```python
def _run_split(self, state):
    """Split commits by module."""
    # Load commit-extract output
    # Parse each commit for module keywords
    # Split multi-module commits
    # Save units
```

### Step 4: Run test to verify it passes

```bash
pytest tests/e2e/test_commit_semantic.py::test_split_commits_by_module -v
```
Expected: PASS

### Step 5: Commit

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: implement commit-semantic split stage"
```

---

## Task 4: Implement commit-semantic Analyze & Score

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: Update `tests/e2e/test_commit_semantic.py`

### Step 1: Write failing test

```python
def test_score_functional_commits():
    """Test that functional commits are scored."""
    from skills.commit_semantic.run import CommitSemanticRunner

    runner = CommitSemanticRunner()
    # After analyze, functional commits should have scores
    # Non-functional should not be scored
```

### Step 2: Run test to verify it fails

```bash
pytest tests/e2e/test_commit_semantic.py::test_score_functional_commits -v
```
Expected: FAIL

### Step 3: Implement analyze stage with LLM scoring

In `skills/commit-semantic/run.py`:
```python
def _run_analyze(self, state):
    """Analyze units with LLM scoring."""
    # Load units
    # For each functional unit:
    #   - LLM score: clarity, domain, reusability
    #   - Score 0-10
    # Save to functional/{high,medium,low}/
    # Save non-functional to non-functional/all/
```

### Step 4: Run test to verify it passes

```bash
pytest tests/e2e/test_commit_semantic.py::test_score_functional_commits -v
```
Expected: PASS

### Step 5: Commit

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: implement commit-semantic analyze and scoring"
```

---

## Task 5: Implement commit-semantic Aggregate & Distill

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: Update `tests/e2e/test_commit_semantic.py`

### Step 1: Write failing test

```python
def test_extract_canonical_patterns():
    """Test that high-scored commits produce canonical patterns."""
    from skills.commit_semantic.run import CommitSemanticRunner

    runner = CommitSemanticRunner()
    # After aggregate/distill, should have patterns/
```

### Step 2: Run test to verify it fails

```bash
pytest tests/e2e/test_commit_semantic.py::test_extract_canonical_patterns -v
```
Expected: FAIL

### Step 3: Implement aggregate and distill stages

In `skills/commit-semantic/run.py`:
```python
def _run_aggregate(self, state):
    """Aggregate by module, extract patterns."""
    # Group high-scored commits by module
    # Extract common patterns
    # Save to patterns/{module}.yaml

def _run_distill(self, state):
    """Extract canonical demands from high-scored."""
    # Top-N high-scored commits
    # LLM extract canonical demand descriptions
    # Save to patterns/canonical.yaml
```

### Step 4: Run test to verify it passes

```bash
pytest tests/e2e/test_commit_semantic.py::test_extract_canonical_patterns -v
```
Expected: PASS

### Step 5: Commit

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: implement commit-semantic aggregate and distill"
```

---

## Task 6: Update Skill Documentation

**Files:**
- Modify: `skills/commit-extract/SKILL.md`
- Modify: `skills/commit-semantic/SKILL.md`

### Step 1: Update commit-extract/SKILL.md

```markdown
---
name: commit-extract
description: Aggregate raw commits by month
---

# Commit Extract

Aggregate CC-generated commits by month.

## Usage

```
/commit-extract run              # Full pipeline
/commit-extract status           # Check state
/commit-extract step             # Run next stage
/commit-extract resume           # Continue from checkpoint
```

## Output

- `data/commit-extract/YYYY-MM.yaml` - Monthly commit data

## Stage

1. **collect** - Group commits by month
```

### Step 2: Update commit-semantic/SKILL.md

```markdown
---
name: commit-semantic
description: Cross-commit semantic analysis and pattern extraction
---

# Commit Semantic

Analyze commits, score functional changes, extract canonical patterns.

## Usage

```
/commit-semantic run              # Full pipeline
/commit-semantic status           # Check state
/commit-semantic step             # Run next stage
/commit-semantic resume           # Continue from checkpoint
```

## Stages

1. **split** - Parse commits by module
2. **analyze** - LLM scoring (functional only)
3. **aggregate** - Group by module
4. **distill** - Extract canonical demands

## Classification

- `functional`: feat, bugfix, optimize, refactor+bugfix
- `non-functional`: refactor, test, config, cleanup
```

### Step 3: Commit

```bash
git add skills/commit-extract/SKILL.md skills/commit-semantic/SKILL.md
git commit -m "docs: update skill documentation"
```

---

## Task 7: Run Full E2E Test

### Step 1: Create test repo with sample commits

```python
# In test, create temp git repo with sample commits
```

### Step 2: Run commit-extract

```bash
python -m skills.commit_extract.run --repo /tmp/test-repo
```

### Step 3: Run commit-semantic

```bash
python -m skills.commit_semantic.run
```

### Step 4: Verify output structure

```bash
ls data/commit-extract/
ls data/commit-semantic/
```

Expected:
- `data/commit-extract/YYYY-MM.yaml` exists
- `data/commit-semantic/functional/{high,medium,low}/` exists
- `data/commit-semantic/patterns/` exists

### Step 5: Commit

```bash
git add tests/
git commit -m "test: add full e2e test suite"
```

---

## Completion

All tasks complete. Skills ready for use.
