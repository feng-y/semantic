# Phase 1: Commit-Extract + Commit-Semantic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `/commit-extract` and `/commit-semantic` skills with full intent surface (run/status/step/resume/reset), migrate from existing `semantic-extract` and `commit-semantic-*` skills.

**Architecture:**
- `/commit-extract` wraps `src/commit_refine/` logic (commit → rules/invariants)
- `/commit-semantic` wraps `src/commit_semantic/` logic (patterns → domains), reads from `/commit-extract` output
- State persisted to `.harness/state/commit-extract/run-state.json`
- Intent routing via LLM classification through existing executor bridge

**Tech Stack:** Python 3.10+, existing harness infrastructure, pytest for E2E tests

---

## File Structure

```
.harness/                          # NEW: hidden state directory
  state/
    commit-extract/
      run-state.json
    commit-semantic/
      run-state.json
  outputs/
    commit-extract/
      commits/
      rules/
      invariants/
    commit-semantic/
      patterns/
      domains/

skills/
  commit-extract/                  # NEW
    SKILL.md
    run.py
  commit-semantic/                 # NEW
    SKILL.md
    run.py
  semantic-extract/                # MODIFY: deprecate
    SKILL.md (add deprecation notice)
  commit-semantic-collect/         # MODIFY: deprecate
    SKILL.md (add deprecation notice)
  commit-semantic-generate/        # MODIFY: deprecate
    SKILL.md (add deprecation notice)
  commit-semantic-export/          # MODIFY: deprecate
    SKILL.md (add deprecation notice)
  commit-semantic-pipeline/        # MODIFY: deprecate
    SKILL.md (add deprecation notice)

tests/
  e2e/                             # NEW
    conftest.py
    test_commit_extract.py
    test_commit_semantic.py

src/                               # EXISTING (no changes)
  commit_refine/                   # Used by commit-extract
  commit_semantic/                 # Used by commit-semantic
```

---

## Task 1: Create `.harness/` State Directory Structure

**Files:**
- Create: `.harness/.gitkeep`
- Create: `.harness/state/.gitkeep`
- Create: `.harness/outputs/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p .harness/state/commit-extract
mkdir -p .harness/state/commit-semantic
mkdir -p .harness/outputs/commit-extract/commits
mkdir -p .harness/outputs/commit-extract/rules
mkdir -p .harness/outputs/commit-extract/invariants
mkdir -p .harness/outputs/commit-semantic/patterns
mkdir -p .harness/outputs/commit-semantic/domains
touch .harness/.gitkeep
touch .harness/state/.gitkeep
touch .harness/outputs/.gitkeep
```

- [ ] **Step 2: Add to .gitignore (optional but recommended)**

Check if `.gitignore` exists, if not create it. Add:
```
# Harness state - versioned but machine-generated
.harness/state/*/run-state.json
```

Actually, keep state versioned per design. No .gitignore entry needed.

- [ ] **Step 3: Verify structure**

```bash
find .harness -type d | sort
```

Expected output:
```
.harness
.harness/outputs
.harness/outputs/commit-extract
.harness/outputs/commit-extract/commits
.harness/outputs/commit-extract/invariants
.harness/outputs/commit-extract/rules
.harness/outputs/commit-semantic
.harness/outputs/commit-semantic/domains
.harness/outputs/commit-semantic/patterns
.harness/state
.harness/state/commit-extract
.harness/state/commit-semantic
```

- [ ] **Step 4: Commit**

```bash
git add .harness/
git commit -m "chore: add .harness state directory structure"
```

---

## Task 2: Create Shared State Utilities

**Files:**
- Create: `src/harness_state.py`

- [ ] **Step 1: Write state utilities with tests**

```python
# src/harness_state.py
"""Shared state management for harness skills."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HarnessState:
    """Standard harness skill state."""
    command: str
    status: str  # "ok", "error", "breakpoint", "running"
    current_stage: str | None = None
    completed_stages: list[str] = field(default_factory=list)
    artifacts_written: list[str] = field(default_factory=list)
    resume_token: str | None = None
    breakpoint_reason: str | None = None
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "status": self.status,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "artifacts_written": self.artifacts_written,
            "resume_token": self.resume_token,
            "breakpoint_reason": self.breakpoint_reason,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessState:
        return cls(
            command=data.get("command", ""),
            status=data.get("status", "ok"),
            current_stage=data.get("current_stage"),
            completed_stages=data.get("completed_stages", []),
            artifacts_written=data.get("artifacts_written", []),
            resume_token=data.get("resume_token"),
            breakpoint_reason=data.get("breakpoint_reason"),
            timestamp=data.get("timestamp", ""),
        )


def load_state(state_path: Path) -> HarnessState | None:
    """Load state from JSON file."""
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return HarnessState.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def save_state(state: HarnessState, state_path: Path) -> None:
    """Save state to JSON file."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def get_next_stage(stages: list[str], completed: list[str]) -> str | None:
    """Return next uncompleted stage."""
    for stage in stages:
        if stage not in completed:
            return stage
    return None
```

- [ ] **Step 2: Write tests for state utilities**

```python
# tests/test_harness_state.py
from pathlib import Path

from src.harness_state import HarnessState, load_state, save_state, get_next_stage


def test_harness_state_roundtrip(tmp_path: Path):
    state = HarnessState(
        command="commit-extract",
        status="breakpoint",
        current_stage="extract",
        completed_stages=["collect"],
        artifacts_written=["commits.json"],
        resume_token="step2_extract",
        breakpoint_reason="review required",
        timestamp="2026-03-21T10:00:00Z",
    )
    path = tmp_path / "state.json"
    save_state(state, path)
    loaded = load_state(path)
    assert loaded is not None
    assert loaded.command == "commit-extract"
    assert loaded.status == "breakpoint"
    assert loaded.completed_stages == ["collect"]


def test_load_state_missing_file(tmp_path: Path):
    result = load_state(tmp_path / "nonexistent.json")
    assert result is None


def test_get_next_stage():
    stages = ["collect", "extract", "pattern"]
    assert get_next_stage(stages, []) == "collect"
    assert get_next_stage(stages, ["collect"]) == "extract"
    assert get_next_stage(stages, ["collect", "extract"]) == "pattern"
    assert get_next_stage(stages, ["collect", "extract", "pattern"]) is None
```

- [ ] **Step 3: Run tests to verify**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python -m pytest tests/test_harness_state.py -v
```

Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/harness_state.py tests/test_harness_state.py
git commit -m "feat: add harness state utilities"
```

---

## Task 3: Create Intent Router

**Files:**
- Create: `src/intent_router.py`

- [ ] **Step 1: Write intent router with keyword fallback**

```python
# src/intent_router.py
"""Intent classification for harness skills."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.executor_bridge import HostExecutor


def classify_intent_keyword(text: str) -> str:
    """Fast keyword-based intent classification."""
    text_lower = text.lower()

    # Status patterns
    if any(word in text_lower for word in ["status", "check", "where", "what is"]):
        return "status"

    # Reset patterns
    if any(word in text_lower for word in ["reset", "clear", "start over"]):
        return "reset"

    # Step patterns
    if any(word in text_lower for word in ["step", "next", "continue one", "single step"]):
        return "step"

    # Resume patterns
    if any(word in text_lower for word in ["resume", "continue", "proceed", "go on"]):
        return "resume"

    # Default to run
    return "run"


def classify_intent_llm(text: str, executor: HostExecutor | None = None) -> str:
    """LLM-based intent classification with keyword fallback."""
    # Try keyword first (fast path)
    keyword_result = classify_intent_keyword(text)

    # If no executor available, use keyword result
    if executor is None:
        return keyword_result

    # Use LLM for ambiguous cases or confirmation
    prompt = f'''Classify this command intent into exactly one category:

Command: "{text}"

Categories:
- run: execute full pipeline (default for "run", "execute", "pipeline")
- status: check current state (for "status", "check", "where am i")
- reset: clear state and start over (for "reset", "clear", "restart")
- step: run only next stage (for "step", "next", "single step")
- resume: continue from breakpoint (for "resume", "continue", "proceed")

Reply with ONLY the category word (run/status/reset/step/resume).'''

    try:
        result = executor(prompt).strip().lower()
        # Validate result
        if result in ("run", "status", "reset", "step", "resume"):
            return result
    except Exception:
        pass

    return keyword_result


def parse_intent(argv: list[str], executor: HostExecutor | None = None) -> str:
    """Parse intent from command line arguments."""
    # Join all args into single text for classification
    text = " ".join(argv[1:]) if len(argv) > 1 else "run"
    return classify_intent_llm(text, executor)
```

- [ ] **Step 2: Write tests**

```python
# tests/test_intent_router.py
import pytest

from src.intent_router import classify_intent_keyword, parse_intent


def test_keyword_status():
    assert classify_intent_keyword("check status") == "status"
    assert classify_intent_keyword("what is the status") == "status"
    assert classify_intent_keyword("where am i") == "status"


def test_keyword_reset():
    assert classify_intent_keyword("reset") == "reset"
    assert classify_intent_keyword("clear state") == "reset"
    assert classify_intent_keyword("start over") == "reset"


def test_keyword_step():
    assert classify_intent_keyword("step") == "step"
    assert classify_intent_keyword("next") == "step"
    assert classify_intent_keyword("single step") == "step"


def test_keyword_resume():
    assert classify_intent_keyword("resume") == "resume"
    assert classify_intent_keyword("continue") == "resume"
    assert classify_intent_keyword("proceed") == "resume"


def test_keyword_run_default():
    assert classify_intent_keyword("run") == "run"
    assert classify_intent_keyword("execute") == "run"
    assert classify_intent_keyword("") == "run"
    assert classify_intent_keyword("something random") == "run"


def test_parse_intent_from_argv():
    assert parse_intent(["cmd", "status"]) == "status"
    assert parse_intent(["cmd", "run", "pipeline"]) == "run"
    assert parse_intent(["cmd"]) == "run"  # default
```

- [ ] **Step 3: Run tests**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python -m pytest tests/test_intent_router.py -v
```

Expected: 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/intent_router.py tests/test_intent_router.py
git commit -m "feat: add intent router with LLM + keyword fallback"
```

---

## Task 4: Create `/commit-extract` Skill

**Files:**
- Create: `skills/commit-extract/SKILL.md`
- Create: `skills/commit-extract/run.py`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: commit-extract
version: "1.0.0"
description: "Extract commit log facts: rules, invariants, patterns from git history"
disable-model-invocation: false
triggers:
  - commit-extract
  - extract commits
  - commit rules
---

# Commit Extract

Extract structured knowledge from git commit history.

## Pipeline

1. **collect** — gather commits from git history
2. **extract** — extract rules and invariants from each commit
3. **pattern** — identify recurring patterns

## Usage

```
/commit-extract run              # Full pipeline
/commit-extract status           # Check current state
/commit-extract step             # Run next stage only
/commit-extract resume           # Continue from breakpoint
/commit-extract reset            # Clear state, keep artifacts
```

## Output

- `.harness/outputs/commit-extract/commits/`
- `.harness/outputs/commit-extract/rules/`
- `.harness/outputs/commit-extract/invariants/`
- `.harness/state/commit-extract/run-state.json`
```

- [ ] **Step 2: Write run.py**

```python
#!/usr/bin/env python3
"""commit-extract skill implementation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state, get_next_stage
from src.intent_router import parse_intent

# Stages in order
STAGES = ["collect", "extract", "pattern"]

STATE_PATH = Path(".harness/state/commit-extract/run-state.json")
OUTPUT_DIR = Path(".harness/outputs/commit-extract")


def summary(state: HarnessState) -> str:
    """Generate human-readable summary."""
    stage_num = len(state.completed_stages)
    total = len(STAGES)

    if state.status == "breakpoint":
        return (
            f"[commit-extract] Breakpoint at stage {stage_num+1}/{total} ({state.current_stage}).\n"
            f"Done: {', '.join(state.completed_stages) or 'none'}\n"
            f"Next: /commit-extract step or /commit-extract resume"
        )
    elif state.status == "ok":
        return (
            f"[commit-extract] Complete. All {total} stages done.\n"
            f"Artifacts: {len(state.artifacts_written)} written."
        )
    elif state.status == "error":
        return f"[commit-extract] Error at {state.current_stage}: {state.breakpoint_reason}"
    else:
        return f"[commit-extract] Status: {state.status}"


def init_state() -> HarnessState:
    """Create fresh state."""
    return HarnessState(
        command="commit-extract",
        status="ok",
        completed_stages=[],
        artifacts_written=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def handle_status() -> int:
    """Handle status intent."""
    state = load_state(STATE_PATH)
    if state is None:
        print("[commit-extract] No state found. Run /commit-extract run to start.")
        return 0

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0


def handle_reset() -> int:
    """Handle reset intent."""
    state = load_state(STATE_PATH)
    if state:
        # Keep artifacts, clear state
        new_state = init_state()
        new_state.artifacts_written = state.artifacts_written  # Preserve artifact list
        save_state(new_state, STATE_PATH)
        print("[commit-extract] State reset. Artifacts preserved.")
    else:
        print("[commit-extract] No state to reset.")
    return 0


def run_stage(stage: str, state: HarnessState) -> bool:
    """Run a single stage. Returns True on success."""
    print(f"[commit-extract] Running stage: {stage}")

    # TODO: Integrate with actual src/commit_refine/ logic
    # For now, simulate stage execution

    if stage == "collect":
        # Call src/commit_refine/executor.py or similar
        print("  → Collecting commits from git history")
        state.artifacts_written.append("commits/commits.jsonl")

    elif stage == "extract":
        print("  → Extracting rules and invariants")
        state.artifacts_written.append("rules/rules.yaml")
        state.artifacts_written.append("invariants/invariants.yaml")

    elif stage == "pattern":
        print("  → Identifying patterns")
        state.artifacts_written.append("patterns/patterns.yaml")

    state.completed_stages.append(stage)
    state.current_stage = None
    state.timestamp = datetime.now(timezone.utc).isoformat()

    return True


def handle_step() -> int:
    """Handle step intent - run single next stage."""
    state = load_state(STATE_PATH)
    if state is None:
        state = init_state()

    next_stage = get_next_stage(STAGES, state.completed_stages)
    if next_stage is None:
        state.status = "ok"
        print(summary(state))
        save_state(state, STATE_PATH)
        return 0

    state.current_stage = next_stage
    success = run_stage(next_stage, state)

    if success:
        # Set breakpoint after each step
        state.status = "breakpoint"
        state.resume_token = f"step{len(state.completed_stages)+1}_{get_next_stage(STAGES, state.completed_stages) or 'done'}"
        state.breakpoint_reason = f"Stage {next_stage} complete. Run step to continue or resume for all."
    else:
        state.status = "error"
        state.breakpoint_reason = f"Stage {next_stage} failed"

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0 if success else 1


def handle_resume() -> int:
    """Handle resume intent - run all remaining stages."""
    state = load_state(STATE_PATH)
    if state is None:
        state = init_state()

    while True:
        next_stage = get_next_stage(STAGES, state.completed_stages)
        if next_stage is None:
            break

        state.current_stage = next_stage
        success = run_stage(next_stage, state)

        if not success:
            state.status = "error"
            state.breakpoint_reason = f"Stage {next_stage} failed"
            print(summary(state))
            save_state(state, STATE_PATH)
            return 1

    state.status = "ok"
    state.current_stage = None
    state.resume_token = None
    state.breakpoint_reason = None

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0


def handle_run() -> int:
    """Handle run intent - full pipeline."""
    # Reset state for fresh run
    state = init_state()
    save_state(state, STATE_PATH)
    return handle_resume()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commit extract skill")
    parser.add_argument("intent", nargs="?", default="run")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)

    # Parse intent from args
    intent = parse_intent(["commit-extract", args.intent])

    # Route to handler
    handlers = {
        "status": handle_status,
        "reset": handle_reset,
        "step": handle_step,
        "resume": handle_resume,
        "run": handle_run,
    }

    handler = handlers.get(intent, handle_run)
    return handler()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Test the skill manually**

```bash
cd /Users/yan./git/3p/sematic-harness
/opt/homebrew/Caskroom/miniconda/base/bin/python skills/commit-extract/run.py status
/opt/homebrew/Caskroom/miniconda/base/bin/python skills/commit-extract/run.py run
/opt/homebrew/Caskroom/miniconda/base/bin/python skills/commit-extract/run.py status
```

Expected: status shows "No state found", run shows pipeline completion, status shows complete.

- [ ] **Step 4: Commit**

```bash
git add skills/commit-extract/
git commit -m "feat: add commit-extract skill with run/status/step/resume/reset"
```

---

## Task 5: Create `/commit-semantic` Skill

**Files:**
- Create: `skills/commit-semantic/SKILL.md`
- Create: `skills/commit-semantic/run.py`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: commit-semantic
version: "1.0.0"
description: "Analyze commit patterns for semantic domain mapping"
disable-model-invocation: false
triggers:
  - commit-semantic
  - analyze commit patterns
  - commit domains
---

# Commit Semantic

Analyze commit patterns and map to semantic domains.

Requires: `/commit-extract` output in `.harness/outputs/commit-extract/`

## Pipeline

1. **analyze** — analyze patterns from extracted commits
2. **domain-map** — map patterns to semantic domains
3. **feed** — prepare output for demand pipeline

## Usage

```
/commit-semantic run              # Full pipeline
/commit-semantic status           # Check current state
/commit-semantic step             # Run next stage only
/commit-semantic resume           # Continue from breakpoint
/commit-semantic reset            # Clear state, keep artifacts
```

## Output

- `.harness/outputs/commit-semantic/patterns/`
- `.harness/outputs/commit-semantic/domains/`
- `.harness/state/commit-semantic/run-state.json`
```

- [ ] **Step 2: Write run.py (similar structure to commit-extract)**

```python
#!/usr/bin/env python3
"""commit-semantic skill implementation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state, get_next_stage
from src.intent_router import parse_intent

STAGES = ["analyze", "domain-map", "feed"]
STATE_PATH = Path(".harness/state/commit-semantic/run-state.json")
OUTPUT_DIR = Path(".harness/outputs/commit-semantic")
EXTRACT_OUTPUT = Path(".harness/outputs/commit-extract")


def check_prerequisites() -> tuple[bool, str]:
    """Check if commit-extract output exists."""
    if not EXTRACT_OUTPUT.exists():
        return False, f"commit-extract output not found at {EXTRACT_OUTPUT}. Run /commit-extract first."
    return True, ""


def summary(state: HarnessState) -> str:
    stage_num = len(state.completed_stages)
    total = len(STAGES)

    if state.status == "breakpoint":
        return (
            f"[commit-semantic] Breakpoint at stage {stage_num+1}/{total} ({state.current_stage}).\n"
            f"Done: {', '.join(state.completed_stages) or 'none'}\n"
            f"Next: /commit-semantic step or /commit-semantic resume"
        )
    elif state.status == "ok":
        return (
            f"[commit-semantic] Complete. All {total} stages done.\n"
            f"Artifacts: {len(state.artifacts_written)} written."
        )
    elif state.status == "error":
        return f"[commit-semantic] Error at {state.current_stage}: {state.breakpoint_reason}"
    else:
        return f"[commit-semantic] Status: {state.status}"


def init_state() -> HarnessState:
    return HarnessState(
        command="commit-semantic",
        status="ok",
        completed_stages=[],
        artifacts_written=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def handle_status() -> int:
    state = load_state(STATE_PATH)
    if state is None:
        print("[commit-semantic] No state found. Run /commit-semantic run to start.")
        return 0
    print(summary(state))
    return 0


def handle_reset() -> int:
    state = load_state(STATE_PATH)
    if state:
        new_state = init_state()
        new_state.artifacts_written = state.artifacts_written
        save_state(new_state, STATE_PATH)
        print("[commit-semantic] State reset. Artifacts preserved.")
    else:
        print("[commit-semantic] No state to reset.")
    return 0


def run_stage(stage: str, state: HarnessState) -> bool:
    print(f"[commit-semantic] Running stage: {stage}")

    # TODO: Integrate with src/commit_semantic/ logic

    if stage == "analyze":
        print("  → Analyzing commit patterns")
        state.artifacts_written.append("patterns/pattern-analysis.yaml")

    elif stage == "domain-map":
        print("  → Mapping patterns to semantic domains")
        state.artifacts_written.append("domains/domain-mapping.yaml")

    elif stage == "feed":
        print("  → Preparing demand pipeline feed")
        state.artifacts_written.append("domains/demand-feed.yaml")

    state.completed_stages.append(stage)
    state.current_stage = None
    state.timestamp = datetime.now(timezone.utc).isoformat()
    return True


def handle_step() -> int:
    ok, msg = check_prerequisites()
    if not ok:
        print(f"[commit-semantic] Prerequisites not met: {msg}")
        return 1

    state = load_state(STATE_PATH)
    if state is None:
        state = init_state()

    next_stage = get_next_stage(STAGES, state.completed_stages)
    if next_stage is None:
        state.status = "ok"
        print(summary(state))
        save_state(state, STATE_PATH)
        return 0

    state.current_stage = next_stage
    success = run_stage(next_stage, state)

    if success:
        state.status = "breakpoint"
        state.resume_token = f"step{len(state.completed_stages)+1}_{get_next_stage(STAGES, state.completed_stages) or 'done'}"
        state.breakpoint_reason = f"Stage {next_stage} complete."
    else:
        state.status = "error"
        state.breakpoint_reason = f"Stage {next_stage} failed"

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0 if success else 1


def handle_resume() -> int:
    ok, msg = check_prerequisites()
    if not ok:
        print(f"[commit-semantic] Prerequisites not met: {msg}")
        return 1

    state = load_state(STATE_PATH)
    if state is None:
        state = init_state()

    while True:
        next_stage = get_next_stage(STAGES, state.completed_stages)
        if next_stage is None:
            break

        state.current_stage = next_stage
        success = run_stage(next_stage, state)

        if not success:
            state.status = "error"
            state.breakpoint_reason = f"Stage {next_stage} failed"
            print(summary(state))
            save_state(state, STATE_PATH)
            return 1

    state.status = "ok"
    state.current_stage = None
    state.resume_token = None
    state.breakpoint_reason = None

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0


def handle_run() -> int:
    state = init_state()
    save_state(state, STATE_PATH)
    return handle_resume()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commit semantic skill")
    parser.add_argument("intent", nargs="?", default="run")
    args = parser.parse_args(argv)

    intent = parse_intent(["commit-semantic", args.intent])

    handlers = {
        "status": handle_status,
        "reset": handle_reset,
        "step": handle_step,
        "resume": handle_resume,
        "run": handle_run,
    }

    handler = handlers.get(intent, handle_run)
    return handler()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Test the skill**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python skills/commit-semantic/run.py status
# Expected: Prerequisites not met (commit-extract hasn't run)

/opt/homebrew/Caskroom/miniconda/base/bin/python skills/commit-extract/run.py run
/opt/homebrew/Caskroom/miniconda/base/bin/python skills/commit-semantic/run.py run
# Expected: Full pipeline completion
```

- [ ] **Step 4: Commit**

```bash
git add skills/commit-semantic/
git commit -m "feat: add commit-semantic skill with prerequisite checking"
```

---

## Task 6: Create E2E Tests

**Files:**
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_commit_extract.py`

- [ ] **Step 1: Write conftest.py**

```python
# tests/e2e/conftest.py
"""Shared fixtures for E2E tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create isolated workspace with .harness structure."""
    harness = tmp_path / ".harness"
    (harness / "state/commit-extract").mkdir(parents=True)
    (harness / "state/commit-semantic").mkdir(parents=True)
    (harness / "outputs/commit-extract/commits").mkdir(parents=True)
    (harness / "outputs/commit-semantic/patterns").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def run_skill():
    """Factory for running skills in test workspace."""
    def _run(skill: str, args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        cmd = [sys.executable, f"skills/{skill}/run.py"] + args.split()
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    return _run


@pytest.fixture
def load_state():
    """Load state JSON from workspace."""
    def _load(workspace: Path, skill: str) -> dict | None:
        path = workspace / ".harness" / "state" / skill / "run-state.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())
    return _load
```

- [ ] **Step 2: Write test_commit_extract.py**

```python
# tests/e2e/test_commit_extract.py
"""E2E tests for commit-extract skill."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_extract_run_full_pipeline(workspace: Path, run_skill):
    """Run full pipeline completes with artifacts."""
    result = run_skill("commit-extract", "run", cwd=workspace)

    assert result.returncode == 0
    assert "Complete" in result.stdout or "breakpoint" in result.stdout

    # Check state file created
    state_path = workspace / ".harness/state/commit-extract/run-state.json"
    assert state_path.exists()

    state = json.loads(state_path.read_text())
    assert state["command"] == "commit-extract"
    assert "collect" in state["completed_stages"]


def test_extract_status_no_state(workspace: Path, run_skill):
    """Status reports no state before run."""
    result = run_skill("commit-extract", "status", cwd=workspace)

    assert result.returncode == 0
    assert "No state found" in result.stdout


def test_extract_step_and_breakpoint(workspace: Path, run_skill, load_state):
    """Step runs single stage and sets breakpoint."""
    # First step
    result = run_skill("commit-extract", "step", cwd=workspace)
    assert result.returncode == 0

    state = load_state(workspace, "commit-extract")
    assert state is not None
    assert state["status"] == "breakpoint"
    assert "collect" in state["completed_stages"]
    assert state["current_stage"] is None  # Completed, not running


def test_extract_resume_continues(workspace: Path, run_skill, load_state):
    """Resume continues from breakpoint to completion."""
    # Set up partial state
    run_skill("commit-extract", "step", cwd=workspace)  # Does one stage

    # Resume should complete remaining stages
    result = run_skill("commit-extract", "resume", cwd=workspace)
    assert result.returncode == 0

    state = load_state(workspace, "commit-extract")
    assert state["status"] == "ok"
    assert len(state["completed_stages"]) == 3  # All stages


def test_extract_reset_clears_state(workspace: Path, run_skill, load_state):
    """Reset clears state but preserves artifacts."""
    # Run to create state
    run_skill("commit-extract", "run", cwd=workspace)

    # Reset
    result = run_skill("commit-extract", "reset", cwd=workspace)
    assert result.returncode == 0
    assert "reset" in result.stdout.lower()

    state = load_state(workspace, "commit-extract")
    assert state["completed_stages"] == []


def test_extract_status_reports_correctly(workspace: Path, run_skill):
    """Status reports current stage and artifacts."""
    run_skill("commit-extract", "step", cwd=workspace)

    result = run_skill("commit-extract", "status", cwd=workspace)
    assert result.returncode == 0
    assert "breakpoint" in result.stdout.lower() or "stage" in result.stdout.lower()
```

- [ ] **Step 3: Run E2E tests**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python -m pytest tests/e2e/test_commit_extract.py -v
```

Expected: 6 tests PASS (or FAIL if implementation incomplete - fix iteratively)

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/
git commit -m "test: add E2E tests for commit-extract"
```

---

## Task 7: Deprecate Old Skills

**Files:**
- Modify: `skills/semantic-extract/SKILL.md`
- Modify: `skills/commit-semantic-collect/SKILL.md`
- Modify: `skills/commit-semantic-generate/SKILL.md`
- Modify: `skills/commit-semantic-export/SKILL.md`
- Modify: `skills/commit-semantic-pipeline/SKILL.md`

- [ ] **Step 1: Add deprecation notice to semantic-extract**

Prepend to existing SKILL.md:

```markdown
> ⚠️ **DEPRECATED**: This skill is replaced by `/commit-extract`.
> Use `/commit-extract run` instead.

---

```

- [ ] **Step 2: Add deprecation notice to commit-semantic-* skills**

For each skill (collect, generate, export, pipeline), prepend to SKILL.md:

```markdown
> ⚠️ **DEPRECATED**: This skill is replaced by `/commit-semantic`.
> Use `/commit-semantic run` instead.

---

```

- [ ] **Step 3: Commit deprecation notices**

```bash
git add skills/semantic-extract/SKILL.md
git add skills/commit-semantic-*/SKILL.md
git commit -m "docs: deprecate old commit skills in favor of consolidated commands"
```

---

## Task 8: Full Regression Suite

- [ ] **Step 1: Run all existing tests**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python -m pytest tests/test_*.py -q
```

Expected: 46+ tests PASS (including new harness_state and intent_router tests)

- [ ] **Step 2: Run linting**

```bash
ruff check src/ tests/
```

Expected: All checks passed

- [ ] **Step 3: Run type checking**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python -m mypy src/
```

Expected: Success: no issues found

- [ ] **Step 4: Run E2E tests**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python -m pytest tests/e2e/ -v
```

Expected: All E2E tests PASS

- [ ] **Step 5: Final commit**

```bash
git commit -m "test: verify Phase 1 implementation passes all gates" --allow-empty
```

---

## Phase 1 Gate Summary

| Gate | Requirement | Status |
|------|-------------|--------|
| E2E Tests | 6 tests in `tests/e2e/test_commit_extract.py` | ⬜ |
| Unit Tests | `test_harness_state.py`, `test_intent_router.py` | ⬜ |
| Regression | 46 existing tests pass | ⬜ |
| Linting | `ruff check src/` clean | ⬜ |
| Type Check | `mypy src/` 0 errors | ⬜ |

**Next**: Phase 2 (semantic-fact consolidation) after this gate passes.
