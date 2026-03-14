# 010 — Runtime Purity Principle

## Purpose

This document defines a hard rule for Semantic Harness implementation:

**step-by-step implementation does not justify stub execution inside core runtime.**

Stub behavior belongs to:

- tests
- dev-only harnesses
- fake executors used outside formal runtime

Stub behavior must **not** exist in the formal semantic construction execution path.

---

## Core Principle

Semantic Harness is a **semantic state system**.

Its outputs are not disposable demo strings. They become repository state:

- `repo-facts`
- `repo-understanding`
- `knowledge-confidence`
- `review-summary`
- `baseline`

Because these artifacts are persistent semantic state, the core runtime must never generate fake semantic artifacts through stub execution.

---

## Formal Runtime Path

The only valid formal execution path is:

```text
prompt_loader
→ context_builder
→ host prompt execution
→ validation
→ artifact_writer
→ versioning
```

Where:

- `prompt_loader` loads prompt definitions
- `context_builder` assembles bounded context
- `host prompt execution` is provided by the host environment (Claude Code)
- `validation` checks schema and semantic rules
- `artifact_writer` persists artifacts safely
- `versioning` maintains working-state lineage

---

## Forbidden Runtime Pattern

The following design is forbidden in formal runtime:

```text
prompt_loader
→ host executor
or
→ stub executor
→ artifact_writer
```

This is forbidden because it creates two incompatible semantic meanings for the same runtime:

- real semantic execution
- fake semantic execution

That makes semantic state untrustworthy.

---

## Required Behavior When Host Execution Is Unavailable

If host prompt execution is unavailable, core runtime must:

1. return `not_implemented` or `execution_error`
2. stop the pipeline
3. avoid writing fake semantic artifacts
4. preserve the last valid artifact state

Core runtime must **not** silently fall back to stub generation.

---

## Where Stub Is Allowed

Stub execution is allowed only in:

- `tests/`
- `dev_harness/`
- explicit fake executor utilities used for testing
- local isolated debugging tools outside formal runtime

These test-only paths must not write misleading semantic artifacts into the formal repository state unless explicitly marked as test output.

---

## Implementation Rule

Step-by-step delivery should follow this rule:

- incomplete core runtime returns clear `not_implemented`
- completed runtime uses only the formal host execution path
- fake execution is isolated outside core runtime

This keeps development iterative without polluting runtime semantics.

---

## Why This Rule Matters

Without runtime purity, Semantic Harness can produce artifacts that look valid but are not semantically trustworthy.

That would corrupt:

- architect review
- refinement
- acceptance
- baseline synthesis

In a semantic state system, fake intermediate state is more dangerous than an explicit unimplemented error.

---

## Final Rule

**Step-by-step implementation is an implementation strategy, not a runtime semantic.**

**Stub is a testing tool, not a core runtime capability.**
