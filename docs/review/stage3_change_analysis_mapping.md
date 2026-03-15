# Stage 3 — Change Analysis Mapping

## Goal

Implement the minimum bridge from IBS Core to change analysis:

- Inputs: `purpose.md`, `pipelines.md`, `domains.md`, `concepts.md`
- Output: `change-analysis`

## Mapping

### 1) Change Intent

- Source: `purpose.md`
- Mapping:
  - `Primary Purpose` -> core change intent statement
  - `Supported Scenarios` -> intended scope of change
  - `Non Goals` -> explicit change boundaries

### 2) Affected Pipelines

- Source: `pipelines.md`
- Mapping:
  - `Pipeline Name` -> affected pipeline list
  - `Purpose` / `Flow` -> short impact notes per pipeline

### 3) Affected Domains and Concepts

- Source: `domains.md`, `concepts.md`
- Mapping:
  - `Domain Name` -> affected domain list
  - `Concept Name` -> affected concept list
  - `Related Pipelines` / `Used By` -> relationship hints

### 4) Impact and Risks

- Source: `pipelines.md`, `concepts.md`
- Mapping:
  - `Confidence` fields -> risk signals
  - pipeline/domain/concept coverage -> impact surface summary

### 5) Suggested Next Changes

- Source: all IBS Core artifacts
- Mapping:
  - prioritize updates around affected pipelines/domains/concepts
  - recommend focused validation/test follow-up from impact/risk signals

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
