
# Semantic Harness — P1/P2 Hardening & Review Execution Plan
(Claude Code Execution Guide)

This document is a **single execution plan** for Claude Code to:

1. verify remaining architectural risks
2. implement necessary P1 fixes
3. optionally implement safe P2 improvements
4. run review after fixes
5. produce a **final development + review report**

The goal is to **raise system completeness and robustness before declaring v1 stable**.

---

# Execution Rules

Claude Code must follow these rules:

- Prefer **verification first, fixes second**
- Only modify code if a real issue is confirmed
- Keep architecture intact
- Maintain runtime purity
- Do not introduce external dependencies
- Do not redesign the pipeline

Pipeline under verification:

init → discover → refine → baseline

---

# Part 1 — Schema & Runtime Alignment Check (P1)

Verify that runtime artifact formats fully align with schema definitions in:

docs/fact/schemas/

Artifacts to verify:

- repo-understanding
- knowledge-confidence
- domain-candidates
- review-summary

Baseline artifacts:

- purpose
- domains
- concepts
- pipelines

Check:

1. schema headings
2. validator logic
3. acceptance gate logic
4. parser expectations
5. executor outputs

Required condition:

All components must expect **the same structural contract**.

If mismatch exists:

- modify validator or parser
- do NOT silently tolerate mismatch

Output:

Schema Alignment Review
result: PASS / ISSUE
fixes applied: ...

---

# Part 2 — Multi-Artifact Atomicity (P1)

Verify that refine updates multiple artifacts atomically.

Focus:

repo-understanding + knowledge-confidence

Check pipeline behavior:

stage → validate → commit

Failure cases:

- validation failure of one artifact
- executor output malformed
- write failure

Required condition:

Partial state must **never become working state**.

If problem detected:

Implement staged write or commit grouping.

Output:

Artifact Atomicity Review
result: PASS / ISSUE
fixes applied: ...

---

# Part 3 — Baseline Parser Contract (P1)

Verify strictness of baseline parser.

Required headings:

## Purpose
## Domains
## Concepts
## Pipelines

Check:

- missing section → fail
- duplicate section → fail
- malformed heading → fail
- reordered sections → allowed
- extra sections → ignored safely

If parser too permissive:

tighten validation.

Output:

Baseline Parser Review
result: PASS / ISSUE
fixes applied: ...

---

# Part 4 — Semantic Snapshot / Checkpoint Consistency (P1)

Verify that snapshot metadata correctly reflects artifact versions.

Check:

- snapshot created only after successful pipeline completion
- snapshot records artifact versions
- recovery detects version skew

Simulate:

repo-understanding.v3
knowledge-confidence.v2

Expected:

system detects mismatch.

If not implemented:

add consistency validation before refine/baseline.

Output:

Snapshot Consistency Review
result: PASS / ISSUE
fixes applied: ...

---

# Part 5 — Failure Recovery Behavior (P1)

Simulate failures:

1. truncated artifact
2. malformed markdown
3. missing schema section
4. executor failure
5. baseline generation failure

Verify:

- system halts safely
- last valid artifacts preserved
- rerun recovers state

If failure recovery unsafe:

implement guards.

Output:

Failure Recovery Review
result: PASS / ISSUE
fixes applied: ...

---

# Part 6 — Observability Improvements (P2)

Check if system produces sufficient runtime insight.

Suggested improvements:

- step execution summary
- artifact write log
- validation error summary
- pipeline halt reason
- checkpoint summary

If missing:

implement lightweight logging.

Output:

Observability Review
result: PASS / ISSUE
changes applied: ...

---

# Part 7 — Documentation Consistency (P2)

Verify documentation consistency across:

architecture docs
invariants docs
runtime purity docs
schema docs

Check:

- docs reflect current behavior
- no outdated assumptions

If mismatch exists:

update docs.

Output:

Documentation Review
result: PASS / ISSUE
updates applied: ...

---

# Part 8 — Automated Failure Tests (P2)

Add minimal automated tests for:

- corrupted artifact
- missing schema section
- invalid baseline output
- version skew

Tests should verify that system halts safely.

Output:

Failure Test Suite
result: PASS / ISSUE
tests added: ...

---

# Final Report

Claude Code must produce the following final report.

Semantic Harness Hardening Report

Schema Alignment: PASS / ISSUE
Artifact Atomicity: PASS / ISSUE
Baseline Parser: PASS / ISSUE
Snapshot Consistency: PASS / ISSUE
Failure Recovery: PASS / ISSUE
Observability: PASS / ISSUE
Documentation Consistency: PASS / ISSUE
Failure Tests: PASS / ISSUE

Fixes Implemented:
- ...

Remaining Risks:
- ...

Overall Verdict:

SYSTEM READY FOR V1
or
ADDITIONAL HARDENING REQUIRED

---

# Execution Instruction

Claude Code should:

1. run the verification tasks above
2. apply fixes where issues are confirmed
3. re-run review after fixes
4. produce the final report
