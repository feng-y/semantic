# FACT Layer Foundation - File Index

This directory contains the **FACT layer expected sample** for semantic-harness repo.

## Purpose

Define what the FACT layer **should look like** for this Claude Code plugin repo, providing:
1. Clear separation between observable facts and semantic interpretation
2. Canonical output format for downstream semantic layer consumption
3. Naming clarity to prevent confusion between fact/semantic/demand layers

## Files

### 1. fact_expected_sample.md
**Comprehensive FACT layer specification**

Contains:
- FACT layer definition (what it is, what it's not)
- Input/output specification
- Mapping to current discover/review/refine/baseline pipeline
- Field-level specification for agent consumption
- Relationship to future semantic/demand layers

**Read this first** to understand the FACT layer conceptually.

### 2. fact_expected_sample.yaml
**Real FACT layer output sample**

A **concrete, filled sample** (not empty template) showing:
- `repo_facts`: Observable structure (modules, entrypoints, entities, config)
- `repo_understanding`: Purpose, pipelines, concepts with evidence
- `domain_candidates`: Candidate domain boundaries
- `knowledge_confidence`: Confidence ratings per fact
- `review_summary`: Consolidated facts for architect
- `baseline_reference`: Accepted baseline metadata

**Use this** as the canonical shape for agent-consumable FACT output.

### 3. fact_naming_mapping.md
**Naming clarity and migration path**

Explains:
- Why current pipeline = FACT only (not semantic, not demand)
- How old names map to FACT interpretation
- Why semantic/demand layers don't exist yet
- What semantic/demand would do (future)
- Migration path from FACT → Semantic → Demand

**Read this** to understand why we're not mixing layers.

## Key Insights

### Current State
- ✅ FACT layer is **implemented** (discover/review/refine/baseline)
- ❌ Semantic layer is **not implemented** (no abstraction, no interpretation)
- ❌ Demand layer is **not implemented** (no impact analysis, no change planning)

### Why This Matters
Calling the current pipeline "semantic" is misleading. It's a **fact extraction and validation system**.

### What's Next
1. **Stabilize FACT**: Ensure fact extraction is reliable and complete
2. **Add Semantic**: Abstract facts into semantic models (domains, contracts, patterns)
3. **Add Demand**: Analyze change requests against semantic model

## Usage

### For Agent Consumption
Use `fact_expected_sample.yaml` as the canonical shape:
```yaml
repo_facts:
  repository:
    primary_language: "Python"
    repository_type: "plugin"
  modules:
    - name: "artifact_writer"
      responsibility: "Versioned artifact I/O"
```

### For Human Understanding
Read `fact_expected_sample.md` for full specification.

### For Naming Clarity
Read `fact_naming_mapping.md` to understand why current pipeline = FACT only.

## Validation

All samples are based on **real semantic-harness repo structure**:
- `manifest.yaml`: Claude Code plugin manifest
- `skills/*.skill`: 7 public skills
- `prompts/**/*.prompt`: Discovery and refine prompts
- `src/*.py`: 14 Python runtime modules
- `docs/semantic/`: Generated fact state directory

## Next Steps

1. **Verify FACT completeness**: Does current pipeline extract all necessary facts?
2. **Define Semantic layer**: What abstractions are needed on top of FACT?
3. **Design Demand layer**: How to analyze change requests against semantic model?

---

Generated: 2026-03-16
Repo: semantic-harness (Claude Code plugin)
