# FACT Contract Mapping

**Purpose**: Define the boundary between canonical facts and working summary

**Version**: 1.0
**Date**: 2026-03-16

---

## Overview

FACT layer outputs are split into two distinct contracts:

1. **Canonical Facts** (`fact_canonical_sample.yaml`) - Observable, evidence-backed facts only
2. **Working Summary** (`fact_working_summary_sample.yaml`) - Interpretation, analysis, and working context

This document defines what goes into each contract and why.

---

## Canonical Facts Contract

### Definition

**Canonical facts** are observable, evidence-backed claims about the repository structure. They contain:
- What exists (modules, files, functions, entrypoints)
- Where it exists (file paths, line numbers)
- How it's structured (imports, dependencies, configuration)
- Evidence supporting each claim (file:line references)

### What Goes Into Canonical

| Category | Examples | Why Canonical |
|----------|----------|---------------|
| **Module structure** | Module names, file paths, function names | Observable from code |
| **Entrypoints** | Skill definitions, command mappings | Observable from manifest/skills |
| **Data structures** | Dataclass fields, protocol methods | Observable from type definitions |
| **Configuration** | manifest.yaml, pyproject.toml values | Observable from config files |
| **Dependencies** | Import statements, package requirements | Observable from code/config |
| **Evidence refs** | file:line, command outputs | Observable from source |
| **Version metadata** | Artifact versions, checkpoint data | Observable from file system |

### What Does NOT Go Into Canonical

| Category | Why Not Canonical | Where It Goes |
|----------|-------------------|---------------|
| **Purpose interpretation** | "System purpose is X" | Working summary |
| **Role assignments** | "Module X's role is Y" | Working summary |
| **Domain proposals** | "Modules A,B form domain X" | Working summary |
| **Relationship analysis** | "Pipeline X uses concept Y" | Working summary |
| **Open questions** | "Unclear if X or Y" | Working summary |
| **Assumptions** | "Assuming X based on Y" | Working summary |
| **Confidence ratings** | "High/medium/low confidence" | Working summary (metadata) |

### Canonical Schema Rules

1. **Evidence required**: Every claim must have file:line or command evidence
2. **Observable only**: No interpretation, abstraction, or semantic judgment
3. **Stable structure**: Top-level keys and field names are frozen
4. **Version tracked**: All artifacts have version numbers
5. **Immutable baseline**: Accepted baseline cannot be auto-modified

---

## Working Summary Contract

### Definition

**Working summary** contains interpretation, analysis, and working context derived from canonical facts. It includes:
- Purpose interpretation (what the system means to do)
- Role assignments (what each module's responsibility is)
- Domain proposals (how modules group into domains)
- Relationship analysis (how pipelines use concepts)
- Open questions (what's unclear or uncertain)
- Assumptions (what we're inferring)

### What Goes Into Working Summary

| Category | Examples | Why Working Summary |
|----------|----------|---------------------|
| **Purpose interpretation** | "System purpose is semantic understanding" | Semantic abstraction |
| **Role assignments** | "artifact_writer's role is version control" | Semantic abstraction |
| **Domain proposals** | "Artifact Management domain: writer + inspector" | Semantic grouping |
| **Relationship analysis** | "Discovery pipeline uses Evidence concept" | Semantic relationship |
| **Open questions** | "Unclear if X should be Y or Z" | Working context |
| **Assumptions** | "Assuming baseline is immutable" | Working context |
| **Confidence ratings** | "High confidence in module structure" | Metadata |
| **Review summaries** | "System summary for architect" | Human communication |

### What Does NOT Go Into Working Summary

| Category | Why Not Working Summary | Where It Goes |
|----------|-------------------------|---------------|
| **Module names** | Observable fact | Canonical |
| **File paths** | Observable fact | Canonical |
| **Function signatures** | Observable fact | Canonical |
| **Evidence refs** | Observable fact | Canonical |
| **Version numbers** | Observable fact | Canonical |

### Working Summary Schema Rules

1. **Interpretation allowed**: Purpose, role, domain proposals are semantic work
2. **Confidence metadata**: All interpretations have confidence ratings
3. **Mutable**: Working summary can evolve as understanding improves
4. **Human-readable**: Optimized for architect review, not agent consumption
5. **Evidence-linked**: All interpretations reference canonical facts

---

## Mapping Rules

### Rule 1: Observable vs Interpreted

**Observable** → Canonical
**Interpreted** → Working Summary

Examples:
- ✅ Canonical: "Module artifact_writer has function write_versioned_artifact"
- ❌ Canonical: "artifact_writer's role is version control"
- ✅ Working Summary: "artifact_writer's interpreted role is version control"

### Rule 2: Structure vs Meaning

**Structure** → Canonical
**Meaning** → Working Summary

Examples:
- ✅ Canonical: "Pipeline: discover → review → refine → baseline"
- ❌ Canonical: "Discovery pipeline's purpose is fact extraction"
- ✅ Working Summary: "Discovery pipeline's interpreted purpose is fact extraction"

### Rule 3: Evidence vs Analysis

**Evidence** → Canonical
**Analysis** → Working Summary

Examples:
- ✅ Canonical: "Evidence: src/artifact_writer.py:45-67"
- ❌ Canonical: "High confidence in artifact_writer's responsibility"
- ✅ Working Summary: "Confidence: high (based on clear function names)"

### Rule 4: Existence vs Relationship

**Existence** → Canonical
**Relationship** → Working Summary

Examples:
- ✅ Canonical: "Module: discovery_executor, Module: refine_executor"
- ❌ Canonical: "discovery_executor and refine_executor form Pipeline Orchestration domain"
- ✅ Working Summary: "Proposed domain: Pipeline Orchestration (discovery_executor, refine_executor)"

### Rule 5: Configuration vs Interpretation

**Configuration** → Canonical
**Interpretation** → Working Summary

Examples:
- ✅ Canonical: "manifest.yaml: target=claude-code"
- ❌ Canonical: "System is a Claude Code plugin for semantic understanding"
- ✅ Working Summary: "Interpreted purpose: semantic understanding pipeline for Claude Code"

---

## Field-Level Mapping

### Canonical Fields

```yaml
# Canonical structure
modules:
  - name: string                    # Observable
    path: string                    # Observable
    functions: [string]             # Observable
    evidence: string                # Observable

entrypoints:
  - name: string                    # Observable
    type: string                    # Observable
    location: string                # Observable
    command: string                 # Observable
    evidence: string                # Observable

core_entities:
  - name: string                    # Observable
    type: string                    # Observable
    defined_in: string              # Observable
    fields: [string]                # Observable
    evidence: string                # Observable
```

### Working Summary Fields

```yaml
# Working summary structure
system_purpose:
  interpreted_purpose: string       # Interpretation
  supported_scenarios: [string]     # Interpretation
  non_goals: [string]               # Interpretation
  confidence: string                # Metadata

pipelines:
  - name: string                    # Reference to canonical
    interpreted_purpose: string     # Interpretation
    flow_interpretation: [...]      # Interpretation
    confidence: string              # Metadata

concepts:
  - name: string                    # Reference to canonical
    interpreted_role: string        # Interpretation
    used_by_pipelines: [string]     # Relationship analysis
    confidence: string              # Metadata

domain_proposals:
  - name: string                    # Semantic grouping
    rationale: string               # Interpretation
    proposed_modules: [string]      # Relationship analysis
    confidence: string              # Metadata
```

---

## Migration Path

### From Current `fact_expected_sample.yaml`

**Step 1**: Extract canonical facts
- Keep: modules, entrypoints, core_entities, configuration, dependencies
- Remove: purpose, role, used_by, domain_candidates, open_questions
- Result: `fact_canonical_sample.yaml`

**Step 2**: Extract working summary
- Keep: purpose, role, used_by, domain_candidates, open_questions
- Add: confidence ratings, assumptions, review summaries
- Result: `fact_working_summary_sample.yaml`

**Step 3**: Update references
- Canonical references working summary: No
- Working summary references canonical: Yes (via name fields)

---

## Consumption Patterns

### For Semantic Layer

**Primary input**: `fact_canonical_sample.yaml`
- Consume: modules, entrypoints, core_entities, configuration
- Ignore: working summary (semantic will generate its own interpretation)

**Secondary input**: `docs/fact/baseline/*.md`
- Consume: accepted baseline artifacts
- Filter: extract observable facts, ignore interpretation

**Ignore**: `fact_working_summary_sample.yaml`
- Semantic layer generates its own semantic model
- Working summary is for human review, not semantic consumption

### For Human Review

**Primary input**: `fact_working_summary_sample.yaml`
- Read: purpose interpretation, domain proposals, open questions
- Validate: assumptions, confidence ratings

**Secondary input**: `fact_canonical_sample.yaml`
- Reference: check evidence for interpretations
- Validate: ensure interpretations are grounded in facts

---

## Validation Rules

### Canonical Validation

1. **Evidence required**: Every claim must have evidence field
2. **No interpretation**: No fields like "purpose", "role", "used_by"
3. **Observable only**: All values must be extractable from code/config
4. **Stable schema**: Top-level keys match frozen contract

### Working Summary Validation

1. **Confidence required**: Every interpretation must have confidence rating
2. **Canonical reference**: All interpretations must reference canonical facts
3. **Interpretation allowed**: Fields like "interpreted_purpose", "rationale" are valid
4. **Mutable**: Working summary can evolve without breaking canonical

---

## Summary

| Aspect | Canonical | Working Summary |
|--------|-----------|-----------------|
| **Content** | Observable facts | Interpretation & analysis |
| **Evidence** | Required | References canonical |
| **Mutability** | Immutable (baseline) | Mutable |
| **Consumption** | Semantic layer | Human review |
| **Schema** | Frozen contract | Flexible |
| **Confidence** | Not included | Required for all interpretations |
| **Purpose** | Stable foundation | Working context |

**Key principle**: Canonical is the **source of truth** for observable facts. Working summary is **derived interpretation** for human understanding.

---

**Next steps**:
1. Freeze canonical schema contract (see `fact_canonical_contract.md`)
2. Create templates for both contracts (see `templates/fact/`)
3. Update current FACT documentation to reference split contracts
