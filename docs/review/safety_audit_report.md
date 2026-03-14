# Semantic Harness Safety Audit Report

---

## PART 1 — Validation Boundary

```
Validation Boundary

validator_before_commit: YES
any_bypass_paths: YES (non-semantic artifacts only)
code_locations:
  VALIDATED (semantic state):
  - discovery_executor.py:194 — safe_write_artifact with validate_artifact_content
  - discovery_executor.py:277 — safe_write_artifact with validate_artifact_content (augment)
  - refine_executor.py:281-283 — stage_artifact with validate_refined_artifact
  - refine_executor.py:308 — commit_staged (only after all validations pass)
  - refine_executor.py:350 — safe_write_artifact with validate_refined_artifact
  - refine_executor.py:555-569 — validate_baseline_artifact before write_baseline at 574

  UNVALIDATED (non-semantic artifacts):
  - discovery_executor.py:200 — sampling-report (unversioned operational artifact)
  - refine_executor.py:398 — semantic-change-log (operational log, not semantic state)
```

Assessment: All semantic state artifacts (repo-understanding, knowledge-confidence, domain-candidates, repo-facts, review-summary, baseline) pass validation before commit. The two unvalidated writes are operational artifacts (sampling-report, change-log) that do not participate in semantic state or acceptance gates. **No safety violation.**

---

## PART 2 — Executor Boundary

```
Executor Boundary

executor_output_validated: YES (for all semantic artifacts)
executor_bypass_exists: YES (for non-semantic artifacts only)
details:
  - Semantic artifacts: executor → parse/validate → commit (enforced)
  - sampling-report: executor → write (no validation, intentional — operational artifact)
  - semantic-change-log: executor → write (no validation, intentional — operational log)
  - Baseline: executor → parse_baseline_output → validate_baseline_artifact → write_baseline
  - Refine patches: executor → stage_artifact(validate_fn) → commit_staged
```

Assessment: No executor output for semantic state reaches disk without validation. The two bypass paths are for non-semantic operational artifacts. **No safety violation.**

---

## PART 3 — Version Safety

```
Version Safety

version_monotonic: YES
  — _next_version (artifact_writer.py:62-67) returns max(existing) + 1

pruning_safe: YES
  — prune_old_versions (artifact_writer.py:112-143) skips accepted_versions
  — keep parameter ensures latest N versions survive
  — latest version always protected by the keep window

latest_valid_resolution: PARTIAL
  — get_latest_version_path (artifact_writer.py:82-96) skips empty files (st_size > 0)
  — does NOT skip structurally invalid (non-empty but malformed) files
  — downstream validation catches invalid content before it propagates
```

Note: `get_latest_version_path` returns the latest non-empty file, not the latest *valid* file. In the scenario v1(valid), v2(valid), v3(invalid), v4(invalid), it returns v4. However, this is safe because every consumer validates after reading — the pipeline halts on invalid content before it can propagate. The resolution is size-based, not schema-based, which is a deliberate simplicity tradeoff.

---

## PART 4 — Multi-Artifact Consistency

```
Multi-Artifact Consistency

atomic_commit: YES
partial_commit_possible: NO
```

`_execute_staged_patches` (refine_executor.py:238-314):
1. Stages repo-understanding with `stage_artifact(validate_fn=validate_refined_artifact)`
2. Stages knowledge-confidence with same validation
3. If either fails → returns immediately, nothing written
4. If both pass → `commit_staged()` writes both

Baseline writes (refine_executor.py:571-575): all 4 sections validated before any `write_baseline` call. If any section fails validation, the entire baseline step returns `validation_failed` and no files are written.

---

## PART 5 — Baseline Boundary

```
Baseline Boundary

baseline_readable_by_discovery: NO
baseline_readable_by_refine: NO
baseline_write_restricted: YES
```

- `get_latest_working_version_path` (artifact_writer.py:99-109) returns `None` for `category == "baseline"`
- `build_refine_context` reads only from discovery/review via `_read_latest_working_artifact`
- `build_baseline_context` reads only from discovery/review via `_read_latest_working_artifact`
- `write_baseline` is the sole baseline write function, called only from `_execute_baseline_step`
- Discovery pipeline never references baseline directory

---

## PART 6 — Acceptance Gate Safety

```
Acceptance Gate

acceptance_explicit_required: YES
false_acceptance_possible: NO
```

- `_check_acceptance` (refine_executor.py:105-115) requires exact line `acceptance: true` (case-insensitive value)
- Free-text mentions like "I accept" or "acceptance is true" do not match
- `evaluate_acceptance` (refine_executor.py:476-522) enforces 4 structural gates:
  1. `acceptance: true` field present
  2. knowledge-confidence has schema-defined sections
  3. repo-understanding has schema-defined sections
  4. domain-candidates is non-empty
- All 4 gates must pass; any failure blocks baseline synthesis
- No fuzzy matching or semantic inference in any gate

---

## PART 7 — Corruption Propagation

```
Corruption Handling

self_healing_supported: YES
validator_blocks_invalid: YES
```

Scenario A (self-healing): A capable executor receives bad source artifacts via context, produces valid patched output → validator passes → pipeline continues. Verified by test `test_scenario_a_good_executor_recovers_from_bad_source`.

Scenario B (halt on invalid): Executor produces malformed output → `validate_refined_artifact` rejects → staged flow prevents any writes → pipeline returns `validation_failed`. Verified by tests `test_scenario_a_truncated_artifact_with_bad_executor` and `test_previous_valid_artifacts_survive_failure`.

Both behaviors are supported and tested.

---

## PART 8 — Context Boundary

```
Context Boundary

context_sources_controlled: YES
unbounded_repo_access: NO (in refine/baseline paths)
```

- `build_refine_context` (context_builder.py:251-267): reads only `repo_understanding`, `knowledge_confidence`, `architect_feedback` — all from versioned artifacts
- `build_baseline_context` (context_builder.py:311-335): reads only `repo_understanding`, `knowledge_confidence`, `domain_candidates`, `review_summary` — all from versioned artifacts
- `build_repo_tree_summary` and `read_selected_files` (which access the filesystem) are only called from discovery context builders (`_ctx_repo_sampling`, `_ctx_repo_facts`, `_ctx_evidence_extraction`)
- No refine or baseline path triggers repository scanning

---

## PART 9 — Runtime Purity

```
Runtime Purity

test_code_in_runtime: NO
runtime_purity_preserved: YES
```

- Zero matches for `fake_executor`, `stub_executor`, or `from tests` in `src/`
- No external LLM SDK imports (openai, anthropic, langchain) in `src/`
- `HostExecutor` protocol (host_executor.py) is the sole execution interface
- `fake_executors.py` exists only in `tests/`

---

## FINAL REPORT

```
Semantic Harness Safety Audit

Validation Boundary: PASS
Executor Boundary: PASS
Version Safety: PASS
Multi-Artifact Consistency: PASS
Baseline Boundary: PASS
Acceptance Gate: PASS
Corruption Handling: PASS
Context Boundary: PASS
Runtime Purity: PASS

Overall Safety Verdict:
SYSTEM SAFE
```

No blocking safety issues detected. One non-blocking observation:

- `get_latest_version_path` resolves by file size (non-empty), not structural validity. Structurally invalid but non-empty files would be returned as "latest." This is safe because all consumers validate after reading, but a future hardening pass could add structural validation to version resolution if desired. This is a defense-in-depth improvement, not a safety violation — the current pipeline catches invalid content before it propagates.
