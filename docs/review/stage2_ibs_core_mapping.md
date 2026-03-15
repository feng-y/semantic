# Stage 2 — IBS Core Mapping

## Goal

Synthesize existing FACT artifacts into IBS Core baseline outputs:

- `purpose.md`
- `pipelines.md`
- `domains.md`
- `concepts.md`

This stage is intentionally limited to IBS Core synthesis only.

## Source FACT Artifacts

- `repo-facts`
- `repo-understanding`
- `domain-candidates`
- `knowledge-confidence`
- `review-summary`

## Mapping Specification

### purpose

- Primary source: `repo-understanding` (`System Purpose`) and `review-summary` (`System Summary`)
- Supporting source: `repo-facts` (repository type, entrypoints, entities)
- Confidence overlay: `knowledge-confidence` (confirmed/inferred/uncertain markers)
- Output intent:
  - `Primary Purpose`
  - `Supported Scenarios`
  - `Non Goals`

### pipelines

- Primary source: `repo-understanding` (`Pipelines`)
- Supporting source: `review-summary` (`Pipelines` / `Main Pipelines`)
- Supporting source: `repo-facts` (`Entrypoints`, `Modules`)
- Confidence overlay: `knowledge-confidence`
- Output intent:
  - `Pipeline Name`
  - `Purpose`
  - `Flow`
  - `Inputs`
  - `Outputs`
  - `Concepts`
  - `Evidence`
  - `Confidence`

### domains

- Primary source: `domain-candidates` (`Candidate Domains`)
- Supporting source: `repo-understanding` (`Candidate Domains`)
- Supporting source: `review-summary` (`Candidate Domains`)
- Output intent:
  - `Domain Name`
  - `Description`
  - `Related Pipelines`

### concepts

- Primary source: `repo-understanding` (`Concepts`)
- Supporting source: `review-summary` (`Concepts` / `Core Concepts`)
- Supporting source: `repo-facts` (`Core Entities`)
- Confidence overlay: `knowledge-confidence`
- Output intent:
  - `Concept Name`
  - `Description`
  - `Role`
  - `Used By`
  - `Evidence`
  - `Confidence`

## Runtime Integration Notes

- Existing refine acceptance gates and baseline parser remain unchanged.
- Baseline prompt output remains a required runtime gate.
- IBS Core generation runs after baseline parser/validator gates pass.
- Generated IBS Core content is validated with baseline keyword contracts before write.

## IBS Core File Contracts (Source of Truth)

The generated file bodies must follow these contract fields:

### purpose.md

- `Primary Purpose`
- `Supported Scenarios`
- `Non Goals`

### pipelines.md

- `Pipeline Name`
- `Purpose`
- `Flow`
- `Inputs`
- `Outputs`
- `Concepts`
- `Evidence`
- `Confidence`

### domains.md

- `Domain Name`
- `Description`
- `Related Pipelines`

### concepts.md

- `Concept Name`
- `Description`
- `Role`
- `Used By`
- `Evidence`
- `Confidence`

These contracts align with:

- `docs/semantic/schemas/purpose.schema.md`
- `docs/semantic/schemas/pipelines.schema.md`
- `docs/semantic/schemas/domains.schema.md`
- `docs/semantic/schemas/concepts.schema.md`

## Non-Goals (Stage 2)

- No `change-analysis`
- No `implementation-plan`
- No runtime architecture redesign
