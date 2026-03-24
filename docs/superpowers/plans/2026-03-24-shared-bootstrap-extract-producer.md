# Shared Bootstrap Extract Producer Implementation Plan

**Goal:** Make `commit-extract` the temporary producer of the shared layered `repo-context.json` artifact, while preserving current extraction behavior and leaving `commit-semantic` compatibility in place.

**Architecture:** This subproject adds a focused bootstrap helper under `skills/commit-extract/` and wires it into the `collect` flow before worker manifest construction. The helper reads fixed repo input sources, builds the shared layered context contract already locked in Subproject 1, writes it to `data/commit-extract/repo-context.json`, and injects only the `shared_hints` portion into worker prompts. It does not implement freshness, fallback, bypass, or eval logic yet.

**Tech Stack:** Python 3.10+, pytest, JSON artifact IO, existing `SkillRunner` / `HarnessState` / git CLI orchestration.

---

## File Structure

### Files to create
- `skills/commit-extract/bootstrap.py`
  - New helper module for Subproject 2 only.
  - Responsibilities:
    - discover fixed input sources
    - read `.planning/codebase/*` if present
    - read `README.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `AGENTS.md` if present
    - build layered `repo-context.json`
    - derive `shared_hints` block for prompt injection
- `tests/test_commit_extract_bootstrap.py`
  - Unit tests for bootstrap source loading and contract writing.
- `tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json`
  - Golden fixture representing a valid producer-side output.

### Files to modify
- `skills/commit-extract/run.py`
  - Wire bootstrap helper into `_run_collect()` before prompt/manifest creation.
  - Inject `shared_hints` into worker prompt construction.
  - Record written artifact path in state.
- `tests/e2e/test_commit_extract.py`
  - Add e2e coverage for bootstrap artifact generation and worker prompt injection.
- `docs/generate_commit.md`
  - Do **not** rewrite semantics in this subproject; only confirm prompt can accept an injected repo context prefix if needed.

### Files to inspect while implementing
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-context-contract.md`
  - Source of truth for the contract.
- `skills/commit-semantic/run.py`
  - Current temporary producer; use it as shape reference, not as owner.
- `tests/test_shared_repo_context_contract.py`
  - Contract expectations that Subproject 2 producer must satisfy.
- `skills/commit-semantic/SKILL.md`
  - Confirms ownership has not fully migrated yet; preserve that compatibility posture.

### Explicitly out of scope in this subproject
- Removing `commit-semantic`’s current producer path
- Freshness / staleness detection
- Adaptive fallback / bypass
- Health summary behavior guarantees beyond writing the contract
- Eval fixtures
- `commit-semantic` consumer migration beyond continuing to read what already works

---

## Producer Contract for this subproject

### Canonical artifact path
- `data/commit-extract/repo-context.json`

### Subproject 2 output requirements
The new producer must write a `repo-context.json` with the same layered structure established in Subproject 1:
- `shared_hints`
- `semantic_context`
- `summary`

### Minimum producer guarantees now
- `shared_hints` must be populated from fixed input sources using deterministic transformation
- `semantic_context` may be a conservative projection of `shared_hints` for compatibility
- `summary` may use provisional values but must obey the contract shape

### Required fixed input sources
Attempt to read these exact sources if present:
- `README.md`
- `ARCHITECTURE.md`
- `CLAUDE.md`
- `AGENTS.md`
- every file under `.planning/codebase/*`

Missing sources are allowed in this subproject. They do not fail the run.

### Producer behavior rule
Subproject 2 must be boring:
- If a source is missing → skip it
- If all optional sources are missing → still produce a minimal layered artifact
- Do not implement degraded/full/bypass semantics yet beyond contract-compliant placeholder `summary`

---

## Task 1: Add bootstrap unit tests and fixture first

**Files:**
- Create: `tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json`
- Create: `tests/test_commit_extract_bootstrap.py`

- [ ] **Step 1: Create the producer-side fixture**

Write `tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json` with a valid layered `repo-context.json` example that matches the Subproject 1 contract.

- [ ] **Step 2: Write failing bootstrap source-loading tests**

In `tests/test_commit_extract_bootstrap.py`, add tests for a future helper such as:

```python
def test_collect_bootstrap_sources_reads_fixed_repo_docs(tmp_path):
    ...

def test_collect_bootstrap_sources_reads_planning_codebase_files(tmp_path):
    ...

def test_collect_bootstrap_sources_skips_missing_inputs(tmp_path):
    ...
```

Assert:
- fixed source filenames are discovered when present
- `.planning/codebase/*` files are included when present
- missing inputs do not raise

- [ ] **Step 3: Write failing producer-shape tests**

Add tests asserting a future bootstrap helper returns/writes:
- top-level `shared_hints`, `semantic_context`, `summary`
- `shared_hints.source_snapshot.docs`
- `shared_hints.source_snapshot.codebase_map`
- `summary.hint_count` and `summary.source_counts` match contract counting rules

- [ ] **Step 4: Write failing shared-hints extraction test**

Add a test for a helper like:

```python
def test_bootstrap_builds_shared_hints_for_prompt_injection():
    ...
```

Assert the returned prompt payload is the `shared_hints` layer, not the whole `repo-context.json`.

- [ ] **Step 5: Run tests to verify failure**

Run:
```bash
pytest tests/test_commit_extract_bootstrap.py -v
```

Expected: FAIL because helper module does not exist yet.

- [ ] **Step 6: Commit (optional checkpoint)**

```bash
git add tests/test_commit_extract_bootstrap.py tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json
git commit -m "test: add commit-extract bootstrap producer fixtures"
```

---

## Task 2: Implement bootstrap helper

**Files:**
- Create: `skills/commit-extract/bootstrap.py`
- Test: `tests/test_commit_extract_bootstrap.py`

- [ ] **Step 1: Create source discovery helpers**

Implement small, deterministic functions such as:

```python
def collect_bootstrap_doc_paths(repo_root: Path) -> dict[str, list[Path]]:
    ...

def read_bootstrap_sources(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    ...
```

Rules:
- `docs` bucket = fixed source files if present
- `codebase_map` bucket = `.planning/codebase/*` files if present
- Missing files are skipped quietly

- [ ] **Step 2: Create deterministic projection into layered context**

Implement helper(s) that transform the source set into the layered context contract.

This subproject does **not** need full semantic intelligence. Minimal acceptable behavior:
- source file paths populate `source_snapshot`
- empty/default shapes are present for provenance/confidence/conflicts
- `shared_hints.local_capabilities`, `aliases`, `ownership_hints`, `seed_concepts` may start conservative/empty if no extraction logic exists yet
- `semantic_context` is derived from `shared_hints` in a simple compatibility-friendly way
- `summary.hint_count` / `source_counts` follow the contract counting rules

- [ ] **Step 3: Run unit tests**

Run:
```bash
pytest tests/test_commit_extract_bootstrap.py -v
pytest tests/test_shared_repo_context_contract.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/commit-extract/bootstrap.py tests/test_commit_extract_bootstrap.py tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json
git commit -m "feat: add commit-extract bootstrap helper"
```

---

## Task 3: Wire bootstrap producer into `commit-extract`

**Files:**
- Modify: `skills/commit-extract/run.py`
- Test: `tests/e2e/test_commit_extract.py`

- [ ] **Step 1: Extend `CommitExtractRunner` to build context before manifest creation**

Add the minimal bootstrap call inside `_run_collect()` after output directories are prepared and before prompt/manifest writing.

Target behavior:
- build layered context artifact
- write `data/commit-extract/repo-context.json`
- record artifact in state
- continue normal collect flow even if inputs are sparse

Do not add freshness/fallback logic yet.

- [ ] **Step 2: Update worker prompt construction to inject `shared_hints` only**

Modify `_build_worker_prompt()` so it can prepend a compact `Repo Context` / `Shared Hints` block before the existing analysis prompt.

Rules:
- inject only `shared_hints`
- do not inject the full layered `repo-context.json`
- preserve existing prompt instructions from `prompt.md` / `docs/generate_commit.md`

- [ ] **Step 3: Write failing e2e tests for producer behavior**

In `tests/e2e/test_commit_extract.py`, add tests asserting:
- `repo-context.json` is written during collect
- the written artifact has layered top-level keys
- manifest still gets written
- worker prompt includes a shared-hints block when context exists

- [ ] **Step 4: Run targeted tests**

Run:
```bash
pytest tests/e2e/test_commit_extract.py -k "context or prompt or collect" -v
pytest tests/test_commit_extract_bootstrap.py -v
```

Expected: PASS

- [ ] **Step 5: Run broader extract e2e coverage**

Run:
```bash
pytest tests/e2e/test_commit_extract.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/commit-extract/run.py tests/e2e/test_commit_extract.py
git commit -m "feat: produce shared repo context in commit-extract"
```

---

## Task 4: Verify subproject boundaries and compatibility

**Files:**
- Modify: `docs/superpowers/plans/2026-03-24-shared-bootstrap-extract-producer.md` (this plan only, if needed)

- [ ] **Step 1: Verify no owner cutover happened yet**

Confirm:
- `commit-extract` now produces shared `repo-context.json`
- `commit-semantic` producer path is still present for compatibility
- no delete/remove work was done in `commit-semantic`

- [ ] **Step 2: Verify no reliability logic slipped in**

Confirm no implementation added:
- freshness checks
- stale detection
- adaptive fallback
- debug bypass
- eval fixtures

If any slipped in, remove them or defer them.

- [ ] **Step 3: Final verification**

Run:
```bash
pytest tests/test_commit_extract_bootstrap.py tests/test_shared_repo_context_contract.py tests/e2e/test_commit_extract.py -v
```

Expected: PASS

- [ ] **Step 4: Final commit**

```bash
git add skills/commit-extract/bootstrap.py skills/commit-extract/run.py tests/test_commit_extract_bootstrap.py tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json tests/e2e/test_commit_extract.py docs/superpowers/plans/2026-03-24-shared-bootstrap-extract-producer.md
git commit -m "chore: finalize extract bootstrap producer subproject"
```

---

## Test Strategy Summary

### Unit coverage
- `tests/test_commit_extract_bootstrap.py`
  - source discovery
  - source reading
  - layered context writing
  - shared-hints extraction for prompt injection

### Integration coverage
- `tests/e2e/test_commit_extract.py`
  - `repo-context.json` emitted during collect
  - manifest still written
  - worker prompt receives shared hints only

### Explicitly deferred
- freshness / stale detection
- degraded/full/bypass runtime behavior
- debug bypass
- eval fixtures for helpful/stale/conflicting prior
- `commit-semantic` consumer cutover

---

## Acceptance Criteria
- `commit-extract` writes canonical layered `data/commit-extract/repo-context.json` during collect.
- The written artifact satisfies the Subproject 1 contract.
- Worker prompt injection uses only the `shared_hints` layer.
- Existing collect/manifest behavior continues to pass e2e tests.
- No reliability-layer or cutover work slips into this subproject.

---

## Notes for implementers
- Keep the diff boring and local.
- This subproject is about producing the shared artifact, not switching all consumers yet.
- Conservative empty/default `shared_hints` values are acceptable if source-derived extraction is not yet implemented, as long as the contract is valid and prompt injection path is wired.
- If you need a tiny deterministic helper to project source files into placeholder hint fields, do it in `skills/commit-extract/bootstrap.py`; do not expand `run.py` into a second orchestration monolith.
