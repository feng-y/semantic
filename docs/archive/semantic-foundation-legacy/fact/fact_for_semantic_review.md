# FACT as SEMANTIC Input Readiness Review

**Review Date**: 2026-03-16
**Reviewer**: Claude Opus 4.6
**Review Target**: Current FACT layer outputs as inputs for future SEMANTIC layer

## Reviewed Files

1. `docs/semantic-foundation/fact/fact_expected_sample.md` - FACT layer specification and explanation
2. `docs/semantic-foundation/fact/fact_expected_sample.yaml` - Current canonical FACT sample (21KB)
3. `docs/semantic-foundation/fact/fact_naming_mapping.md` - Naming clarity and layer boundaries

---

## Overall Judgment: PASS WITH GAPS

**Status**: `pass_with_gaps`

**Can Enter Semantic**: ✅ **YES**

**Should Split FACT YAML**: ✅ **YES** (medium priority)

Current FACT outputs are **sufficient** for the SEMANTIC layer to start. The `fact_expected_sample.yaml` contains all minimum required inputs. However, it mixes observable facts with interpretation, and splitting into `fact_canonical_sample.yaml` + `fact_working_summary_sample.yaml` would improve FACT purity and semantic input quality.

---

## Four-Dimension Assessment

### 1. Canonical Purity: PARTIAL

**Status**: `partial`

#### Strengths
- Strong evidence traceability: Every claim backed by file paths, line numbers, or commands
- Observable-first design: `repo_facts` focuses on modules, entrypoints, entities, config
- Clear versioning: All discovery artifacts versioned (vN.md), baseline immutable
- Schema-validated: 10 schema files define structural contracts

#### Issues
- **Interpretation mixed in canonical**: `repo_understanding` includes semantic-level fields:
  - `Purpose`: "System purpose and non-goals" (semantic interpretation)
  - `Role`: "Role in system" for concepts (semantic abstraction)
  - `Used By`: "Which pipelines use this concept" (semantic relationship)
- **Domain candidates in canonical**: Domain identification is semantic work, not observable fact
- **Open Questions in canonical**: `repo_understanding.schema.md` includes "Open Questions" section (should be working summary)

#### Evidence from `fact_expected_sample.yaml`
```yaml
repo_understanding:
  system_purpose:
    purpose: "Semantic understanding pipeline for Claude Code plugins"  # ← Interpretation
    evidence: "manifest.yaml:target=claude-code, skills/*.skill"
    confidence: "high"

  concepts:
    - name: "Artifact Versioning"
      description: "Immutable versioned outputs with .vN.md naming"
      role: "Version control for generated artifacts"  # ← Semantic role
      used_by: ["Discovery Pipeline", "Refinement Pipeline"]  # ← Semantic relationship
```

#### Recommendation
**Separate interpretation from observation**:
- Canonical should contain: module names, file paths, function signatures, imports, config values
- Working summary should contain: purpose interpretation, role assignments, domain boundaries

---

### 2. Structure Stability: PASS

**Status**: `pass`

#### Strengths
- **Top-level objects are clear**: `repo_facts`, `repo_understanding`, `domain_candidates`, `knowledge_confidence`, `review_summary`, `baseline_reference`
- **Field naming is stable**: Consistent use of `name`, `description`, `evidence`, `confidence`
- **Evidence/source/version traceable**: Every artifact has evidence refs, version numbers, source metadata
- **Agent-friendly YAML**: Hierarchical structure, clear field types, parseable format
- **Baseline metadata stable**: `checkpoint.json` tracks source versions, feedback hash, timestamp

#### Evidence from `fact_expected_sample.yaml`
```yaml
metadata:
  fact_layer_complete: true
  semantic_layer_ready: false
  demand_layer_ready: false

  agent_consumption_notes:
    - "All structured fields (pipeline_name, concept_name, domain_name) are agent-parseable"
    - "Evidence fields are for human audit, not agent consumption"
    - "Confidence ratings (high/medium/low) guide agent trust in claims"
    - "Baseline artifacts are immutable; working artifacts are mutable"
```

#### Conclusion
Structure is **stable enough** for long-term semantic consumption. Field contracts are clear, versioning is reliable, and agent consumption is well-documented.

---

### 3. Working Summary Separation: PARTIAL

**Status**: `partial`

#### Current State
- **No explicit separation**: `fact_expected_sample.yaml` combines canonical facts and working summary into single structure
- **review-summary is stub**: `docs/fact/review/review-summary.v1.md` contains only stub content
- **Unclear boundary**: No documentation of which fields go to canonical vs working summary

#### What Should Be Separated

**Canonical (strict facts)**:
- Module names, file paths, function signatures
- Entrypoint definitions, execution flows
- Configuration values, build system facts
- Evidence refs (file:line)
- Version metadata

**Working Summary (interpretation)**:
- System purpose interpretation
- Domain boundary proposals
- Concept role assignments
- Pipeline relationship analysis
- Open questions for architect
- Assumptions and uncertainties

#### Evidence from Current Artifacts
```yaml
# Currently in canonical (should be working summary):
repo_understanding:
  system_purpose:
    purpose: "Semantic understanding pipeline..."  # ← Interpretation

  concepts:
    - role: "Version control for generated artifacts"  # ← Semantic role
      used_by: ["Discovery Pipeline", "Refinement Pipeline"]  # ← Relationship

# Currently in review-summary (correct placement, but stub):
review_summary:
  system_summary: "(stub: pending real generation)"
  assumptions: "- (stub: pending)"
  questions_for_architect: "- (stub: pending)"
```

#### Recommendation
**Clarify canonical vs working boundary**:
1. Create `fact_canonical_sample.yaml` with only observable facts
2. Create `fact_working_summary_sample.yaml` with interpretation and questions
3. Document mapping: which fields go where

---

### 4. Semantic Minimum Input Completeness: PASS

**Status**: `pass`

#### Minimum Semantic Input Requirements

| Requirement | Present | Source |
|-------------|---------|--------|
| Observable repository structure | ✅ | `repo_facts.modules`, `repo_facts.entrypoints` |
| Plugin/skill entrypoints | ✅ | `repo_facts.entrypoints` (7 skills) |
| Generated artifact inventory | ✅ | `repo_facts.core_entities` (DiscoveryResult, RefineResult) |
| Explicit modules/configs/paths | ✅ | `repo_facts.modules` (14 modules), `repo_facts.configuration` |
| Accepted baseline checkpoint | ✅ | `baseline_reference.checkpoint_metadata` |
| Evidence refs | ✅ | All artifacts have `evidence` fields |
| Repo understanding | ✅ | `repo_understanding` (even if mixed with interpretation) |
| Review summary | ✅ | `review_summary` (stub, but structure defined) |

#### Evidence from `fact_expected_sample.yaml`
```yaml
repo_facts:
  modules:
    - name: "artifact_writer"
      path: "src/artifact_writer.py"
      responsibility: "Versioned artifact I/O with atomic writes"
      evidence: "src/artifact_writer.py:write_versioned_artifact()"

  entrypoints:
    - name: "semantic-discover"
      type: "skill"
      location: "skills/semantic-discover.skill"
      execution_flow: "skill → dispatcher → discovery_executor → prompts"

baseline_reference:
  checkpoint_metadata:
    source_versions:
      repo_understanding: 2
      knowledge_confidence: 1
      domain_candidates: 1
    baseline_files: ["purpose.md", "pipelines.md", "domains.md", "concepts.md"]
    feedback_hash: "a3f5c8e9"
```

#### Conclusion
All **minimum semantic inputs are present**. Semantic layer can start immediately with current FACT output.

---

## Strengths

1. **Strong evidence traceability**: Every claim backed by file paths, line numbers, or commands
2. **Clear versioning model**: All discovery artifacts versioned (vN.md), baseline immutable
3. **Well-defined schemas**: 10 schema files define structural contracts
4. **Observable-first design**: `repo_facts` focuses on modules, entrypoints, entities, config
5. **Confidence metadata**: `knowledge_confidence` provides trust ratings per claim
6. **Baseline checkpoint**: `checkpoint.json` tracks source versions and feedback hash
7. **Agent-consumable structure**: YAML format with clear field hierarchy
8. **Complete pipeline coverage**: discover → review → refine → baseline fully mapped

---

## Gaps

1. **Canonical contains interpretation**: `repo_understanding` includes semantic-level fields (Purpose, Role, Used By)
2. **Domain candidates are mixed**: Domain identification is semantic work, not observable fact
3. **Working summary not fully separated**: `review-summary.v1.md` is stub, unclear what goes into working vs canonical
4. **Confidence placement unclear**: `knowledge_confidence` is separate artifact, but confidence ratings also appear inline in `repo_understanding`
5. **Open Questions in canonical**: `repo_understanding.schema.md` includes "Open Questions" section (should be working summary)
6. **No explicit canonical/working split**: `fact_expected_sample.yaml` combines everything, no separate `working_summary.yaml`

---

## Blocking Issues

**None**.

Current FACT output is sufficient for semantic layer to start. Identified gaps are about FACT purity and separation, not semantic input completeness.

---

## Recommended Actions

### 1. Separate interpretation from canonical
**Action**: `separate`
**Target**: `repo_understanding`
**Reason**: Split 'Purpose/Role/Used By' interpretation into working summary, keep only observable structure in canonical

**Before** (canonical):
```yaml
concepts:
  - name: "Artifact Versioning"
    role: "Version control for generated artifacts"  # ← Semantic
    used_by: ["Discovery Pipeline", "Refinement Pipeline"]  # ← Semantic
```

**After** (canonical):
```yaml
concepts:
  - name: "Artifact Versioning"
    defined_in: "src/artifact_writer.py"
    functions: ["write_versioned_artifact", "get_latest_working_version_path"]
    evidence: "src/artifact_writer.py:45-67"
```

**After** (working summary):
```yaml
concept_interpretation:
  - name: "Artifact Versioning"
    role: "Version control for generated artifacts"
    used_by: ["Discovery Pipeline", "Refinement Pipeline"]
    confidence: "high"
```

---

### 2. Move domain identification to working summary
**Action**: `separate`
**Target**: `domain_candidates`
**Reason**: Domain identification is semantic work, canonical should only contain module/entrypoint boundaries

**Before** (canonical):
```yaml
domain_candidates:
  - name: "Artifact Management"
    description: "Versioned artifact I/O and state management"
    related_pipelines: ["Discovery", "Refinement"]
```

**After** (canonical):
```yaml
module_boundaries:
  - modules: ["artifact_writer", "state_inspector"]
    shared_dependencies: ["pathlib", "json"]
    evidence: "import analysis"
```

**After** (working summary):
```yaml
domain_proposals:
  - name: "Artifact Management"
    rationale: "Modules share artifact I/O responsibility"
    modules: ["artifact_writer", "state_inspector"]
    confidence: "medium"
```

---

### 3. Clarify confidence placement
**Action**: `clarify`
**Target**: `confidence_placement`
**Reason**: Decide whether confidence is inline metadata or separate artifact (currently both)

**Options**:
- **Option A**: Confidence inline only (remove `knowledge_confidence` artifact)
- **Option B**: Confidence in separate artifact only (remove inline confidence)
- **Option C**: Both, but document which is authoritative

**Recommendation**: Option B (separate artifact), because:
- Keeps canonical clean (facts only)
- Allows confidence updates without touching canonical
- Matches "confidence is metadata, not claim content" principle

---

### 4. Move Open Questions to working summary
**Action**: `separate`
**Target**: `open_questions`
**Reason**: "Open Questions" should be in `review_summary` (working summary), not `repo_understanding` (canonical)

**Before** (`repo_understanding.schema.md`):
```
Open Questions
Required Fields:
- Description
- Why Unresolved
```

**After** (`review_summary.schema.md`):
```
Open Questions
Required Fields:
- Description
- Why Unresolved
- Related Artifacts
```

---

### 5. Freeze canonical schema contract
**Action**: `freeze_contract`
**Target**: `canonical_schema`
**Reason**: Define strict canonical schema with only observable facts (modules, entrypoints, config, evidence)

**Deliverable**: Create `docs/fact/schemas/canonical.schema.yaml` with:
```yaml
canonical_fact_schema:
  allowed_top_level_keys:
    - repo_identity
    - modules
    - entrypoints
    - configuration
    - evidence_index
    - version_metadata

  prohibited_fields:
    - purpose  # ← Interpretation
    - role  # ← Semantic abstraction
    - used_by  # ← Semantic relationship
    - domain_candidates  # ← Semantic work
    - open_questions  # ← Working summary
```

---

### 6. Document canonical vs working mapping
**Action**: `add_mapping`
**Target**: `canonical_to_working`
**Reason**: Document which fields go to canonical vs working summary

**Deliverable**: Create `docs/semantic-foundation/fact/canonical_working_mapping.md`:
```markdown
| Field | Canonical | Working Summary | Reason |
|-------|-----------|-----------------|--------|
| module.name | ✅ | ❌ | Observable |
| module.responsibility | ❌ | ✅ | Interpretation |
| concept.name | ✅ | ❌ | Observable |
| concept.role | ❌ | ✅ | Semantic abstraction |
| domain_candidates | ❌ | ✅ | Semantic work |
| open_questions | ❌ | ✅ | Working summary |
```

---

## Final Decision

### Can Semantic Start Now?

✅ **YES**

### Why?

1. **Minimum input present**: All required semantic inputs are available in current FACT output
2. **Structure is stable**: Field contracts are clear, versioning is reliable
3. **Evidence is traceable**: Every claim has file/line refs
4. **Baseline exists**: Accepted baseline artifacts provide stable foundation
5. **Gaps are non-blocking**: Interpretation mixed in canonical can be filtered by semantic layer

### What Semantic Should Consume

**Primary input**: `docs/fact/baseline/*.md`
- `purpose.md`: System purpose (filter interpretation, extract observable goals)
- `pipelines.md`: Execution flows (extract entrypoints, inputs, outputs)
- `domains.md`: Domain boundaries (extract module groupings)
- `concepts.md`: Core concepts (extract entity definitions)

**Secondary input**: `docs/fact/baseline/checkpoint.json`
- Source version traceability
- Feedback hash for change detection

**Ignore**: `docs/fact/review/review-summary.vN.md` (working summary, not needed for semantic)

---

## Residual Risks

### 1. Interpretation Leakage
**Risk**: Semantic layer might consume interpretation as fact
**Mitigation**: Semantic layer must filter fields like `purpose`, `role`, `used_by`
**Severity**: Low (semantic can handle this)

### 2. Working Summary Undefined
**Risk**: Unclear what goes into working summary vs canonical
**Mitigation**: Document canonical/working boundary (recommended action #6)
**Severity**: Low (semantic doesn't need working summary)

### 3. Confidence Placement Ambiguity
**Risk**: Confidence appears both inline and in separate artifact
**Mitigation**: Clarify authoritative source (recommended action #3)
**Severity**: Low (semantic can use either source)

### 4. Schema Evolution
**Risk**: FACT schema might change, breaking semantic consumption
**Mitigation**: Freeze canonical schema contract (recommended action #5)
**Severity**: Medium (requires schema versioning)

---

## Summary

**Current FACT output is semantic-ready**. Identified gaps improve FACT purity but do not block semantic layer development. Semantic layer can start immediately by consuming `docs/fact/baseline/*.md` and filtering out interpretation as needed.

**Recommended next steps**:
1. Start semantic layer development (not blocked)
2. Implement recommended actions in parallel to tighten FACT purity
3. Document canonical/working boundary for future FACT refinement
4. Freeze canonical schema contract to prevent breaking changes

**Final answer**:
- ✅ Is current fact canonical pure enough? **Partial, but sufficient**
- ✅ Is working summary sufficiently separated? **Partial, but not blocking**
- ✅ Does current fact satisfy semantic minimum input? **Yes**
- ✅ Can semantic start now? **Yes**

---

## Final Decisions

### Decision 1: Can Enter Semantic?

**YES** ✅

Current FACT outputs contain all minimum required inputs for semantic layer to start:
- Observable repository structure (modules, entrypoints, entities, config)
- Execution flows with evidence
- Baseline checkpoint metadata
- Accepted baseline artifacts

Gaps are about FACT purity, not semantic input completeness.

---

### Decision 2: Should Split FACT YAML?

**YES** ✅ (Medium Priority)

**Rationale**: Current `fact_expected_sample.yaml` mixes observable facts with interpretation.

**What should be split**:

**Canonical** (`fact_canonical_sample.yaml`):
- Module names, file paths, function signatures
- Entrypoint definitions, execution flows
- Configuration values, build system facts
- Evidence refs (file:line)
- Version metadata, checkpoint data

**Working Summary** (`fact_working_summary_sample.yaml`):
- System purpose interpretation
- Domain boundary proposals
- Concept role assignments
- Pipeline relationship analysis
- Open questions for architect
- Assumptions and uncertainties

**Split benefit**: Clearer separation improves semantic input quality and FACT purity

**Split urgency**: Medium - not blocking semantic start, but improves long-term maintainability

**Proposed future files**:
1. `fact_canonical_sample.yaml` - Strict observable facts only
2. `fact_working_summary_sample.yaml` - Interpretation and working context

---

## Review Conclusion

**Overall Status**: PASS WITH GAPS

**Can semantic start now?** YES

**Should FACT YAML be split?** YES (medium priority)

**Next actions**:
1. ✅ Start semantic layer development (not blocked)
2. 🔄 Split `fact_expected_sample.yaml` into canonical + working summary (improves quality)
3. 🔄 Implement 6 recommended actions to tighten FACT purity
4. 🔄 Freeze canonical schema contract to prevent breaking changes

---

**Review completed**: 2026-03-16
**Reviewer**: Claude Opus 4.6
