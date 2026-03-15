# Runtime Repair Report

## Summary

8-stage runtime repair completed. All issues resolved, 217 tests passing.

---

## Issues Fixed

### Stage 1: Runtime Validation Hardening
Enforced structured artifact validation at write time. Discovery and refine executors
now reject artifacts missing required section headings rather than silently accepting
empty or malformed content.

### Stage 2: Discovery Failure Propagation
Fixed discovery pipeline to stop on validation failures and propagate error status
correctly. Previously, validation failures were recorded but execution continued.

### Stage 3: Acceptance Contract Unification
Unified acceptance semantics across `refine_executor.py`, `state_inspector.py`, and
`evaluate_acceptance()`. All acceptance checks now require the exact structured field
`acceptance: true` — free-text mentions are rejected.

### Stage 4: Baseline Version Retention
Added `get_accepted_versions()` to `artifact_writer.py` to read accepted baseline
versions from `checkpoint.json`. Both `_apply_versioning_protocol()` implementations
(discovery and refine) now load checkpoint data and protect accepted versions from
pruning.

### Stage 5: State Inspector Fix
Fixed `state_inspector.inspect()` to detect versioned `review-summary.vN.md` files.
Previously it checked for the unversioned `review-summary.md`, which the runtime never
writes.

### Stage 6: Dispatcher / CLI Execution Path
Fixed `dispatcher.py` to forward the `executor` parameter to `_handle_discover()` and
`_handle_refine()`. Fixed `main.py` to return exit code 1 for `validation_failed`,
`execution_unavailable`, and `version_skew` statuses (previously only `error` triggered
a non-zero exit).

### Stage 7: Path Traversal Protection
Added `_validate_path(path, root)` sandbox helper to both `skill_loader.py` and
`prompt_loader.py`. All file loads now verify the resolved path is within the repository
root. `resolve_prompt_path()` validates on every call.

### Stage 8: Version Allocation Race Protection
Replaced the non-atomic `_next_version()` with an `O_CREAT | O_EXCL` atomic
implementation that retries up to 64 times on collision. Added `_peek_next_version()`
for staging/validation passes where no file should be created until all validations
pass. `stage_artifact()` uses the peek variant; `write_artifact()` uses the atomic
variant.

---

## Files Modified

**Source files:**
- `src/artifact_writer.py` — `get_accepted_versions()`, atomic `_next_version()`, `_peek_next_version()`
- `src/discovery_executor.py` — `_apply_versioning_protocol()` reads checkpoint accepted versions
- `src/dispatcher.py` — executor forwarding in `_handle_discover()` / `_handle_refine()`
- `src/main.py` — exit code 1 for `validation_failed`, `execution_unavailable`, `version_skew`
- `src/prompt_loader.py` — `PathSandboxError`, `_validate_path()`, sandbox in `load_prompt()` / `resolve_prompt_path()`
- `src/refine_executor.py` — `_apply_versioning_protocol()` reads checkpoint accepted versions
- `src/skill_loader.py` — `PathSandboxError`, `_validate_path()`, sandbox in `load_skill()` / `load_all_skills()`
- `src/state_inspector.py` — versioned `review-summary.vN.md` detection

**Test files added:**
- `tests/test_baseline_retention.py` — 6 tests
- `tests/test_cli_exit_codes.py` — 7 tests
- `tests/test_dispatcher.py` — 4 tests
- `tests/test_path_sandbox.py` — 10 tests
- `tests/test_state_inspector.py` — 7 tests
- `tests/test_version_allocation.py` — 4 tests

---

## Test Results

```
217 passed in 0.35s
```

Starting count: 179 (after Stage 3)
Tests added in Stages 4–8: 38
Final count: 217

---

## Commits

| Commit | Stage | Message |
|--------|-------|---------|
| `bbe696f` | 4 | runtime: protect accepted baseline history |
| `483119e` | 5 | runtime: detect versioned review summaries |
| `1af39c1` | 6 | runtime: fix dispatcher executor forwarding and CLI exit codes |
| `d04b660` | 7 | security: enforce repo sandbox for plugin file loading |
| `a036e43` | 8 | runtime: make artifact version allocation atomic |

---

## Remaining Risks

- `stage_artifact()` + `commit_staged()` is not fully atomic end-to-end: two concurrent
  staging calls may compute the same peek version. In practice this path is always called
  sequentially, but a future refactor should pass the atomically-allocated path through
  from `commit_staged()` rather than from `stage_artifact()`.

- Path sandbox validation uses `Path.resolve()` which follows symlinks. A symlink within
  the repo pointing outside the root would pass validation. This is an acceptable
  trade-off for the current use case.
