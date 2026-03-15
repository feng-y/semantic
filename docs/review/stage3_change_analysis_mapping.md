# Stage 3 — Change Analysis Mapping

## Goal

Implement the minimum bridge from IBS Core to change-analysis:

- Inputs: `purpose.md`, `pipelines.md`, `domains.md`, `concepts.md`
- Output: `change-analysis`

## Current Stage 3 Semantics

Current Stage 3 is **IBS Core -> generic semantic impact analysis**.

- It is grounded in the accepted IBS Core snapshot only.
- It does not yet consume explicit external change request/context input.
- Request-specific change intent interpretation is deferred to a later stage.

## Mapping

### 1) Change Intent

- Source: `purpose.md`
- Mapping:
  - `Primary Purpose` -> intent anchor sentence
  - first item of `Supported Scenarios` (if present) -> prioritization hint in next changes
  - first items of `Non Goals` (if present) -> boundary statement

### 2) Affected Pipelines

- Source: `pipelines.md`
- Mapping:
  - `Pipeline Name` -> affected pipeline names list
  - Stage 3 currently lists names only (no per-pipeline flow/purpose impact notes)

### 3) Affected Domains and Concepts

- Source: `domains.md`, `concepts.md`
- Mapping:
  - `Domain Name` -> affected domain names list
  - `Concept Name` -> affected concept names list

### 4) Impact and Risks

- Source: `pipelines.md`, `concepts.md`
- Mapping:
  - top pipeline/domain names -> impact surface summary
  - low `Confidence` markers in IBS Core text -> risk bullet items

### 5) Suggested Next Changes

- Source: all IBS Core artifacts
- Mapping:
  - generic next-step guidance anchored to supported scenario (if present)
  - pipeline-first semantic update order
  - semantic validation/testing follow-up recommendation

## Output Contract

`change-analysis` must contain these sections:

- `Change Intent`
- `Affected Pipelines`
- `Affected Domains and Concepts`
- `Impact and Risks`
- `Suggested Next Changes`

## Stage 3 Scope Guard

- Includes only IBS Core -> change-analysis bridge.
- Excludes implementation-plan generation.
- Excludes full IBS analysis pack.
- Excludes request-context ingestion pipeline (deferred).
