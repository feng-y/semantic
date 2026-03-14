
# 009 — Prompt Context Contract

## Purpose

This document defines the **context contract** used by Semantic Harness prompts.

The goal is to ensure:

- predictable prompt inputs
- bounded token usage
- deterministic semantic construction
- avoidance of "entire repo" context explosion

Prompts must **only receive explicitly defined inputs**.

---

# 1. Context Sources

All prompt context must come from one of the following controlled sources:

1. Repository structure
2. Selected source files
3. Existing semantic artifacts
4. Sampling results
5. Architect feedback

No prompt may arbitrarily read the entire repository.

---

# 2. Context Categories

## Repository Structure

A summarized view of the repository tree.

Example:

```
repo_tree_summary
```

Generated from:

```
git ls-files
```

Used for:

- repo-facts
- domain-candidates

---

## Selected Files

A limited set of files chosen during sampling.

Defined by:

```
sampling-report.md
```

Prompts must only read files listed in the sampling report.

---

## Semantic Artifacts

Existing semantic state generated earlier in the pipeline.

Examples:

```
repo-facts.vN.md
repo-understanding.vN.md
domain-candidates.vN.md
```

These artifacts represent the **current semantic model**.

---

## Sampling Results

```
docs/semantic/discovery/sampling-report.md
```

Contains:

- selected directories
- representative files
- sampling strategy

This ensures discovery does not scan the entire repository.

---

## Architect Feedback

```
docs/semantic/review/architect-feedback.md
```

Only used in refinement steps.

---

# 3. Prompt Context Rules

## Rule 1 — Explicit Context Only

Prompts must not fetch additional files outside the provided context.

---

## Rule 2 — Bounded File Input

Maximum recommended input size:

```
10–20 files
```

Large repositories must rely on sampling.

---

## Rule 3 — Artifact First

When semantic artifacts exist, prompts must prefer them over raw repository scanning.

---

## Rule 4 — Context Determinism

Two runs with the same repository state must produce identical prompt context.

---

# 4. Context Contracts by Prompt

## repo-sampling.prompt

Inputs:

- repository tree summary

Outputs:

```
sampling-report.md
```

---

## repo-facts.prompt

Inputs:

- sampling-report
- selected files
- repo tree summary

Outputs:

```
repo-facts.vN.md
```

---

## evidence-extraction.prompt

Inputs:

- latest repo-facts artifact
- selected files

Outputs:

```
repo-facts.vN+1.md
```

---

## domain-candidates.prompt

Inputs:

- repo-facts artifact

Outputs:

```
domain-candidates.vN.md
```

---

## repo-understanding.prompt

Inputs:

- repo-facts artifact
- domain-candidates artifact

Outputs:

```
repo-understanding.vN.md
```

---

## knowledge-confidence.prompt

Inputs:

- repo-understanding artifact

Outputs:

```
knowledge-confidence.vN.md
```

---

## review-summary.prompt

Inputs:

- repo-understanding
- knowledge-confidence

Outputs:

```
review-summary.vN.md
```

---

# 5. Execution Model

Prompt execution follows this model:

```
prompt_loader
      ↓
context_builder
      ↓
host_prompt_execution
      ↓
artifact_validation
      ↓
artifact_writer
```

Semantic Harness never directly calls an external LLM SDK.

The host environment (Claude Code) executes prompts.

---

# 6. Design Principle

Semantic Harness treats prompts as **deterministic semantic transformations**:

```
controlled inputs
        ↓
prompt reasoning
        ↓
validated artifact
```

This contract prevents:

- uncontrolled repository scanning
- token explosion
- semantic drift

