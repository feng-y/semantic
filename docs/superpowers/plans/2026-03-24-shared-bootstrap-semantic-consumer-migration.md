# Shared Bootstrap Semantic Consumer Migration Implementation Plan

**Goal:** Migrate `commit-semantic` from being the temporary producer of shared repo context toward being a consumer of the shared `data/commit-extract/repo-context.json` artifact, while preserving compatibility during cutover.

**Architecture:** This subproject is a consumer-first migration. `commit-semantic` should prefer the shared context emitted by `commit-extract`, keep the existing local context stage only as a transitional compatibility path, and make that precedence explicit in code, tests, and docs. It does not remove the old producer path yet, and it does not add reliability-layer behavior such as freshness checks or fallback policy.

**Tech Stack:** Python 3.10+, pytest, JSON artifact IO, existing `SkillRunner` / `HarnessState` / `HostExecutor` patterns.

---

## File Structure

### Files to modify
- `skills/commit-semantic/run.py`
  - Add explicit read-path precedence for shared context from `data/commit-extract/repo-context.json`
  - Keep local `data/commit-semantic/repo-context.json` producer path as compatibility-only fallback
  - Ensure downstream capability synthesis consumes the selected semantic context deterministically
- `skills/commit-semantic/SKILL.md`
  - Document the new precedence rule and the transitional compatibility posture
- `tests/e2e/test_commit_semantic.py`
  - Add/adjust tests for shared-context preference and fallback behavior
- `tests/e2e/test_pipeline_e2e.py`
  - Add/adjust assertions that the shared context path is consumed when available

### Files to create
- `tests/fixtures/commit_semantic_consumer/shared_extract_repo_context.json`
  - Fixture representing a shared producer artifact coming from `commit-extract`
- `tests/test_commit_semantic_context_resolution.py`
  - Focused tests for context-source resolution and precedence

### Files to inspect while implementing
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-context-contract.md`
  - Source of truth for contract shape
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-extract-producer.md`
  - Source of truth for producer-side artifact location and behavior
- `skills/commit-extract/bootstrap.py`
  - Current producer implementation shape
- `tests/test_shared_repo_context_contract.py`
  - Contract compliance expectations

### Explicitly out of scope in this subproject
- Removing `commit-semantic`’s context stage entirely
- Freshness / staleness checks
- Adaptive fallback / bypass
- Health summary behavior beyond reading already-produced shared context
- Prompt injection changes in `commit-extract`
- Eval fixtures

---

## Consumer Resolution Rules

### Canonical read order
`commit-semantic` must resolve repo context in this order:

1. `data/commit-extract/repo-context.json` (shared producer artifact) — **preferred**
2. `data/commit-semantic/repo-context.json` (local compatibility artifact) — fallback
3. legacy flat payload behavior — final compatibility fallback only if needed inside loaders

### Behavioral contract for this subproject
- If shared context exists and is valid, `commit-semantic` consumes it.
- If shared context is absent, `commit-semantic` may continue to use its local context-stage output.
- If both exist, shared context wins.
- This subproject does **not** yet remove local generation.
- This subproject does **not** introduce freshness-based arbitration. Existence + validity only.

### Semantic consumer rule
Downstream prompt building in `commit-semantic` should consume only the selected `semantic_context` view, not the full layered object.

---

## Task 1: Add consumer-resolution fixtures and focused tests first

**Files:**
- Create: `tests/fixtures/commit_semantic_consumer/shared_extract_repo_context.json`
- Create: `tests/test_commit_semantic_context_resolution.py`

- [ ] **Step 1: Create shared-context fixture**

Write `tests/fixtures/commit_semantic_consumer/shared_extract_repo_context.json` as a valid layered repo-context artifact shaped like the producer output from Subproject 2.

Include:
- non-empty `shared_hints`
- non-empty `semantic_context.local_capabilities`
- valid `summary`

- [ ] **Step 2: Write failing precedence tests**

In `tests/test_commit_semantic_context_resolution.py`, add tests for a resolution helper or loader path such as:

```python
def test_load_repo_context_prefers_shared_extract_artifact(tmp_path):
    ...

def test_load_repo_context_falls_back_to_local_semantic_artifact(tmp_path):
    ...

def test_load_repo_context_returns_empty_when_no_artifacts_exist(tmp_path):
    ...
```

Assert:
- shared extract artifact wins when both exist
- local semantic artifact is used when shared extract artifact is absent
- no artifact returns `{}` or equivalent current empty behavior

- [ ] **Step 3: Write failing tests for semantic-context extraction**

Add tests asserting the consumer path extracts only `semantic_context` from the layered artifact.

Example target behavior:

```python
assert resolved_context == payload["semantic_context"]
```

- [ ] **Step 4: Run tests to verify failure**

Run:
```bash
pytest tests/test_commit_semantic_context_resolution.py -v
```

Expected: FAIL because explicit shared-vs-local resolution logic does not exist yet.

---

## Task 2: Implement shared-context resolution in `commit-semantic`

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: `tests/test_commit_semantic_context_resolution.py`

- [ ] **Step 1: Add explicit shared-context path helpers**

Add helper path functions such as:

```python
def _shared_repo_context_file() -> Path:
    return EXTRACT_OUTPUT / "repo-context.json"


def _local_repo_context_file() -> Path:
    return SEMANTIC_OUTPUT / "repo-context.json"
```

Keep `_repo_context_file()` only if needed for temporary compatibility, or rename clearly to reduce ambiguity.

- [ ] **Step 2: Implement deterministic read precedence**

Update `_load_repo_context()` so it:
- reads shared extract artifact first if present and valid
- falls back to local semantic artifact if shared one is absent
- returns only `semantic_context` from the layered object
- falls back to legacy flat payload only when needed for compatibility

Do not add staleness or conflict logic yet.

- [ ] **Step 3: Run focused tests**

Run:
```bash
pytest tests/test_commit_semantic_context_resolution.py -v
```

Expected: PASS

- [ ] **Step 4: Commit (optional checkpoint)**

```bash
git add skills/commit-semantic/run.py tests/test_commit_semantic_context_resolution.py tests/fixtures/commit_semantic_consumer/shared_extract_repo_context.json
git commit -m "feat: prefer shared extract repo context in commit-semantic"
```

---

## Task 3: Update `commit-semantic` e2e coverage for shared-context consumption

**Files:**
- Modify: `tests/e2e/test_commit_semantic.py`
- Modify: `tests/e2e/test_pipeline_e2e.py`

- [ ] **Step 1: Add e2e test for shared-context preference**

In `tests/e2e/test_commit_semantic.py`, add a test that creates:
- a shared `data/commit-extract/repo-context.json`
- a local `data/commit-semantic/repo-context.json`

Then assert `commit-semantic` uses the shared artifact’s `semantic_context` when both exist.

- [ ] **Step 2: Add e2e test for fallback to local context**

Add a test asserting that when shared extract context is missing, current local context behavior still works.

- [ ] **Step 3: Update full-pipeline e2e assertions**

In `tests/e2e/test_pipeline_e2e.py`, add or update assertions so the pipeline validates cross-subproject integration:
- shared context emitted by `commit-extract`
- shared context consumed by `commit-semantic`

Do not require reliability-layer behavior yet.

- [ ] **Step 4: Run targeted e2e tests**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -k "context or shared" -v
pytest tests/e2e/test_pipeline_e2e.py -k "context or shared" -v
```

Expected: PASS

- [ ] **Step 5: Run broader semantic e2e slice**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -v
```

Expected: PASS

---

## Task 4: Update skill docs to match transitional consumer behavior

**Files:**
- Modify: `skills/commit-semantic/SKILL.md`

- [ ] **Step 1: Document shared-context preference explicitly**

Update docs to say:
- `commit-semantic` now prefers the shared context emitted by `commit-extract`
- local context generation remains temporary compatibility behavior
- producer ownership has not yet been fully removed from `commit-semantic`

- [ ] **Step 2: Clarify cutover posture**

Document that this subproject changes **consumer precedence**, not full ownership removal.

- [ ] **Step 3: Run doc/code read-through**

Verify docs match:
- current runtime behavior
- actual file paths
- actual transitional semantics

---

## Task 5: Verify subproject boundaries and compatibility

**Files:**
- Modify: `docs/superpowers/plans/2026-03-24-shared-bootstrap-semantic-consumer-migration.md` (this plan only, if needed)

- [ ] **Step 1: Verify no producer removal happened yet**

Confirm `commit-semantic` can still generate local context if needed in compatibility mode.

- [ ] **Step 2: Verify no reliability-layer logic slipped in**

Confirm no implementation added:
- freshness / stale detection
- adaptive fallback / bypass
- eval fixtures

- [ ] **Step 3: Final verification**

Run:
```bash
pytest tests/test_commit_semantic_context_resolution.py tests/e2e/test_commit_semantic.py tests/e2e/test_pipeline_e2e.py -v
```

Expected: PASS

- [ ] **Step 4: Final commit**

```bash
git add skills/commit-semantic/run.py skills/commit-semantic/SKILL.md tests/test_commit_semantic_context_resolution.py tests/fixtures/commit_semantic_consumer/shared_extract_repo_context.json tests/e2e/test_commit_semantic.py tests/e2e/test_pipeline_e2e.py docs/superpowers/plans/2026-03-24-shared-bootstrap-semantic-consumer-migration.md
git commit -m "chore: finalize semantic consumer migration subproject"
```

---

## Test Strategy Summary

### Unit coverage
- `tests/test_commit_semantic_context_resolution.py`
  - shared-vs-local context precedence
  - fallback behavior
  - extraction of `semantic_context` only

### Integration coverage
- `tests/e2e/test_commit_semantic.py`
  - shared context preferred when available
  - local context fallback still works
- `tests/e2e/test_pipeline_e2e.py`
  - Subproject 2 producer + Subproject 3 consumer integration

### Explicitly deferred
- producer removal from `commit-semantic`
- freshness / stale detection
- degraded/full/bypass behavior
- eval fixtures

---

## Acceptance Criteria
- `commit-semantic` prefers `data/commit-extract/repo-context.json` when it exists and is valid.
- `commit-semantic` falls back to local semantic context when the shared artifact is absent.
- Only `semantic_context` is consumed downstream.
- Existing compatibility behavior remains available during transition.
- No reliability-layer or producer-removal work slips into this subproject.

---

## Notes for implementers
- Keep the diff boring and migration-oriented.
- This subproject is about consumer precedence, not total producer removal.
- If there is ambiguity, prefer preserving current behavior with a narrow shared-context preference rule rather than redesigning the whole context stage.
