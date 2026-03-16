# FACT Layer Assessment for semantic-harness

## Executive Summary

I've analyzed the semantic-harness repo and produced **FACT layer expected samples** that clarify what the current pipeline actually does versus what "semantic" implies.

### Key Finding

**The current pipeline is FACT-only, not semantic.**

- ✅ Extracts observable facts with evidence
- ✅ Validates facts through human review
- ✅ Synthesizes accepted baseline
- ❌ Does NOT abstract facts into semantic models
- ❌ Does NOT analyze change impact or demand

---

## Generated Files

### 1. `fact/fact_expected_sample.md` (344 lines)
**Comprehensive FACT layer specification**

Defines:
- What FACT is (evidence-driven facts) vs. what it's not (semantic modeling)
- FACT inputs (repo tree, source files, config)
- FACT outputs (discovery artifacts, review artifacts, baseline artifacts)
- Mapping: current pipeline phases → FACT layer roles
- Field-level specification for agent consumption
- Relationship to future semantic/demand layers

### 2. `fact/fact_expected_sample.yaml` (519 lines)
**Real FACT layer output sample**

A **concrete, filled sample** using semantic-harness repo's actual structure:
- `repo_facts`: 5 modules, 3 entrypoints, 3 core entities, 2 configs
- `repo_understanding`: System purpose, 2 pipelines, 8 concepts
- `domain_candidates`: 4 candidate domains
- `knowledge_confidence`: Confidence ratings (high/medium/low)
- `review_summary`: Consolidated facts
- `baseline_reference`: Checkpoint metadata

**This is agent-consumable YAML**, not human-readable Markdown.

### 3. `fact/fact_naming_mapping.md` (220 lines)
**Naming clarity and migration path**

Explains:
- Why current pipeline = FACT only
- Old names → FACT interpretation mapping
- Why semantic/demand layers don't exist yet
- What semantic/demand would do (future)
- Migration path: FACT → Semantic → Demand

### 4. `fact/README.md` (104 lines)
**Directory index and usage guide**

Quick reference for file purposes, key insights, usage patterns, and next steps.

---

## Current Repo FACT Layer Assessment

### ✅ What's Clear

1. **Plugin-facing layer is well-defined**
   - 7 public skills in `skills/*.skill`
   - `manifest.yaml` registers skills
   - Clear command routing through `dispatcher.py`

2. **Fact extraction pipeline is complete**
   - `discover`: sampling → facts → understanding → confidence
   - `review`: present facts for validation
   - `refine`: patch facts with corrections
   - `baseline`: synthesize accepted facts

3. **Versioning and validation are robust**
   - All artifacts versioned (`.vN.md`)
   - Schema validation in `docs/fact/schemas/`
   - Atomic writes prevent partial state
   - Acceptance gates before baseline synthesis

4. **Evidence traceability is consistent**
   - Every fact backed by file paths or commands
   - Evidence fields in all artifacts
   - Confidence ratings per claim

### ⚠️ What's Confusing

1. **"Semantic" naming is misleading**
   - Directory: `docs/fact/` → should be `docs/fact/`
   - Skills: `semantic-*` → should be `fact-*`
   - Current pipeline extracts facts, not semantic models

2. **No semantic abstraction layer**
   - Facts are not abstracted into domain models
   - No behavioral contracts or interaction patterns
   - No semantic documentation generation

3. **No demand analysis layer**
   - No change impact analysis
   - No risk assessment
   - No migration planning

### 🔍 What's Missing for Semantic Layer

To move from FACT → Semantic, you need:

1. **Semantic abstraction logic**
   - Abstract facts into domain models
   - Define behavioral contracts
   - Model interaction patterns

2. **Semantic output format**
   - Domain definitions (not just candidates)
   - Contract specifications
   - Pattern documentation

3. **Semantic validation**
   - Consistency checks across domains
   - Contract completeness validation
   - Pattern coverage assessment

### 🔍 What's Missing for Demand Layer

To move from Semantic → Demand, you need:

1. **Change request parser**
   - Parse natural language change requests
   - Extract affected domains/concepts
   - Identify change type (feature/fix/refactor)

2. **Impact analyzer**
   - Analyze change against semantic model
   - Identify affected domains and contracts
   - Assess breaking changes

3. **Risk assessor**
   - Evaluate change complexity
   - Identify migration requirements
   - Generate change plan

---

## Recommendations

### Immediate (Keep FACT Stable)

1. **Don't rename anything yet**
   - Keep `semantic-*` skill names for backward compatibility
   - Keep `docs/fact/` directory structure
   - Focus on conceptual clarity, not refactoring

2. **Use FACT samples as canonical shape**
   - `fact_expected_sample.yaml` defines agent-consumable format
   - Validate current outputs against this shape
   - Ensure all required fields are present

3. **Document FACT layer boundaries**
   - Make it clear what's observable vs. interpreted
   - Separate evidence (FACT) from meaning (Semantic)
   - Don't mix fact extraction with semantic modeling

### Next Phase (Add Semantic Layer)

1. **Design semantic abstraction**
   - Define what "semantic model" means for this repo
   - Specify semantic output format
   - Design semantic validation logic

2. **Implement semantic synthesis**
   - New pipeline: `semantic-synthesize`
   - Input: FACT baseline
   - Output: Semantic model

3. **Keep FACT and Semantic separate**
   - FACT: `docs/fact/` (current, keep for now)
   - Semantic: `docs/fact-model/` (new)
   - Clear boundary between layers

### Future Phase (Add Demand Layer)

1. **Design demand analysis**
   - Define change request format
   - Specify impact analysis logic
   - Design risk assessment criteria

2. **Implement demand pipeline**
   - New pipeline: `demand-analyze`
   - Input: Semantic model + Change request
   - Output: Demand analysis (impact, risks, plan)

3. **Keep all three layers separate**
   - FACT: Observable facts
   - Semantic: Interpreted meaning
   - Demand: Change analysis

---

## Judgment: Is Current FACT Layer Clear?

### ✅ Yes, FACT extraction is clear

The current pipeline has:
- Well-defined phases (discover/review/refine/baseline)
- Clear artifact schemas
- Robust versioning and validation
- Consistent evidence traceability

### ❌ No, FACT boundaries are unclear

The confusion comes from:
- Calling it "semantic" when it's actually "fact"
- No explicit separation between fact/semantic/demand
- Mixing observable facts with interpreted meaning in documentation

### Recommendation

**The FACT layer implementation is solid, but the naming and conceptual boundaries need clarification.**

Use the generated samples to:
1. Understand what FACT actually is
2. Separate FACT from future Semantic/Demand layers
3. Design Semantic layer without mixing it into FACT

---

## What's Still Missing to Enter Semantic Layer

### 1. Semantic Abstraction Design

**Question**: What does "semantic model" mean for this repo?

**Answer needed**:
- Domain model structure
- Contract specification format
- Pattern documentation format

### 2. Semantic Synthesis Logic

**Question**: How do we abstract facts into semantic models?

**Answer needed**:
- Abstraction rules (fact → semantic)
- Domain boundary inference
- Contract extraction logic

### 3. Semantic Output Format

**Question**: What does semantic layer output look like?

**Answer needed**:
- File structure (`docs/fact-model/`)
- YAML/JSON schema for semantic artifacts
- Agent-consumable format

### 4. Semantic Validation

**Question**: How do we validate semantic models?

**Answer needed**:
- Consistency checks
- Completeness criteria
- Quality metrics

---

## Next Steps

1. **Review generated FACT samples**
   - Read `fact_expected_sample.md` for full specification
   - Validate `fact_expected_sample.yaml` against current outputs
   - Use `fact_naming_mapping.md` for conceptual clarity

2. **Design Semantic layer**
   - Define semantic abstraction rules
   - Specify semantic output format
   - Design semantic validation logic

3. **Implement Semantic synthesis**
   - New skill: `semantic-synthesize`
   - Input: FACT baseline
   - Output: Semantic model

4. **Keep layers separate**
   - FACT: Observable facts with evidence
   - Semantic: Interpreted meaning and models
   - Demand: Change analysis and planning

---

Generated: 2026-03-16
Repo: semantic-harness (Claude Code plugin)
Total lines: 1187 (across 4 files)
