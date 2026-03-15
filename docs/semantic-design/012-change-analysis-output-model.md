# 012 — Change Analysis Output Model

## Context

Stage 3 introduces the minimum bridge from IBS Core artifacts to a
deterministic change-analysis artifact.

Inputs:

- `purpose.md`
- `pipelines.md`
- `domains.md`
- `concepts.md`

Output:

- `change-analysis` (versioned review artifact)

## Decision

Use a structural, deterministic synthesis model:

1. Read accepted IBS Core baseline artifacts.
2. Extract stable labeled fields (`Primary Purpose`, `Pipeline Name`,
   `Domain Name`, `Concept Name`, `Confidence`).
3. Generate a sectioned change-analysis artifact.
4. Validate required sections and minimal content shape before writing.

## Output Sections

- `Change Intent`
- `Affected Pipelines`
- `Affected Domains and Concepts`
- `Impact and Risks`
- `Suggested Next Changes`

## Constraints

- Do not generate implementation-plan in Stage 3.
- Do not redesign discovery/refine architecture.
- Keep change-analysis generation additive and post-IBS.

## Rationale

This preserves the staged architecture:

`repo -> facts -> IBS Core -> change-analysis -> implementation-plan`

and enables safe progression to Stage 4 without coupling Stage 3 to
full planning logic.
