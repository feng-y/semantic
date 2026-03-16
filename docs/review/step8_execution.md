# Step 8 — Semantic Harness System Verification & Review Guide for Claude Code

This document is the **single instruction file** for Claude Code to execute **Step 8**.

Step 8 is **not feature development**.  
It is the final **system verification, failure hardening, and release-readiness review** stage for Semantic Harness v1.

Claude Code should use this file as the primary execution guide.

---

# Scope

The system under verification is:

```text
init
→ discover
→ refine
→ baseline
```

The goals of Step 8 are:

1. verify end-to-end determinism
2. verify failure safety
3. verify version integrity
4. verify prompt/output contract robustness
5. verify global system invariants
6. produce a final release-readiness assessment

---

# Execution Rules

Claude Code must follow these rules during Step 8:

- do not redesign architecture
- do not add new features unless needed to fix a verified failure
- prefer verification first, fixes second
- if a failure is found, explain the exact root cause
- keep runtime purity intact
- do not reintroduce stub logic into core runtime
- keep baseline immutable
- keep context bounded and artifact-based

---

# Part A — Step 8 Execution

## 1. End-to-End Determinism Test

Run the full pipeline multiple times on the same repository and compare results.

### Procedure

1. Prepare a clean working state while preserving required repo structure.
2. Run:
   - discover
   - refine
   - baseline synthesis (only when acceptance conditions are met)
3. Repeat the full process at least **3 times**.

### Verify

- semantic artifacts are identical across runs
- baseline artifacts are identical across runs
- version numbers behave consistently
- snapshot / checkpoint metadata is consistent
- no hidden nondeterminism appears between runs

### Fail Conditions

- artifacts differ across runs
- baseline differs across runs
- version numbers diverge unexpectedly
- pipeline behavior differs across runs with identical input state

### Required Report Format

```text
Determinism Test
runs: N
result: PASS / ISSUE
differences: ...
```

---

## 2. Failure Injection Tests

Simulate corrupted or malformed artifacts and verify the system halts safely.

### Scenario A — Truncated Artifact

Corrupt one of:

- repo-understanding
- knowledge-confidence

Expected:

- validation fails
- pipeline halts
- no new artifacts written
- previous valid artifacts remain intact

### Scenario B — Missing Required Section

Remove a required structural section from an artifact.

Expected:

- validation fails
- baseline synthesis is blocked if required state is incomplete

### Scenario C — Corrupted Markdown / Malformed Structure

Insert malformed headings or invalid markdown structure.

Expected:

- parser or validator rejects it
- no corrupted state propagates

### Required Report Format

```text
Failure Injection
scenario: ...
result: PASS / ISSUE
pipeline behavior: ...
```

---

## 3. Version Integrity Tests

Simulate edge cases in version history.

### Test A — Invalid Newer Versions

Create a history like:

```text
repo-understanding.v1 (valid)
repo-understanding.v2 (valid)
repo-understanding.v3 (invalid)
repo-understanding.v4 (invalid)
repo-understanding.v5 (invalid)
```

Verify:

- pruning cannot delete the only valid artifact
- protected / accepted versions survive pruning
- latest-version resolution ignores invalid artifacts where applicable

### Test B — Version Skew

Create a state like:

```text
repo-understanding.v3
knowledge-confidence.v2
```

Verify:

- semantic snapshot detects inconsistency
- pipeline warns or halts safely
- inconsistent semantic state is not treated as valid

### Required Report Format

```text
Version Integrity
test: ...
result: PASS / ISSUE
details: ...
```

---

## 4. Prompt / Output Contract Robustness

Simulate malformed host-executor outputs.

### Case A — Missing Required Baseline Section

Remove one required heading, for example:

```text
## Domains
```

Expected:

- parser rejects output
- baseline is not written

### Case B — Reordered Required Headings

Reorder:

```text
## Purpose
## Domains
## Concepts
## Pipelines
```

Expected:

- heading-driven parser still succeeds if all required headings exist

### Case C — Extra Unexpected Section

Add:

```text
## RandomSection
```

Expected:

- extra section is ignored safely or rejected consistently
- required sections still determine validity

### Required Report Format

```text
Prompt Contract Test
case: ...
result: PASS / ISSUE
```

---

## 5. Global Invariant Verification

Verify that the system still satisfies the core invariants.

## Invariant 1 — Artifact Schema Invariant

Check that:

- runtime artifact format
- validation logic
- acceptance evaluator logic
- parsing logic

all align with:

```text
docs/fact/schemas/
```

## Invariant 2 — Semantic State Invariant

Check that the working semantic state remains internally consistent.

In particular:

- related artifacts advance consistently
- partial semantic state cannot become valid state

## Invariant 3 — Baseline Boundary Invariant

Check that:

- discovery never reads baseline
- refine never reads baseline
- only baseline synthesis writes baseline

## Invariant 4 — Deterministic Gate Invariant

Check that all gates remain structural and deterministic.

No fuzzy semantic inference is allowed for:

- validation
- acceptance
- baseline generation

## Invariant 5 — Context Boundary Invariant

Check that prompt context remains:

- bounded
- artifact-based
- deterministic

No uncontrolled repository scanning should occur in refine/baseline paths.

### Required Report Format

```text
Invariant Check
schema invariant: PASS / ISSUE
semantic state invariant: PASS / ISSUE
baseline boundary invariant: PASS / ISSUE
deterministic gate invariant: PASS / ISSUE
context boundary invariant: PASS / ISSUE
```

---

# Part B — Step 8 Review

After running the execution tests above, perform a full architecture review.

## Review Checklist

### 1. Runtime Purity

Verify:

- no stub logic in `src/`
- no fake executor reachable from runtime
- no external LLM SDK introduced
- host execution model still intact

### 2. Artifact Atomicity

Verify:

- multi-artifact updates cannot leave partial semantic state
- refine does not commit only one artifact if another fails
- baseline writes are not partial

### 3. Baseline Immutability

Verify:

- baseline remains a terminal layer
- no working-state helper reads baseline
- baseline artifacts are not modified by discover/refine

### 4. Acceptance Gate Safety

Verify:

- baseline runs only when `acceptance: true`
- structural gates prevent accidental baseline generation
- no fuzzy acceptance logic exists

### 5. Metadata Integrity

Verify:

- checkpoint / snapshot metadata accurately reflects source artifact versions
- metadata is not treated as semantic state

### 6. Recovery Behavior

Verify:

- rerunning after failure recovers safely
- corrupted intermediate state does not permanently block the system
- valid prior artifacts remain usable

### Required Review Output Format

```text
Architecture Review

Runtime Purity: PASS / ISSUE
Artifact Atomicity: PASS / ISSUE
Baseline Immutability: PASS / ISSUE
Acceptance Gate Safety: PASS / ISSUE
Metadata Integrity: PASS / ISSUE
Recovery Behavior: PASS / ISSUE
```

---

# Part C — Final Release Assessment

Claude Code must produce a final release-readiness summary.

## Final Summary Format

```text
Semantic Harness Step 8 Result

Determinism: PASS / ISSUE
Failure Safety: PASS / ISSUE
Version Integrity: PASS / ISSUE
Prompt Contract Safety: PASS / ISSUE
Global Invariants: PASS / ISSUE
Architecture Review: PASS / ISSUE

Overall Verdict:
STABLE FOR V1
or
HARDENING REQUIRED

Blocking Issues:
- ...
Non-Blocking Issues:
- ...
Recommended Next Actions:
- ...
```

---

# Required Output Deliverables

Claude Code should produce:

1. a structured Step 8 execution report
2. a structured Step 8 architecture review
3. a final release-readiness verdict
4. a list of any blocking or non-blocking issues discovered

---

# Important Note

Step 8 should **prefer verification over implementation**.

Only if a real failure is discovered should Claude Code propose and apply a focused fix.

Do not expand scope beyond system verification and release hardening.
