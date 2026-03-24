# Shared Bootstrap Quality Gates Implementation Plan

**Goal:** Add a final quality-gate layer over the completed shared-bootstrap chain (Subprojects 1–4) so the repo can deterministically answer: is the bootstrap contract healthy enough to trust, and if not, where does it fail? This subproject does **not** change bootstrap behavior semantics; it adds explicit quality gates, verification surfaces, and failure reporting over the now-completed contract → producer → consumer → reliability path.

**Architecture:** Subproject 5 is a gate-and-verification layer, not another semantic/runtime redesign. It should stand on top of the implemented artifacts and runtime behavior from Subprojects 1–4. The work splits into three parts: (1) deterministic gates on artifact shape and runtime summaries, (2) E2E verification that the full chain behaves consistently across extract + semantic consumption, and (3) explicit review/Codex-facing summary surfaces so quality status is easy to audit before accepting the milestone.

**Tech Stack:** Python 3.10+, pytest, JSON artifact IO, existing `SkillRunner` / `HarnessState`, current bootstrap/repo-context fixtures and E2E tests.

---

## Scope

### In scope
- Deterministic quality gates for shared bootstrap artifacts and runtime summaries
- Coverage that the completed Subprojects 1–4 work together end to end
- Clear pass/fail criteria for bootstrap trustworthiness
- Machine-testable and human-auditable verification output/surfaces
- Review/Codex-friendly closure contract

### Out of scope
- No new semantic extraction heuristics
- No producer ownership changes
- No semantic consumer precedence redesign
- No demand integration
- No new caching subsystem
- No new docs-prior logic beyond what is already shipped
- No expansion into general harness/CI framework outside the shared-bootstrap chain

---

## What Subproject 5 is gating

The completed chain now looks like:

```text
Subproject 1: shared repo-context contract
  -> Subproject 2: commit-extract producer
  -> Subproject 3: commit-semantic consumer migration
  -> Subproject 4: reliability layer (freshness/full-degraded-bypass/debug bypass)
```

Subproject 5 should gate the health of this chain at three levels:

1. **Artifact contract gate**
   - `repo-context.json` remains structurally valid and layered
2. **Runtime behavior gate**
   - producer and consumer honor precedence / reliability semantics
3. **Trust gate**
   - summary fields, degraded reasons, and bypass reasons remain explicit and auditable

---

## File Structure

### Files to modify
- `tests/test_shared_repo_context_contract.py`
  - Extend deterministic contract gates for summary/runtime fields now that Subproject 4 is complete
- `tests/test_commit_extract_reliability.py`
  - Add any missing deterministic gate assertions for final-mode semantics if needed
- `tests/e2e/test_commit_extract.py`
  - Ensure runtime gate scenarios are explicit and stable
- `tests/e2e/test_pipeline_e2e.py`
  - Ensure cross-subproject chain is exercised from producer to semantic consumer
- `skills/commit-extract/SKILL.md`
  - Document final trust/gate semantics only if code/tests prove them
- `skills/commit-semantic/SKILL.md`
  - Document the final consumer-side gate assumptions only if needed

### Files to create
- `tests/test_shared_bootstrap_quality_gates.py`
  - Focused deterministic gate suite for final milestone-level quality checks
- `tests/fixtures/shared_repo_context/invalid_runtime_summary.json`
  - Fixture for invalid/misaligned runtime summary cases
  - Used to lock that invalid persisted runtime summaries are rejected into deterministic bypass rather than silently reinterpreted
- `docs/superpowers/plans/2026-03-24-shared-bootstrap-quality-gates.md`
  - This plan file (current file)

### Files to inspect / reuse
- `skills/commit-extract/bootstrap.py`
- `skills/commit-extract/run.py`
- `skills/commit-semantic/run.py`
- `tests/test_commit_extract_bootstrap.py`
- `tests/test_commit_semantic_context_resolution.py`
- `tests/fixtures/shared_repo_context/example_repo_context.json`
- `tests/fixtures/commit_extract_bootstrap/*.json`

---

## Quality gate model

### Gate A — Contract integrity
Shared repo-context must satisfy:
- top-level keys: `shared_hints`, `semantic_context`, `summary`
- `summary.bootstrap_status` in `full|degraded|bypass`
- `summary.hint_count` matches actual shared hint counting rules
- `summary.source_counts` matches snapshot counts
- `summary.used_cached_context` is bool
- `summary.degraded_reasons` is list
- `summary.bypass_reason` is string or null
- `summary.fingerprint` exists and is stable for same inputs

### Gate B — Producer runtime semantics
`commit-extract` collect must prove:
- fresh valid context -> `full` or `degraded` according to helper rules
- explicit `--skip-bootstrap` -> `bypass`
- degraded with reduced hints injects reduced `shared_hints`
- degraded with empty hints injects no shared hints
- persisted bypass stays bypass

### Gate C — Consumer runtime semantics
`commit-semantic` must prove:
- shared extract context takes precedence over local semantic context when valid
- malformed shared extract context falls back safely to local semantic artifact
- downstream consumes `semantic_context` only, not full layered object

### Gate D — Cross-chain integration
Full chain must prove:
- producer writes valid shared context
- consumer uses producer context when present
- runtime summary semantics do not contradict actual runtime behavior
- no Subproject 4 reliability behavior breaks Subproject 3 consumer expectations

### Gate E — Reviewability
A reviewer or Codex should be able to inspect a small stable set of files/tests and answer whether shared bootstrap is trustworthy without reconstructing the whole history.

---

## Execution order

1. **Checkpoint 1 — Final deterministic gate suite**
2. **Checkpoint 2 — Cross-chain E2E closure**
3. **Checkpoint 3 — Review/Codex audit surface**

Do not start the next checkpoint until the current checkpoint tests are green.

---

## Checkpoint 1 — Final deterministic gate suite

### Task 1: Add focused final quality-gate tests

**Files:**
- Create: `tests/test_shared_bootstrap_quality_gates.py`
- Modify: `tests/test_shared_repo_context_contract.py`

- [ ] **Step 1: Write focused gate tests**
Add tests for:
- contract validity of final `summary` semantics
- helper/runtime summary agreement on the same artifact
- persisted bypass remains bypass
- degraded reasons stay explicit and machine-readable
- `hint_count` and `source_counts` stay contract-aligned

- [ ] **Step 2: Run tests to verify RED (if new assertions expose drift)**
Run:
```bash
pytest tests/test_shared_bootstrap_quality_gates.py tests/test_shared_repo_context_contract.py -q
```
Expected: either RED (if drift exists) or immediate GREEN.

- [ ] **Step 3: Implement minimal fixes only if needed**
If tests expose contract drift, fix the smallest violating surface only.

- [ ] **Step 4: Re-run tests to verify GREEN**
Run the same suite until green.

---

## Checkpoint 2 — Cross-chain E2E closure

### Task 2: Lock the producer → consumer chain with explicit gates

**Files:**
- Modify: `tests/e2e/test_commit_extract.py`
- Modify: `tests/e2e/test_pipeline_e2e.py`
- Reuse: `tests/test_commit_semantic_context_resolution.py`

- [ ] **Step 1: Add or tighten chain assertions**
Ensure the E2E surface explicitly proves:
- extract writes runtime summary fields expected by reliability layer
- semantic consumer prefers shared context from extract
- degraded / bypass producer behavior does not leak malformed semantics downstream

- [ ] **Step 2: Run targeted E2E tests**
Run:
```bash
pytest tests/e2e/test_commit_extract.py tests/e2e/test_pipeline_e2e.py tests/test_commit_semantic_context_resolution.py -q
```
Expected: GREEN.

- [ ] **Step 3: Fix only genuine chain gaps**
Do not redesign behavior. Fix only contradictions between already-implemented semantics and gate expectations.

---

## Checkpoint 3 — Review/Codex audit surface

### Task 3: Make closure review cheap and explicit

**Files:**
- Modify if needed: `skills/commit-extract/SKILL.md`
- Modify if needed: `skills/commit-semantic/SKILL.md`

- [ ] **Step 1: Ensure docs match actual shipped behavior**
Document only proven semantics:
- `full / degraded / bypass`
- `--skip-bootstrap`
- consumer precedence expectations
- operational summary fields

- [ ] **Step 2: Run final milestone verification suite**
Run:
```bash
pytest tests/test_shared_repo_context_contract.py tests/test_shared_bootstrap_quality_gates.py tests/test_commit_extract_reliability.py tests/test_commit_extract_bootstrap.py tests/test_commit_semantic_context_resolution.py tests/e2e/test_commit_extract.py tests/e2e/test_commit_semantic.py tests/e2e/test_pipeline_e2e.py -q
```
Expected: GREEN.

- [ ] **Step 3: Final review and Codex review**
Repeat the established closure ritual:
- local verification
- reviewer pass
- verifier pass
- Codex review

---

## Acceptance criteria

Subproject 5 is complete when all of the following are true:

- Shared bootstrap has a deterministic final gate suite
- Final runtime summary semantics are explicitly locked by tests
- Producer runtime modes and consumer precedence are proven together end to end
- Review/Codex can inspect a small stable surface and find no remaining concrete issues
- The completed Subprojects 1–4 are now guarded by explicit pass/fail quality gates instead of only ad hoc milestone review

---

## Notes for implementers

- This subproject should feel **boring**: mostly assertions, no large behavior redesign.
- Prefer tightening tests over inventing new runtime complexity.
- If a gate fails, fix the smallest inconsistency that makes the chain untrustworthy.
- Do not let this become a generic CI/harness project; it is specifically about the shared-bootstrap chain.
