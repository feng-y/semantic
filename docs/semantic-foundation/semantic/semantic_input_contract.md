# Semantic Input Contract

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Contract Definition
**Role**: This document is canonical for semantic input consumption rules. All semantic stages must follow these input rules.

---

## Overview

This document defines what SEMANTIC layer consumes from FACT layer, how to resolve conflicts, and what assumptions are forbidden.

---

## Primary Hard Input

### Source

**Canonical Facts**: `fact_canonical_sample.yaml`

**Baseline Files**: `docs/fact/baseline/*.md`
- `purpose.md`
- `pipelines.md`
- `domains.md`
- `concepts.md`
- `checkpoint.json`

### Content

**From Canonical Facts**:
- `repo_identity`: Repository metadata (name, type, language, build_system)
- `modules`: Observable module structure (name, path, functions, evidence)
- `entrypoints`: Observable entrypoints (name, type, location, command, evidence)
- `core_entities`: Observable data structures (name, type, defined_in, fields, evidence)
- `configuration`: Observable config (name, type, location, evidence)
- `dependencies`: Observable imports and packages
- `execution_flows`: Observable call chains
- `baseline_reference`: Checkpoint metadata

**From Baseline Files**:
- `purpose.md`: System purpose and non-goals
- `pipelines.md`: Key execution flows
- `domains.md`: Domain boundaries (FACT-level)
- `concepts.md`: Core domain concepts
- `checkpoint.json`: Source version traceability

### Consumption Rule

**TRUST as ground truth**.

- All canonical facts are evidence-backed
- All baseline files are architect-accepted
- Evidence refs (file:line) can be validated
- Version metadata is traceable

**SEMANTIC must**:
- Consume canonical facts as primary input
- Trust evidence refs
- Use baseline as stable reference
- Not re-extract facts

---

## Auxiliary Soft Input

### Source

**Working Summary**: `fact_working_summary_sample.yaml`

**Discovery Artifacts**: `docs/fact/discovery/*.vN.md`
- `repo-understanding.vN.md`
- `domain-candidates.vN.md`
- `knowledge-confidence.vN.md`

**Review Artifacts**: `docs/fact/review/*.vN.md`
- `review-summary.vN.md`

### Content

**From Working Summary**:
- `system_purpose`: Interpreted purpose
- `pipelines`: Interpreted pipeline purposes
- `concepts`: Interpreted concept roles
- `domain_proposals`: Proposed domain boundaries
- `module_responsibilities`: Interpreted responsibilities
- `relationships`: Inferred relationships
- `open_questions`: Unresolved questions
- `assumptions`: Working assumptions
- `confidence_assessment`: Confidence ratings

**From Discovery/Review Artifacts**:
- Additional context
- Architect feedback
- Review summaries
- Confidence ratings

### Consumption Rule

**USE as guidance, NOT as hard truth**.

- Working summary is interpretation, not fact
- Domain proposals are hints, not decisions
- Confidence ratings are metadata, not claims
- Open questions indicate uncertainty

**SEMANTIC must**:
- Use working summary for bootstrap context
- Treat domain proposals as suggestions
- Validate interpretations against canonical facts
- Not blindly trust working summary

---

## Conflict Resolution

### Rule 1: Canonical Wins

**When conflict exists between canonical facts and working summary**:
- **Prefer canonical facts**
- Working summary is interpretation, canonical is ground truth
- Example: If canonical says module X has functions [A, B], but working summary says [A, B, C], trust canonical

### Rule 2: Evidence Wins

**When conflict exists between claims**:
- **Prefer claim with evidence refs**
- Evidence-backed claims are verifiable
- Example: If one claim has "file:line" evidence and another doesn't, trust the one with evidence

### Rule 3: Baseline Wins

**When conflict exists between baseline and discovery artifacts**:
- **Prefer baseline**
- Baseline is architect-accepted, discovery is working state
- Example: If baseline says domain X, but discovery says domain Y, trust baseline

### Rule 4: Explicit Wins

**When conflict exists between explicit and inferred**:
- **Prefer explicit**
- Explicit claims are observable, inferred claims are interpretation
- Example: If canonical explicitly lists modules, don't infer additional modules from working summary

---

## Forbidden Assumptions

### Assumption 1: Working Summary is Hard Truth

**FORBIDDEN**: Treating working summary as canonical fact.

**Why**: Working summary is interpretation, not observation. It may contain:
- Incorrect domain proposals
- Speculative relationships
- Unvalidated assumptions
- Open questions

**Correct**: Use working summary as guidance, validate against canonical.

### Assumption 2: Domain Proposals are Final

**FORBIDDEN**: Treating `domain_proposals` as final domain boundaries.

**Why**: Domain proposals are suggestions, not decisions. They may:
- Overlap incorrectly
- Miss important boundaries
- Group modules incorrectly

**Correct**: Use domain proposals as hints, synthesize final domains from canonical facts.

### Assumption 3: Confidence Ratings are Claims

**FORBIDDEN**: Treating confidence ratings as factual claims.

**Why**: Confidence is metadata about claims, not claims themselves. High confidence doesn't make interpretation true.

**Correct**: Use confidence to prioritize validation, not to bypass it.

### Assumption 4: Open Questions are Blockers

**FORBIDDEN**: Treating open questions as blocking issues.

**Why**: Open questions indicate uncertainty, not impossibility. They may:
- Be resolved by canonical facts
- Be irrelevant to semantic synthesis
- Be deferred to later stages

**Correct**: Note open questions, proceed with available facts.

### Assumption 5: Interpretations are Observable

**FORBIDDEN**: Treating interpreted fields (purpose, role, used_by) as observable facts.

**Why**: These are semantic abstractions, not observations. They may:
- Be incorrect
- Be incomplete
- Conflict with canonical facts

**Correct**: Validate interpretations against canonical facts, re-synthesize if needed.

---

## Consumption Rule Summary

### For Canonical Facts

1. **Trust**: Canonical facts are ground truth
2. **Validate**: Use evidence refs to verify claims
3. **Prefer**: When conflict, prefer canonical over working summary
4. **Stable**: Canonical schema is frozen, safe to depend on

### For Working Summary

1. **Guide**: Use as bootstrap context and hints
2. **Validate**: Cross-check against canonical facts
3. **Filter**: Ignore interpretations that conflict with canonical
4. **Soft**: Working summary is mutable, don't hard-depend on it

### For Baseline Files

1. **Reference**: Use as stable semantic reference
2. **Accepted**: Baseline is architect-accepted
3. **Immutable**: Baseline doesn't change without explicit update
4. **Primary**: Prefer baseline over discovery artifacts

### For Discovery/Review Artifacts

1. **Context**: Use for additional context
2. **Working**: These are working state, not final
3. **Versioned**: Check version numbers for freshness
4. **Auxiliary**: Use only when baseline insufficient

---

## Input Validation Checklist

Before SEMANTIC starts, validate:

### Required Inputs Present

- [ ] `fact_canonical_sample.yaml` exists
- [ ] `docs/fact/baseline/purpose.md` exists
- [ ] `docs/fact/baseline/pipelines.md` exists
- [ ] `docs/fact/baseline/domains.md` exists
- [ ] `docs/fact/baseline/concepts.md` exists
- [ ] `docs/fact/baseline/checkpoint.json` exists

### Optional Inputs Present

- [ ] `fact_working_summary_sample.yaml` exists (recommended)
- [ ] `docs/fact/discovery/*.vN.md` exist (helpful)
- [ ] `docs/fact/review/*.vN.md` exist (helpful)

### Input Quality

- [ ] Canonical facts have evidence refs
- [ ] Baseline files are non-empty
- [ ] Checkpoint metadata is valid
- [ ] Working summary (if present) is well-formed

### Conflict Check

- [ ] No obvious conflicts between canonical and baseline
- [ ] Evidence refs are resolvable
- [ ] Version numbers are consistent

---

## Summary

**Primary Hard Input**: Canonical facts + baseline files
- Trust as ground truth
- Use evidence refs
- Prefer when conflict

**Auxiliary Soft Input**: Working summary + discovery/review artifacts
- Use as guidance
- Validate against canonical
- Don't blindly trust

**Conflict Resolution**: Canonical > Evidence > Baseline > Explicit
**Forbidden**: Treating working summary as hard truth, domain proposals as final, confidence as claims

**SEMANTIC must consume inputs correctly to produce valid semantic models.**
