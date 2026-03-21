# Skill Consolidation Design — 2026-03-21

## Status

Draft — pending user approval.

## Problem

The harness exposes **19 skill commands**, creating cognitive overhead and fragmented execution. Capabilities 1-5 are each broken into 3-7 separate commands. Users must know which command to invoke for each stage.

## Goal

Consolidate to **5 top-level skill commands** that each:
1. Accept a natural language intent (run / status / step / resume)
2. Report structured JSON state + brief natural language summary
3. Support step-by-step execution with breakpoints

## Target Command Surface

| Command | Domain | Intent |
|---------|--------|--------|
| `/semantic-fact` | Repo structure | discover → review → refine → baseline |
| `/semantic` | Domain extraction | signals → candidates → recommend → review → finalize |
| `/demand` | Requirement mapping | normalize → map → match → build → validate |
| `/commit-extract` | Commit log extraction | collect → extract rules/invariants → pattern |
| `/commit-semantic` | Commit semantic analysis | analyze patterns → domain mapping → demand feed |

### Intent Routing (within each skill)

Each skill responds to natural language intent via `triggers` in `SKILL.md`:

```
"run", "execute", "pipeline"  → run full pipeline
"status", "check"             → report state (JSON + summary)
"reset"                       → reset working state
"step", "next"                → run next stage only
"resume"                      → resume from breakpoint
```

## Output Structure

```
docs/
  fact/          # semantic-fact output
    schemas/
    discovery/
    review/
    baseline/
  semantic/      # /semantic output
    signals/
    candidates/
    recommendations/
    review-decisions/
    finalized/
  demand/        # /demand output
    cards/
  commit-extract/ # /commit-extract output
    commits/
    rules/
    invariants/
  commit-semantic/ # /commit-semantic output
    patterns/
    domains/
```

Single source of truth per capability. No duplicate storage.

## State Reporting Format

### JSON (written to `run-state.json`)

```json
{
  "command": "semantic",
  "status": "breakpoint",
  "current_stage": "review",
  "completed_stages": ["signals", "candidates", "recommend"],
  "artifacts_written": ["signals.yaml", "candidates.yaml"],
  "resume_token": "step4_review",
  "breakpoint_reason": "architect review required",
  "timestamp": "2026-03-21T..."
}
```

### Natural Language Summary

Printed to stdout:

```
[semantic] Breakpoint at stage 4/5 (review).
Done: signals ✓, candidates ✓, recommend ✓
Next: /semantic review
```

### Status Command Output

```
/semantic status → "Semantic pipeline: breakpoint at review (stage 4/5). 3 artifacts written. Run /semantic step to continue."
```

## Step-by-Step Execution

Each skill maintains `run-state.json` in its output directory.

- `step` / `next` → run only the next uncompleted stage, set breakpoint
- `resume` → continue from current breakpoint
- `run` / `pipeline` → run all remaining stages

### Breakpoint Triggers

- Manual: user says "stop", "pause", "breakpoint"
- Automatic: stage requires human input (architect review, evidence check)
- Error: stage fails validation

## Command Mapping (Current → Consolidated)

| Current (19) | Consolidated (5) |
|---|---|
| semantic-fact-pipeline | /semantic-fact (run) |
| semantic-discover | /semantic-fact step |
| semantic-refine | /semantic-fact step |
| semantic-baseline | /semantic-fact step |
| semantic-init | /semantic-fact init |
| semantic-status | /semantic-fact status |
| semantic-reset | /semantic-fact reset |
| semantic-pipeline | /semantic (run) |
| semantic-signals | /semantic step |
| semantic-candidates | /semantic step |
| semantic-recommend | /semantic step |
| semantic-review | /semantic step |
| semantic-finalize | /semantic step |
| demand-pipeline | /demand (run) |
| semantic-extract | /commit-extract (run) |
| commit-semantic-pipeline | /commit-semantic (run) |
| commit-semantic-collect | /commit-extract step |
| commit-semantic-generate | /commit-semantic step |
| commit-semantic-export | /commit-semantic step |

**Deprecation**: Commands mapped above are NOT deleted — `SKILL.md` in each old skill directory adds a redirect note pointing to the new consolidated command.

## Skill Wrapper Pattern

Each consolidated skill follows this `run.py` structure:

```python
def main():
    args = parse_intent()  # reads natural language intent from argv
    intent = route_intent(args)

    if intent == "status":
        state = load_state(output_dir / "run-state.json")
        print(summary(state))
        write_json(state, output_dir / "run-state.json")
    elif intent == "step":
        state = load_state(output_dir / "run-state.json")
        next_stage = get_next_stage(state)
        run_stage(next_stage, state)
        set_breakpoint(state)
        print(summary(state))
        write_json(state, output_dir / "run-state.json")
    elif intent == "run":
        # run all remaining stages
```

## State File Location

**Decision**: `.harness/` — hidden, at repo root, versioned with the repo.

```
.harness/
  state/
    semantic-fact/
      run-state.json
    semantic/
      run-state.json
    demand/
      run-state.json
    commit-extract/
      run-state.json
    commit-semantic/
      run-state.json
  outputs/
    semantic-fact/
    semantic/
    demand/
    commit-extract/
    commit-semantic/
```

**Rationale**:
- `.harness/` is hidden (`.` prefix) but versioned — state travels with the repo
- `state/` vs `outputs/` separation — state is machine-readable, outputs are human-readable artifacts
- Each capability is isolated — `demand` doesn't pollute `semantic` state
- No mixing with `docs/` — harness internals stay out of user-facing documentation

**No Claude Code session required**: state is filesystem-based. `/commit-extract status` reads `.harness/state/commit-extract/run-state.json` directly.

**Migration**: existing artifacts in `docs/<cap>/` stay where they are. New output goes to `.harness/outputs/<cap>/`. Old skills read from old paths until deprecated.

---

## Intent Routing

**Decision**: LLM classification via existing executor bridge.

```python
def route_intent(user_text: str) -> str:
    """Classify natural language intent using LLM."""
    prompt = f"""Classify this command intent: "{user_text}"

    Options: run, status, reset, step, resume

    Reply with only the intent word."""
    # Uses existing executor_bridge — no new dependencies
    result = executor(prompt)
    return result.strip().lower()
```

- Reuses existing `executor_bridge` (already in codebase)
- Minimal prompt — single-word classification is cheap
- No new infrastructure
- Fallback: keyword matching if LLM unavailable

## Deprecation Strategy

**Decision**: Old commands are **deleted** after migration.

- No redirect, no backward compatibility shims
- Phase 4 removes deprecated skill directories entirely
- Users see error → must migrate to new commands
- Cleaner codebase, no dead code

### Deprecation timeline

1. **Phase 1-3**: Old commands still exist but `SKILL.md` marks them as deprecated
2. **Phase 4**: Old commands deleted after one release cycle
3. `AGENTS.md` updated to only reference new commands

---

## Process & Phases

Each phase follows a **gate-based process**:

```
Design Approved
    ↓
Phase N: Implement
    ↓
E2E Verification (all scenarios pass)
    ↓
Regression Suite (existing tests pass)
    ↓
Phase N+1 or Done
```

### Phase 1: Commit-Extract + Commit-Semantic

**Goal**: Consolidate commit domain into 2 commands.

**Steps**:
1. Create `/commit-extract` skill (migrate `semantic-extract` logic)
2. Create `/commit-semantic` skill (migrate `commit-semantic-pipeline` logic, read from `/commit-extract` output)
3. Deprecate old `commit-semantic-*` skills with redirect note in SKILL.md
4. Create E2E test: `tests/e2e/test_commit_extraction.py`
5. Run full regression suite
6. Gate: E2E pass + 46 existing tests pass

### Phase 2: Semantic-Fact Consolidation

**Goal**: Consolidate fact domain into 1 command.

**Steps**:
1. Create `/semantic-fact` skill (wrap existing fact pipeline)
2. Deprecate old `semantic-fact-*` skills with redirect
3. E2E test: `tests/e2e/test_semantic_fact.py`
4. Regression suite
5. Gate: E2E pass + regression pass

### Phase 3: Semantic + Demand Consolidation

**Goal**: Ensure `/semantic` and `/demand` support full intent surface.

**Steps**:
1. Add intent routing to `/semantic` (status/step/resume)
2. Add status + step to `/demand`
3. E2E test: `tests/e2e/test_semantic_pipeline.py`, `tests/e2e/test_demand.py`
4. Regression suite
5. Gate: E2E pass + regression pass

### Phase 4: Cleanup

1. Remove deprecated skill directories
2. Update `AGENTS.md` command references
3. Final regression suite
4. Gate: all clear

---

## End-to-End Verification Strategy

### Test Structure

```
tests/e2e/
  conftest.py           # shared fixtures
  test_commit_extract.py
  test_commit_semantic.py
  test_semantic_fact.py
  test_semantic_pipeline.py
  test_demand.py
```

### Per-Skill E2E Test Scenarios

Each test file covers all 5 intents for its command:

| Intent | Test |
|--------|------|
| `run` | Full pipeline completes, artifacts written |
| `status` | Correct state reported, JSON written |
| `reset` | State cleared, artifacts remain |
| `step` | Only one stage runs, breakpoint set |
| `resume` | Continues from breakpoint correctly |

### Phase 1 E2E Tests (commit-extract + commit-semantic)

```python
# test_commit_extract.py

def test_extract_run_full_pipeline():
    """Run full extract: collect → extract → pattern"""
    result = run_skill("commit-extract", "run --repo-root .")
    assert result.status == "ok"
    assert (workspace / "commit-extract" / "rules").exists()
    assert (workspace / "commit-extract" / "invariants").exists()

def test_extract_status():
    """Status reports current stage and artifacts"""
    result = run_skill("commit-extract", "status")
    assert result.json["command"] == "commit-extract"
    assert "current_stage" in result.json
    assert result.summary_contains("stage")

def test_extract_step_and_breakpoint():
    """Single step runs and sets breakpoint"""
    result = run_skill("commit-extract", "step")
    assert result.status == "breakpoint"
    assert result.json["current_stage"] is not None
    result2 = run_skill("commit-extract", "status")
    assert "breakpoint" in result2.summary

def test_extract_resume():
    """Resume continues from breakpoint"""
    run_skill("commit-extract", "step")  # set breakpoint
    result = run_skill("commit-extract", "resume")
    assert result.status in ("ok", "breakpoint")

def test_extract_reset():
    """Reset clears state, keeps artifacts"""
    run_skill("commit-extract", "run")
    artifacts_before = list((workspace / "commit-extract").glob("**/*.yaml"))
    run_skill("commit-extract", "reset")
    state = load_json(workspace / "commit-extract" / "run-state.json")
    assert state["completed_stages"] == []
    assert list((workspace / "commit-extract").glob("**/*.yaml")) == artifacts_before
```

### Regression Strategy

1. **Existing test suite** must pass unchanged throughout all phases
2. **No breaking changes** to Python APIs (`src/` function signatures)
3. Old commands are deleted in Phase 4 — Phase 3 is the last gate where they still exist

### Verification Gate

Each phase gate requires:
- All E2E tests pass
- `pytest tests/test_*.py -q` passes (existing 46 tests)
- `ruff check src/` passes
- `mypy src/` passes (0 errors)
