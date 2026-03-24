# GStack Implementation Plan — Commit-Semantic Domain Quality Optimization

Branch: `feature/commit-semantic-domain`
Spec: `docs/superpowers/specs/2026-03-23-commit-semantic-domain-quality-design.md`
Mode: **gstack plan** (not superpowers)

## Goal

Make `commit-semantic` domain output good enough for stable downstream use with an **LLM-only** semantic path.
This plan fixes three things together:
1. domain schema quality
2. classification quality
3. runtime mode/provenance clarity for LLM execution

This plan does **not** preserve semantic fallback behavior. If LLM discover/classify is unavailable or invalid, the pipeline should fail fast rather than emit low-quality semantic output.

---

## What already exists

These are already real and should be reused, not rebuilt:

- `skills/commit-semantic/run.py`
  - full 5-stage runner exists
  - real repo pipeline already runs end-to-end
  - discover / ingest / aggregate / distill / export hooks already exist
- `src/commit_semantic/domain_utils.py`
  - contains pure helpers already used by the pipeline
  - best current home for new normalization/scoring logic
- `tests/e2e/test_commit_semantic.py`
  - already covers real pipeline behavior, fallback behavior, and repo-style output checks
- `tests/test_commit_semantic_domain.py`
  - already covers pure-function behavior and is the right place for more rule-focused tests
- repo-level baseline already exists
  - current real baseline: `uncategorized_ratio = 0.1762`

---

## NOT in scope

Do **not** include any of the following in this implementation:

- changing aggregate / distill scoring formulas
- changing `commit-extract` output schema
- integrating demand stage
- adding write-back / feedback correction loops
- building a new cache subsystem
- refactoring unrelated pipeline files just because they are large
- changing spec during implementation; if spec/code conflict appears, stop and ask

---

## File responsibilities

### Files to modify

#### 1. `src/commit_semantic/domain_utils.py`
Add pure rule logic here:
- domain name normalization
- noise filtering
- duplicate / near-duplicate merge
- deterministic scoring weights
- ambiguity gate
- path-disable-after-multi-domain-failure behavior

This file should own “what the rules are.”

#### 2. `skills/commit-semantic/run.py`
Keep orchestration here:
- call pure helpers
- persist discover provenance in `domains.json`
- restore provenance on cache hit
- set runtime mode metadata
- export runtime mode fields
- enforce **LLM-only** discover/classify behavior
- fail fast when LLM execution is unavailable or invalid

This file should own “when each rule path is used.”

#### 3. `tests/test_commit_semantic_domain.py`
Add focused unit tests for:
- normalization behavior
- merge thresholds
- scoring weights
- ambiguity gate
- path scoring disabled after commit-level multi-domain failure

#### 4. `tests/e2e/test_commit_semantic.py`
Add pipeline-level tests for:
- normalized `domains.json`
- cache hit restoring provenance
- summary mode fields
- multi-domain path failure behavior
- repo-level regression checks

#### 5. `tests/test_export_dataclasses.py`
Only touch if needed for summary schema assertions.
Prefer keeping mode/provenance tests in E2E unless there is a clean export-only assertion.

#### 6. `skills/commit-semantic/SKILL.md`
Update only after runtime mode/export behavior is actually implemented and verified.

---

## 4 execution checkpoints

This plan is intentionally split into 4 hard checkpoints. Do not start the next one until the current one is green.

```text
Checkpoint 1: Schema normalization
Checkpoint 2: Deterministic classify upgrade
Checkpoint 3: Mode / provenance reporting
Checkpoint 4: LLM-first default switch
```

At the end of each checkpoint:
- targeted tests pass
- no broken existing tests in touched areas
- repo-level pipeline still runs

---

## Checkpoint 1 — Schema normalization

### Objective
Make `domains.json` structurally cleaner before trying to lower `uncategorized`.

### Work

#### Task 1.1 — add pure normalization helpers
Modify:
- `src/commit_semantic/domain_utils.py`

Add pure helpers for:
- normalize domain name
- singular/plural merge (`test` + `tests` => `tests`)
- noise token rejection
- duplicate / near-duplicate merge
- minimum quality gate
- winner selection priority during merge

#### Task 1.2 — wire normalization into discover save paths
Modify:
- `skills/commit-semantic/run.py`

Apply the same normalization path to:
- local fallback discover
- `complete_discover()` LLM path

Keep fingerprint logic unchanged.

### Required tests

Add unit tests in `tests/test_commit_semantic_domain.py` for:
- exact duplicate merge
- singular/plural merge
- keyword-overlap merge threshold
- path-overlap merge threshold
- noise filtering
- winner selection priority

Add E2E fixture in `tests/e2e/test_commit_semantic.py` for a **combined normalization case**:
- duplicate `test/tests`
- noisy process tokens
- overlapping keyword/path domains
- expected cleaned `domains.json`

### Exit criteria
- duplicate normalized domains = 0 in test fixture
- `test/tests` collapse correctly
- bad process tokens do not survive as top-level domains unless justified by spec rules

---

## Checkpoint 2 — Deterministic classify upgrade

### Objective
Lower bad fallback assignments and reduce `uncategorized` only where evidence is genuinely strong.

### Work

#### Task 2.1 — move scoring rules into pure functions
Modify:
- `src/commit_semantic/domain_utils.py`

Implement deterministic scoring contract exactly as spec says:
- path-prefix = 5
- theme token = 3
- summary token = 2
- section-name token = 2
- domain-keyword = 1
- repeated hits do not stack per signal type
- minimum assignment score = 4
- ambiguous if `top1 - top2 < 2`

#### Task 2.2 — enforce path-disable-after-commit-failure
Modify:
- `skills/commit-semantic/run.py`
- maybe `src/commit_semantic/domain_utils.py` if context flag belongs there

Rule:
- if commit-level path convergence fails because files span multiple candidate domains,
  unit-level fallback scoring must **not** use path-prefix evidence for that commit.

#### Task 2.3 — keep single-domain fast path intact
Preserve existing behavior:
- if commit-level path assignment cleanly converges to one domain, keep commit-level fast path

### Required tests

Add unit tests in `tests/test_commit_semantic_domain.py` for:
- scoring weights
- non-stacking hits
- minimum score gate
- ambiguity gate

Add E2E tests in `tests/e2e/test_commit_semantic.py` for:
- single-domain path fast path still works
- multi-domain commit falls back to unit scoring
- after multi-domain failure, path scoring is disabled
- ambiguous non-path signals remain `uncategorized` when no stronger signal exists

### Exit criteria
- no regression in single-domain assignment
- multi-domain failure path no longer silently reuses whole-commit path evidence at unit level
- fallback assignments become more conservative, not more eager

---

## Checkpoint 3 — Mode / provenance reporting

### Objective
Make output truthful about how it was produced, especially across cache hits and degraded runs.

### Work

#### Task 3.1 — persist discover provenance in `domains.json`
Modify:
- `skills/commit-semantic/run.py`

Persist alongside `_fingerprint` and `domains`:
- `discover_mode`
- `orchestration_mode_at_discover`

#### Task 3.2 — restore provenance on cache hit
Modify:
- `skills/commit-semantic/run.py`

On discover cache hit:
- restore persisted mode data into `HarnessState.metadata`
- do not silently treat cache hit as “current default mode”

#### Task 3.3 — add exported mode fields
Modify:
- `skills/commit-semantic/run.py`
- `skills/commit-semantic/SKILL.md`

Export in `summary.json`:
- `orchestration_mode`
- `discover_mode`
- `classify_mode`

### Required tests

Add E2E tests for:
- discover cache hit restores provenance correctly
- summary mode fields exist
- local fallback run marks fallback/degraded truthfully
- mixed-degraded scenario is represented correctly

### Critical failure-path tests
These are hard requirements, not optional:
- discover cache hit should not erase provenance
- mode fields must reflect actual execution, not default assumptions

### Exit criteria
- summary always tells the truth about execution mode
- cache hit path is no longer a silent provenance lie

---

## Checkpoint 4 — LLM-only execution

### Objective
Make discover/classify strictly LLM-only and fail fast on invalid or unavailable LLM execution.

### Work

#### Task 4.0 — implement fail-fast decision table as a first-class task
Modify:
- `skills/commit-semantic/run.py`
- tests in `tests/e2e/test_commit_semantic.py`

Do **not** leave this implicit. Implement and test each failure branch directly:

- discover: LLM output empty/invalid
  - fail immediately
- discover: LLM unavailable
  - fail immediately
- classify: any batch fails
  - fail immediately
- classify: all batches must succeed before semantic output is considered valid
- local/no-orchestrator mode
  - fail immediately instead of emitting fallback semantic output

Required tests for Task 4.0:
- discover invalid/empty LLM output fails
- discover unavailable orchestration fails
- classify partial batch failure fails the stage
- classify total failure fails the stage
- no semantic output is emitted as a successful degraded fallback

#### Task 4.1 — define actual default behavior in runner
Modify:
- `skills/commit-semantic/run.py`

Desired behavior:
- default runtime is LLM-only
- no semantic fallback path remains for discover/classify
- exported mode fields describe LLM execution only when the run succeeds

### Required tests

Add tests for:
- default run requires LLM orchestration
- local run without orchestration fails cleanly
- success path exports truthful LLM mode fields only after valid completion

### Exit criteria
- default behavior is LLM-only
- failure branches are explicitly implemented and tested
- no low-quality semantic fallback output is emitted

---

## Verification plan

### Targeted tests after each checkpoint
Run the smallest relevant set first.

### Required full verification before calling the work done
Run all of these:

```bash
pytest tests/test_commit_semantic_domain.py -q
pytest tests/e2e/test_commit_semantic.py -q
pytest tests/test_export_dataclasses.py -q
pytest tests/test_commit_extract_rewrite.py tests/e2e/test_pipeline_e2e.py tests/test_repo_structure.py -q
pytest tests -q
ruff check .
```

### Required real repo manual validation
Re-run the real worktree pipeline with real LLM orchestration and inspect:
- `data/commit-semantic/domains.json`
- `data/commit-semantic/domains-aggregated.jsonl`
- `data/commit-semantic/summary.json`

Manual checklist:
- no duplicate domains like `test/tests`
- `uncategorized_ratio < 0.1762`
- top 5 domains no longer dominated by obvious process/noise buckets
- top 5 domains have stronger paths or stronger deduplicated keywords
- summary contains mode fields
- summary mode fields show successful LLM execution, not fallback/degraded semantics

---

## Failure modes to watch while implementing

1. **Cache lies about provenance**
- Risk: cache hit reports current mode instead of original discover mode
- Must be covered by tests before checkpoint 3 is complete

2. **Multi-domain commits get false-confidence classification**
- Risk: path evidence leaks into ambiguous classification logic and produces overconfident wrong assignments
- Must be covered by tests before checkpoint 2 is complete

3. **Normalization becomes too aggressive**
- Risk: legitimate distinct domains collapse into one bucket
- Mitigation: thresholded merge tests and explicit winner rules

4. **Silent semantic degradation**
- Risk: pipeline emits seemingly-valid semantic output even though LLM execution failed or never happened
- Mitigation: LLM-only fail-fast behavior and stage-level failure tests

---

## Minimal commit strategy

Commit at the end of each checkpoint, not at the end of the whole effort.

Suggested commit boundaries:
1. `feat: normalize commit semantic domains`
2. `feat: gate commit semantic fallback classification`
3. `feat: persist commit semantic runtime provenance`
4. `feat: prefer llm-first commit semantic execution`

---

## Plan-specific notes

- Do not edit the spec during implementation. If spec and code reality conflict, stop and ask.
- Prefer putting new rule logic in `domain_utils.py`, not `run.py`.
- Do not add new infra or generalized caches just because it seems cleaner.
- Keep diffs explicit and checkpointed.
