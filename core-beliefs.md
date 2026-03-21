# Core Beliefs — Golden Principles

These are non-negotiable. Every decision should be traceable to one of these beliefs.

## 1. Artifacts Are First-Class

Versioned artifacts in `docs/fact/` are the primary output and contract. They are not byproducts — they are the product. Every pipeline step writes, validates, or transforms artifacts. Nothing is "just for logging."

## 2. Evidence Over Assertion

Every semantic claim needs evidence — file paths, commit SHAs, code excerpts. The LLM must cite sources. Without evidence, the claim is rejected at validation.

## 3. Immutable Baseline, Mutable Working State

`docs/fact/baseline/` is sacred — written once, never overwritten. `docs/fact/discovery/` and `docs/fact/review/` are working state — safe to rewrite, version, prune. The refine loop promotes working state into baseline.

## 4. Acceptance Is Explicit

The architect must write `acceptance: true` in `architect-feedback.md` to trigger baseline synthesis. No implicit acceptance. No majority-vote. The human decides when the model is ready.

## 5. Validation Before Persistence

Every artifact is validated against its schema before being written. Invalid artifacts are rejected; prior valid artifacts are preserved. The pipeline halts on validation failure — never writes garbage.

## 6. Versioning Is Automatic

The system manages artifact versions (`.vN.md`). Agents should not manually manage version numbers. The versioning protocol handles pruning (keep latest 3), migration, and traceability.

## 7. Skills Are Self-Describing

Every skill has a `SKILL.md` that defines triggers, description, workflow, and output. Skills are invoked via natural language in Claude Code and routed via `skill_loader.py`. No skill should be a black box.

## 8. Pipeline Steps Are Ordered and Recorded

Each pipeline step records its action, target, status, and artifact path. The full execution trace is returned in the result dict. This enables debugging, reproducibility, and recovery from partial failures.

## 9. Incremental Is the Default

Where possible, prefer incremental updates over full rewrites. The change detector, deduplication, and versioning system all support incremental operation. Full rebuilds are opt-in.

## 10. Tests Are Fast and Deterministic

Tests should be unit-level by default, use fake executors, and run in <1s. E2E tests with real LLMs are clearly labeled and opt-in. Non-determinism in tests is a P0 bug.
