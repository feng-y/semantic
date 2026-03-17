# Stage 3 Change Analysis — Input/Output Mapping

This document maps the baseline artifact fields to the change-analysis output sections.

## Input Sources

The change-analysis generator reads from four baseline artifacts:

- `purpose.md` — primary purpose, supported scenarios, non-goals
- `pipelines.md` — pipeline names, flows, inputs, outputs, confidence
- `domains.md` — domain names, descriptions, related pipelines
- `concepts.md` — concept names, roles, evidence, confidence

## Output Sections

### Change Intent

Derived from `purpose.md`. Summarizes what changed relative to the stated primary purpose
and non-goals. Flags any drift from the original intent.

### Affected Pipelines

Derived from `pipelines.md`. Lists each pipeline impacted by the change with its name,
confidence level, and a brief rationale. Format: `- Pipeline: <name>`.

### Affected Domains and Concepts

Derived from `domains.md` and `concepts.md`. Lists:

- Domains: domain names and boundary notes
- Concepts: concept names and role changes

### Impact and Risks

Cross-references all four inputs. Highlights low-confidence markers, surface area of
change, and potential regressions.

### Suggested Next Changes

Derived from pipeline and concept confidence levels. Recommends which artifacts to update
first and whether to re-run semantic refine after change-analysis review feedback.

## Validation Rules

A valid change-analysis document must contain all five sections above. Missing sections
cause `validate_change_analysis()` to return errors.
