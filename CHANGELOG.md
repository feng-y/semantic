# Changelog

## v1.0.0

Stable release. 108 tests passing across all safety boundaries.

### Features
- Full discovery pipeline: sampling, fact extraction, evidence augmentation, domain analysis, repo understanding, knowledge confidence, review summary
- Refinement pipeline: artifact patching with architect feedback, change log generation, validation
- Baseline synthesis: 4-gate acceptance evaluator, atomic baseline generation, checkpoint metadata
- Versioned artifact management: rolling version window (keep 3), accepted version protection, semantic snapshots

### Safety
- Staged multi-artifact writes (atomic commit or nothing)
- Schema-aligned structural validation for all semantic artifacts
- Baseline boundary: discovery/refine never read baseline
- Deterministic acceptance gates (no fuzzy matching)
- Defense-in-depth version resolution (skips structurally invalid artifacts)
- Duplicate baseline section rejection
- Version skew detection blocks pipeline before writes

### Hardening
- Duplicate baseline heading detection in parser
- Schema doc alignment (acceptance field corrected)
- Validated version resolution in context builder

### Architecture
- Runtime purity: no stub/fake code in src/, no LLM SDK imports
- Host executor protocol: all prompt execution delegated to host environment
- Bounded context: refine/baseline paths read only versioned artifacts
- Artifact-based state: all semantic state lives in docs/fact/
