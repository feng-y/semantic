# Commit-Semantic Domain Quality Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve `commit-semantic` domain quality by cleaning domain schema, reducing incorrect/over-eager classification, reporting runtime provenance, and switching the default runtime to LLM-first semantics with explicit degraded fallback behavior.

**Architecture:** Keep `skills/commit-semantic/run.py` as orchestration and move domain normalization / deterministic classification rules into pure functions in `src/commit_semantic/domain_utils.py`. Implement in four checkpoints: schema normalization, deterministic classification gating, mode/provenance reporting, then LLM-first default switching. Every checkpoint must be independently testable and keep the repo-level pipeline runnable.

**Tech Stack:** Python 3.10+, pytest, JSONL artifacts, existing `HarnessState`, existing `commit-semantic` prompts and pipeline.

---

## File Structure

### Primary files to modify
- `src/commit_semantic/domain_utils.py`
  - Add pure functions for domain normalization, duplicate merging, noise filtering, deterministic scoring, and ambiguity gating.
- `skills/commit-semantic/run.py`
  - Keep orchestration only: call pure functions, persist provenance, export mode fields, and switch default runtime behavior.
- `tests/test_commit_semantic_domain.py`
  - Add pure-function tests for normalization, merge thresholds, deterministic scoring, and path-disable-after-multi-domain-failure logic.
- `tests/e2e/test_commit_semantic.py`
  - Add pipeline-level tests for cache/provenance restore, summary mode fields, local fallback behavior, and repo-style classification scenarios.
- `skills/commit-semantic/SKILL.md`
  - Update runtime mode semantics and summary/output contract after code/tests are done.

### Secondary files (only if needed)
- `docs/superpowers/specs/2026-03-23-commit-semantic-domain-quality-design.md`
  - Only if implementation reveals wording mismatch requiring a tiny spec correction.

### Files that should NOT be touched in this plan
- `skills/commit-extract/run.py`
- `skills/repo_structure/run.py`
- `src/demand/**`
- aggregate/distill scoring formulas outside the mode/schema/classify work

---

## Execution Order

1. **Checkpoint A — Domain schema normalization**
2. **Checkpoint B — Deterministic classify upgrade**
3. **Checkpoint C — Mode/provenance reporting**
4. **Checkpoint D — LLM-first default switch**

Do not start the next checkpoint until the current checkpoint tests pass.

---

### Task 1: Add domain normalization pure functions

**Files:**
- Modify: `src/commit_semantic/domain_utils.py`
- Test: `tests/test_commit_semantic_domain.py`

- [ ] **Step 1: Write failing normalization tests**

Add tests for:
- singular/plural merge: `test` + `tests` => `tests`
- exact duplicate merge
- near-duplicate merge with keyword Jaccard overlap >= 0.6
- near-duplicate merge with path-prefix overlap >= 0.5
- noise token rejection (`add`, `update`, `fix`, `impl`, `phase`, `final`, `worktree`)
- winner selection priority:
  1. non-empty paths
  2. more keywords
  3. non-noise name
  4. lexical tie-break

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/test_commit_semantic_domain.py -q
```
Expected: new normalization tests fail because functions do not exist yet.

- [ ] **Step 3: Implement minimal pure functions**

Add pure helpers in `src/commit_semantic/domain_utils.py`:
- `normalize_domain_name(name: str) -> str`
- `is_noise_domain_name(name: str) -> bool`
- `merge_domain_candidates(domains: list[dict]) -> list[dict]`
- `normalize_domains(domains: list[dict]) -> list[dict]`

Rules must follow the spec exactly:
- preserve `domain` field name
- lowercase + dash-case
- singular/plural merge on exact normalized stems
- near-duplicate merge on keyword Jaccard or path overlap thresholds
- apply minimum quality gate

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/test_commit_semantic_domain.py -q
```
Expected: all normalization tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/commit_semantic/domain_utils.py tests/test_commit_semantic_domain.py
git commit -m "feat: normalize commit semantic domains"
```

---

### Task 2: Wire normalization into discover paths

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: `tests/e2e/test_commit_semantic.py`
- Test: `tests/test_commit_semantic_domain.py`

- [ ] **Step 1: Write failing discover integration tests**

Add tests proving:
- `complete_discover()` normalizes LLM output before saving
- local fallback discover also normalizes before saving
- a combined fixture with `test/tests` + noise tokens + overlapping keywords produces a cleaned `domains.json`

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py tests/test_commit_semantic_domain.py -q
```
Expected: new discover normalization tests fail.

- [ ] **Step 3: Implement minimal orchestration changes**

In `skills/commit-semantic/run.py`:
- import and call `normalize_domains()` in both:
  - local fallback discover path
  - `complete_discover()`
- do not change fingerprint behavior
- keep existing prompt preparation behavior intact

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py tests/test_commit_semantic_domain.py -q
```
Expected: discover normalization tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py tests/test_commit_semantic_domain.py
git commit -m "feat: normalize discovered commit semantic domains"
```

---

### Task 3: Add deterministic scoring and ambiguity gate as pure functions

**Files:**
- Modify: `src/commit_semantic/domain_utils.py`
- Test: `tests/test_commit_semantic_domain.py`

- [ ] **Step 1: Write failing scoring tests**

Add pure-function tests for:
- scoring weights:
  - path-prefix = 5
  - theme token = 3
  - summary token = 2
  - section-name token = 2
  - domain-keyword = 1
- repeated hits do not stack beyond one hit per signal type
- minimum score gate = 4
- ambiguous if `top1 - top2 < 2`
- when commit-level multi-domain failure already occurred, unit-level scoring must ignore path-prefix signals

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/test_commit_semantic_domain.py -q
```
Expected: new scoring tests fail.

- [ ] **Step 3: Implement minimal pure helpers**

Add helpers such as:
- `score_unit_for_domain(...)`
- `pick_domain_for_unit(...)`
- `classify_units_locally(...)`

Make the API explicit enough that `run.py` just passes context and receives decisions.

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/test_commit_semantic_domain.py -q
```
Expected: scoring tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/commit_semantic/domain_utils.py tests/test_commit_semantic_domain.py
git commit -m "feat: add deterministic domain classification scoring"
```

---

### Task 4: Replace local classify logic in runner with pure-function orchestration

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: `tests/e2e/test_commit_semantic.py`

- [ ] **Step 1: Write failing ingest/classify integration tests**

Add tests proving:
- multi-domain commit failure disables path-based scoring at unit fallback time
- strong single-domain path match still assigns at commit level
- ambiguous unit remains `uncategorized` if no LLM and no sufficient non-path score
- mixed/no-path unit uses non-path scoring only

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -q
```
Expected: new integration tests fail.

- [ ] **Step 3: Implement minimal runner changes**

In `skills/commit-semantic/run.py`:
- keep commit-level `assign_domain_by_path()` fast path
- when commit-level convergence fails, pass explicit context to pure functions so unit fallback does NOT use path scoring
- keep external orchestration metadata path intact
- keep `complete_classify()` behavior intact for external LLM responses

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -q
```
Expected: ingest/classify integration tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: gate commit semantic fallback classification"
```

---

### Task 5: Add runtime mode provenance persistence and cache restore

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: `tests/e2e/test_commit_semantic.py`
- Test: `tests/test_commit_semantic_domain.py` (if helper extraction is needed)

- [ ] **Step 1: Write failing provenance tests**

Add tests proving:
- `domains.json` persists discover provenance fields
- cache hit restores `discover_mode` into `HarnessState.metadata`
- export reports actual execution mode, not default assumptions
- local fallback and mixed-degraded cases are distinguishable in summary output

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -q
```
Expected: provenance/mode tests fail.

- [ ] **Step 3: Implement minimal provenance changes**

In `skills/commit-semantic/run.py`:
- persist discover provenance into `domains.json`
- restore provenance on cache hit
- set `orchestration_mode`, `discover_mode`, `classify_mode` in `HarnessState.metadata`
- preserve current behavior for `external_orchestration`

Do not invent a generic state framework; keep changes local to this pipeline.

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -q
```
Expected: provenance tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: persist commit semantic runtime provenance"
```

---

### Task 6: Export mode fields and update summary contract

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Modify: `skills/commit-semantic/SKILL.md`
- Test: `tests/test_export_dataclasses.py`
- Test: `tests/e2e/test_commit_semantic.py`

- [ ] **Step 1: Write failing export tests**

Add/adjust tests asserting `summary.json` includes:
- `orchestration_mode`
- `discover_mode`
- `classify_mode`
- existing fields remain intact

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/test_export_dataclasses.py tests/e2e/test_commit_semantic.py -q
```
Expected: export mode-field tests fail.

- [ ] **Step 3: Implement minimal export change**

In `skills/commit-semantic/run.py`:
- emit the three mode fields from `state.metadata`
- do not remove existing summary fields

In `skills/commit-semantic/SKILL.md`:
- document the new mode fields and degraded-mode visibility

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/test_export_dataclasses.py tests/e2e/test_commit_semantic.py -q
```
Expected: export tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/commit-semantic/run.py skills/commit-semantic/SKILL.md tests/test_export_dataclasses.py tests/e2e/test_commit_semantic.py
git commit -m "feat: report commit semantic runtime modes"
```

---

### Task 7: Precompute normalization and scoring inputs

**Files:**
- Modify: `src/commit_semantic/domain_utils.py`
- Test: `tests/test_commit_semantic_domain.py`

- [ ] **Step 1: Write failing precompute-focused tests**

Add tests that lock behavior while allowing internal optimization:
- normalized keywords are deduplicated once
- repeated scoring on the same domains/units reuses precomputed normalized structures
- classification behavior stays identical after precompute refactor

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/test_commit_semantic_domain.py -q
```
Expected: new tests fail.

- [ ] **Step 3: Implement minimal precompute layer**

Add a small pure precompute step for:
- normalized domain keywords
- normalized domain names
- path-prefix structures if needed

Do not add a separate cache subsystem.

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/test_commit_semantic_domain.py -q
```
Expected: precompute tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/commit_semantic/domain_utils.py tests/test_commit_semantic_domain.py
git commit -m "refactor: precompute commit semantic scoring inputs"
```

---

### Task 8: Switch default runtime to LLM-first semantics

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: `tests/e2e/test_commit_semantic.py`

- [ ] **Step 1: Write failing mode-default tests**

Add tests proving:
- default path is now LLM-first semantics
- fallback remains available and explicitly marked degraded
- repo-style run without external orchestration still succeeds via fallback, but exported mode reflects that it degraded

- [ ] **Step 2: Run tests to verify RED**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -q
```
Expected: mode-default tests fail.

- [ ] **Step 3: Implement minimal default-switch behavior**

Update `skills/commit-semantic/run.py` so that:
- design intent is LLM-first by default
- local execution still succeeds via fallback when orchestration is unavailable
- exported mode fields tell the truth about what happened

Do not remove fallback.

- [ ] **Step 4: Run tests to verify GREEN**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -q
```
Expected: mode-default tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: prefer llm-first commit semantic execution"
```

---

### Task 9: Run full verification and real-repo regression

**Files:**
- Modify: none unless failures require fixes in files above
- Test: `tests/test_commit_semantic_domain.py`
- Test: `tests/e2e/test_commit_semantic.py`
- Test: `tests/test_export_dataclasses.py`
- Test: any touched repo-structure tests if summary contract impacts them

- [ ] **Step 1: Run targeted test suite**

Run:
```bash
pytest tests/test_commit_semantic_domain.py tests/e2e/test_commit_semantic.py tests/test_export_dataclasses.py -q
```
Expected: all pass.

- [ ] **Step 2: Run broader regression suite**

Run:
```bash
pytest tests/test_commit_extract_rewrite.py tests/test_repo_structure.py tests/e2e/test_pipeline_e2e.py -q
```
Expected: all pass.

- [ ] **Step 3: Run full test suite**

Run:
```bash
pytest tests -q
```
Expected: full suite green.

- [ ] **Step 4: Run lint**

Run:
```bash
ruff check .
```
Expected: `All checks passed!`

- [ ] **Step 5: Re-run real repo manual validation**

Run:
```bash
python skills/commit-semantic/run.py run --force
```
Then inspect:
- `data/commit-semantic/domains.json`
- `data/commit-semantic/domains-aggregated.jsonl`
- `data/commit-semantic/summary.json`

Verify manually:
- no duplicate `test/tests`
- `uncategorized_ratio < 0.1762`
- top 5 domains have stronger paths/keywords
- mode fields are present and truthful

- [ ] **Step 6: Commit**

```bash
git add skills/commit-semantic/run.py src/commit_semantic/domain_utils.py skills/commit-semantic/SKILL.md tests/test_commit_semantic_domain.py tests/e2e/test_commit_semantic.py tests/test_export_dataclasses.py
git commit -m "feat: improve commit semantic domain quality"
```

---

## Test Plan Artifact

Affected areas to verify during QA / manual validation:
- `commit-semantic` full local run on real repo data
- discover cache hit behavior
- mixed/no-path classification fallback behavior
- summary mode reporting
- repo-level top domain quality and `uncategorized_ratio`

Critical paths:
- real repo `commit-extract -> commit-semantic` run
- local fallback discover/classify path
- future external orchestration compatibility through `complete_discover()` / `complete_classify()`

---

## Plan Review Notes

This plan intentionally avoids:
- changing aggregate/distill scoring formulas
- touching demand integration
- modifying commit-extract schema
- adding heavy new caching or infrastructure

It assumes the current approved spec at:
- `docs/superpowers/specs/2026-03-23-commit-semantic-domain-quality-design.md`

is the source of truth.
