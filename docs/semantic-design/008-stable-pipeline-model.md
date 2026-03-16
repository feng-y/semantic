
# 008 — Semantic Harness Stable Pipeline Model

## Purpose

This document defines the **stable execution model of Semantic Harness v1**.

Goals:

- deterministic semantic construction
- explicit versioned artifacts
- bounded AI execution
- architect‑controlled convergence

All semantic state lives inside the repository:

```
docs/fact/
```

---

# 1. Phase Model

The system runs in **five phases**.

```
Bootstrap
   ↓
Discovery
   ↓
Review
   ↓
Refinement
   ↓
Baseline
```

---

## Phase 0 — Bootstrap

Command:

```
init
```

Creates workspace:

```
docs/fact/schemas/
docs/fact/discovery/
docs/fact/review/
docs/fact/baseline/
```

Default files:

```
docs/fact/discovery/sampling-report.md
docs/fact/review/architect-feedback.md
docs/fact/review/semantic-change-log.md
```

Rules:

- never overwrite existing files
- minimal setup only

---

## Phase 1 — Discovery

Command:

```
discover
```

Purpose:

Extract semantic understanding from the repository.

Generated artifacts:

```
repo-facts.vN.md
domain-candidates.vN.md
repo-understanding.vN.md
knowledge-confidence.vN.md
review-summary.vN.md
```

Sampling report:

```
sampling-report.md
```

All artifacts are **versioned working state**.

---

## Phase 2 — Review

Human architect reviews results.

Feedback location:

```
docs/fact/review/architect-feedback.md
```

Architect may:

- confirm correctness
- correct wrong assumptions
- add missing domain knowledge
- mark acceptance

Acceptance example:

```
acceptance: semantic baseline accepted
```

---

## Phase 3 — Refinement

Command:

```
refine
```

Inputs:

- latest semantic artifacts
- architect-feedback.md

Actions:

```
patch artifacts
preserve evidence
generate semantic-change-log
create new artifact versions
```

Outputs:

```
updated versioned artifacts
semantic-change-log.md
```

---

## Phase 4 — Baseline

Triggered by architect acceptance.

Output directory:

```
docs/fact/baseline/
```

Baseline represents **stable semantic reference**.

Baseline artifacts are never pruned.

---

# 2. Discovery Pipeline

Execution order:

```
sampling
→ repo-facts
→ evidence augmentation
→ validate repo-facts
→ domain candidates
→ repo-understanding
→ validate repo-understanding
→ knowledge-confidence
→ review-summary
→ artifact versioning
```

---

## Sampling

Prompt:

```
repo-sampling.prompt
```

Output:

```
sampling-report.md
```

Modes:

```
auto
confirm
```

---

## Repo Facts

Prompt:

```
repo-facts.prompt
```

Output:

```
repo-facts.vN.md
```

Facts must reference repository evidence.

---

## Evidence Augmentation

Prompt:

```
evidence-extraction.prompt
```

Behavior:

```
read latest repo-facts
append evidence
write new version
```

---

## Validation

Prompt:

```
validate-artifact.prompt
```

If validation fails:

```
pipeline stops
```

---

## Domain Candidates

Prompt:

```
domain-candidates.prompt
```

Output:

```
domain-candidates.vN.md
```

---

## Repo Understanding

Prompt:

```
repo-understanding.prompt
```

Output:

```
repo-understanding.vN.md
```

---

## Knowledge Confidence

Prompt:

```
knowledge-confidence.prompt
```

Output:

```
knowledge-confidence.vN.md
```

---

## Review Summary

Prompt:

```
review-summary.prompt
```

Location:

```
docs/fact/review/
```

Output:

```
review-summary.vN.md
```

---

## Artifact Versioning

Protocol:

```
artifact-versioning.md
```

Retention policy:

```
keep latest 3 versions
```

Never prune:

```
accepted artifacts
baseline artifacts
```

---

# 3. Refinement Pipeline

Refinement steps:

```
load latest artifacts
→ apply architect feedback
→ patch artifacts
→ generate semantic-change-log
→ validate artifacts
→ create new versions
→ baseline synthesis (if accepted)
```

Key rule:

```
patch instead of rewrite
```

---

# 4. Core Rules

## Evidence First

All semantic claims must reference repository evidence.

---

## Patch Not Rewrite

Refinement must modify artifacts incrementally.

---

## Validation Before Replace

Invalid artifacts cannot replace valid versions.

---

## Versioned Working State

Working artifacts are versioned.

Default retention:

```
3 versions
```

---

## Human Acceptance Authority

Baseline creation requires architect approval.

AI cannot finalize semantic state independently.

---

## Visible Sampling

Sampling must produce a visible report.

---

# Summary

Semantic Harness v1 is:

**an evidence‑driven semantic construction pipeline with versioned artifacts and human‑controlled convergence.**
