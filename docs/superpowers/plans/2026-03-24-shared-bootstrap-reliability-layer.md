# Shared Bootstrap Reliability Layer Implementation Plan

**Goal:** Add the reliability layer for the shared bootstrap so repo context production and consumption become operationally trustworthy: freshness checks, three-tier runtime mode (`full` / `degraded` / `bypass`), adaptive fallback, debug bypass, and health summary semantics.

**Architecture:** This subproject sits on top of the already-completed contract, extract producer, and semantic consumer migration. It does not redesign schema ownership or consumer precedence. Instead, it adds a cheap freshness model around the shared `repo-context.json`, a deterministic runtime decision layer for whether to inject hints fully, partially, or not at all, and a human-readable + machine-readable health surface. The reliability logic should live close to the extract producer path, because `commit-extract` is the current owner of shared context generation.

**Tech Stack:** Python 3.10+, pytest, JSON artifact IO, existing `SkillRunner` / `HarnessState`, current bootstrap helper in `skills/commit-extract/bootstrap.py`.

---

## File Structure

### Files to modify
- `skills/commit-extract/bootstrap.py`
  - Add freshness fingerprint helpers
  - Add summary/status computation
  - Add adaptive mode selection helpers
- `skills/commit-extract/run.py`
  - Integrate freshness checks and adaptive fallback into `_run_collect()`
  - Support debug bypass flag
  - Ensure worker prompt injection respects runtime mode
- `tests/test_commit_extract_bootstrap.py`
  - Extend unit coverage for freshness, mode selection, and summary semantics
- `tests/e2e/test_commit_extract.py`
  - Extend e2e coverage for full/degraded/bypass behavior
- `skills/commit-extract/SKILL.md`
  - Document reliability-layer behavior and transitional ownership

### Files to create
- `tests/fixtures/commit_extract_bootstrap/stale_repo_context.json`
  - Fixture for stale / out-of-date context scenarios
- `tests/fixtures/commit_extract_bootstrap/degraded_repo_context.json`
  - Fixture for weak-context / reduced-hints scenarios
- `tests/test_commit_extract_reliability.py`
  - Focused unit tests for freshness, adaptive mode selection, and debug bypass

### Files to inspect while implementing
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-context-contract.md`
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-extract-producer.md`
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-semantic-consumer-migration.md`
- `tests/test_shared_repo_context_contract.py`

### Explicitly out of scope in this subproject
- No producer ownership change
- No removal of `commit-semantic` fallback producer path
- No new semantic extraction heuristics beyond deciding whether hints are injected fully/partially/not at all
- No eval fixture expansion beyond reliability-specific assertions
- No demand-pipeline integration

---

## Reliability Contract

### Runtime modes
The reliability layer must produce exactly one of:
- `full`
  - shared context is fresh and structurally valid
  - inject all eligible `shared_hints` according to existing confidence + relevance rules
- `degraded`
  - shared context exists but is weak / partial / reduced
  - inject only allowed reduced hints (e.g. high-confidence only)
- `bypass`
  - shared context is missing, stale-unusable, invalid, or explicitly bypassed
  - inject no hints

### Fail-loud boundary
The collect flow should only fail loudly when there is infrastructure-level corruption such as:
- unreadable / invalid artifact when no safe fallback path is possible
- fingerprint state cannot be computed or persisted in a way that makes mode selection unsafe
- debug bypass flag handling is broken structurally

Missing docs, sparse inputs, or low-signal context should **not** hard-fail; they should become `degraded` or `bypass`.

### Freshness model
Use a cheap input snapshot. Minimum inputs to fingerprint:
- fixed docs actually present among:
  - `README.md`
  - `ARCHITECTURE.md`
  - `CLAUDE.md`
  - `AGENTS.md`
- all files present under `.planning/codebase/*`
- the bootstrap schema version / code version constant

Minimum persistence requirement:
- store the freshness snapshot in the context summary or adjacent metadata so later runs can compare without recomputing full context semantics.

### Health summary semantics
`summary` should now become operational, not placeholder-only. Minimum fields:
- `bootstrap_status`: `full|degraded|bypass`
- `hint_count`
- `source_counts`
- `used_cached_context`: bool
- `degraded_reasons`: list[str]
- `bypass_reason`: string | null
- `fingerprint`: string

### Debug bypass
Add a narrow debug lever for operators and tests, e.g. `--skip-bootstrap`.
Behavior:
- forces `bootstrap_status=bypass`
- skips hint injection
- still allows collect/manifest flow to proceed
- must be visible in summary output

---

## Task 1: Add failing reliability tests first

**Files:**
- Create: `tests/fixtures/commit_extract_bootstrap/stale_repo_context.json`
- Create: `tests/fixtures/commit_extract_bootstrap/degraded_repo_context.json`
- Create: `tests/test_commit_extract_reliability.py`

- [ ] **Step 1: Write stale/degraded fixtures**
Create fixtures representing:
- a stale context snapshot
- a degraded context with reduced hints and explicit degraded reasons

- [ ] **Step 2: Write failing freshness tests**
Add tests for helper behavior such as:
```python
def test_freshness_snapshot_changes_when_source_files_change():
    ...

def test_context_is_reused_when_fingerprint_matches():
    ...
```

- [ ] **Step 3: Write failing mode-selection tests**
Add tests asserting:
- valid fresh context -> `full`
- weak context -> `degraded`
- missing/invalid or explicit bypass -> `bypass`

- [ ] **Step 4: Write failing debug-bypass test**
Assert collect flow or helper mode selection honors an explicit bypass flag.

- [ ] **Step 5: Run tests to confirm failure**
Run:
```bash
pytest tests/test_commit_extract_reliability.py -v
```
Expected: FAIL before implementation.

---

## Task 2: Implement freshness and mode-selection helpers

**Files:**
- Modify: `skills/commit-extract/bootstrap.py`
- Test: `tests/test_commit_extract_reliability.py`

- [ ] **Step 1: Add snapshot/fingerprint helpers**
Implement helpers to collect source metadata and compute a cheap fingerprint.

- [ ] **Step 2: Add reliability decision helpers**
Implement deterministic helpers such as:
```python
def determine_bootstrap_mode(...):
    ...

def build_reliability_summary(...):
    ...
```

- [ ] **Step 3: Run focused unit tests**
Run:
```bash
pytest tests/test_commit_extract_reliability.py tests/test_commit_extract_bootstrap.py -v
```
Expected: PASS.

---

## Task 3: Wire reliability layer into collect flow

**Files:**
- Modify: `skills/commit-extract/run.py`
- Test: `tests/e2e/test_commit_extract.py`

- [ ] **Step 1: Add debug bypass CLI flag**
Add a narrow collect-time bypass flag (e.g. `--skip-bootstrap`).

- [ ] **Step 2: Apply runtime mode in `_run_collect()`**
Before manifest creation:
- compute freshness/mode
- reuse context when safe
- rebuild when needed
- inject hints based on runtime mode

- [ ] **Step 3: Ensure manifest prompt reflects runtime mode**
Assert:
- `full` uses shared hints
- `degraded` uses reduced shared hints block
- `bypass` omits shared hints entirely

- [ ] **Step 4: Run targeted e2e tests**
Run:
```bash
pytest tests/e2e/test_commit_extract.py -k "collect or prompt or bypass or degraded" -v
```
Expected: PASS.

---

## Task 4: Update docs and verify boundaries

**Files:**
- Modify: `skills/commit-extract/SKILL.md`

- [ ] **Step 1: Document runtime reliability behavior**
Explain freshness, `full/degraded/bypass`, and debug bypass.

- [ ] **Step 2: Verify no scope leak**
Confirm this subproject did not:
- remove semantic producer fallback
- add demand integration
- change semantic consumer precedence rules

- [ ] **Step 3: Final verification**
Run:
```bash
pytest tests/test_commit_extract_reliability.py tests/test_commit_extract_bootstrap.py tests/e2e/test_commit_extract.py tests/e2e/test_pipeline_e2e.py -v
```
Expected: PASS.

---

## Acceptance Criteria
- Shared bootstrap has explicit `full/degraded/bypass` runtime behavior.
- Freshness decisions use a cheap persisted fingerprint.
- Missing or weak inputs degrade or bypass instead of hard-failing the collect flow.
- Debug bypass is visible and test-covered.
- Health summary is operationally meaningful, not placeholder-only.
- Existing producer/consumer boundaries remain intact.

---

## Notes for implementers
- Keep reliability logic local to the current producer (`commit-extract`).
- Do not let this subproject mutate the contract or semantic meaning of `shared_hints` beyond deciding injection mode.
- If in doubt, prefer explicit status fields over clever inference.
