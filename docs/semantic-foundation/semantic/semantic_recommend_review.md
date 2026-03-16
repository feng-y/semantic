# semantic-recommend Implementation Review

**Review Date**: 2026-03-17
**Reviewer**: Claude Opus 4.6
**Review Type**: Implementation Review
**Review Target**: semantic-recommend capability

---

## Executive Summary

**Overall Status**: ✅ **PASS**

**semantic-recommend Ready**: ✅ **YES**

The semantic-recommend implementation is a real, contract-aligned, scoring-correct, traceability-preserving, test-backed, properly bounded third semantic capability. It is ready to be used as the third semantic execution unit.

---

## Reviewed Files

**Skill Definition:**
- `skills/semantic-recommend/SKILL.md` (260 lines)

**Implementation:**
- `src/semantic/score_recommend.py` (429 lines)
- `src/semantic/models.py` (updated with recommendation models)

**Templates:**
- `templates/semantic/recommendations.template.yaml` (updated)

**Prompts:**
- `prompts/semantic/semantic_recommend.prompt.md` (created)

**Tests:**
- `tests/semantic/test_score_recommend.py` (426 lines, 24 tests)

**Generated Outputs:**
- `docs/semantic-foundation/semantic/recommendations.yaml` (verified)
- `docs/semantic-foundation/semantic/recommendations.md` (verified)

**Contract References:**
- `docs/semantic-foundation/semantic/02_step3_scoring_design.md`
- `docs/semantic-foundation/semantic/semantic_stage_contracts.md`

**Dependency Verification:**
- `docs/semantic-foundation/semantic/candidates.yaml` (input)
- `skills/semantic-candidates/SKILL.md` (upstream dependency)

---

## Assessment Results: All PASS

1. ✅ **Standard Skill Correctness**: PASS
2. ✅ **Input Contract Alignment**: PASS
3. ✅ **Real Implementation**: PASS (not scaffold)
4. ✅ **Recommendation Quality**: PASS
5. ✅ **Scoring Correctness**: PASS
6. ✅ **Model Quality**: PASS
7. ✅ **Output Correctness**: PASS
8. ✅ **Traceability**: PASS
9. ✅ **Template Alignment**: PASS
10. ✅ **Test Quality**: PASS (24/24 tests passing)
11. ✅ **Capability Boundary**: PASS

---

## Detailed Assessments

### 1. Standard Skill Correctness: ✅ PASS

**Findings:**
- ✅ SKILL.md follows standard omc format with YAML frontmatter
- ✅ Clear decision tree showing execution flow
- ✅ 6 execution steps detailed (validate inputs, generate 4 recommendation types, write outputs)
- ✅ Clearly states when to use (after semantic-candidates, before semantic-review)
- ✅ Clearly states required inputs (candidates.yaml required)
- ✅ Clearly states outputs (recommendations.yaml canonical, recommendations.md view)
- ✅ Skill remains thin - calls Python implementation via CLI
- ✅ Explicitly bounded to recommend only (not review/finalize)
- ✅ Usage examples provided
- ✅ Success criteria checklist included

**Skill invocation:**
```bash
python -m semantic.score_recommend \
  --candidates docs/semantic-foundation/semantic/candidates.yaml \
  --output docs/semantic-foundation/semantic/recommendations.yaml \
  --render-md docs/semantic-foundation/semantic/recommendations.md
```

**Issues:** None

---

### 2. Input Contract Alignment: ✅ PASS

**Findings:**
- ✅ Primary input: candidates.yaml (REQUIRED) - correctly implemented
- ✅ candidates.yaml treated as direct primary input
- ✅ Recommendation generation derived from candidates (not bypassing)
- ✅ No dependence on later-stage artifacts (review/finalize)
- ✅ `load_candidates()` reads candidates.yaml directly
- ✅ All recommendation generation functions take candidate groups as input
- ✅ Auxiliary inputs (signals.yaml, FACT) mentioned as optional context only

**Code verification:**
```python
def load_candidates(candidates_path: Path) -> Optional[Dict[str, Any]]:
    """Load candidates.yaml (primary input)"""
    if not candidates_path.exists():
        return None
    with open(candidates_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
```

**Issues:** None

---

### 3. Real Implementation: ✅ PASS

**Findings:**
- ✅ score_recommend.py is 429 lines of real logic, NOT scaffold
- ✅ `load_candidates()` - real YAML loading
- ✅ `evaluate_semantic_validity()` - real deterministic validity evaluation
- ✅ `compute_scores()` - real deterministic scoring logic
- ✅ `determine_recommendation()` - real status/action decision logic
- ✅ `generate_reasons()` - real reason generation
- ✅ `check_evidence_needs()` - real evidence gap detection
- ✅ `generate_recommendation_item()` - real complete recommendation generation
- ✅ `generate_domain_recommendations()` - real domain-specific logic
- ✅ `generate_concept_recommendations()` - real concept-specific logic
- ✅ `generate_rule_recommendations()` - real rule-specific logic
- ✅ `generate_demand_model_recommendations()` - real demand model-specific logic
- ✅ `generate_stable_id()` - hash-based stable ID generation
- ✅ `render_recommendations_markdown()` - real markdown generation
- ✅ `main()` - real CLI with argparse
- ✅ Executable and functional (verified by running)

**Verification:**
```bash
$ python -m semantic.score_recommend --candidates docs/semantic-foundation/semantic/candidates.yaml --output docs/semantic-foundation/semantic/recommendations.yaml --render-md docs/semantic-foundation/semantic/recommendations.md
✓ Generated 6 recommendations
  - Domains: 2
  - Concepts: 2
  - Rules: 1
  - Demand models: 1
✓ Written to: docs/semantic-foundation/semantic/recommendations.yaml
✓ Rendered view: docs/semantic-foundation/semantic/recommendations.md
```

**Issues:** None

---

### 4. Recommendation Quality: ✅ PASS

**Findings:**
- ✅ Recommendations generated from candidate groups (not one-to-one copying)
- ✅ Stable IDs generated (hash-based, deterministic)
- ✅ Meaningful names preserved from candidates
- ✅ semantic_validity evaluated with deterministic rules
- ✅ validity_reason provided for each decision
- ✅ business_score and value_score computed with clear formulas
- ✅ priority computed correctly
- ✅ recommendation.status and recommendation.action determined by rules
- ✅ recommended_reasons and not_recommended_reasons generated
- ✅ needs_evidence_check / evidence_gap handled coherently
- ✅ merge_target field present (null when not merging)
- ✅ Functional test: successfully generates 6 recommendations from 6 candidates

**Validity evaluation logic:**
```python
# Deterministic rules:
# - PASS if confidence is high
# - PASS if confidence is medium and has evidence
# - FAIL if confidence is low
# - FAIL if missing required fields
```

**Scoring logic:**
```python
# Base scores by confidence
confidence_scores = {
    'high': 8.0,
    'medium': 6.0,
    'low': 3.0
}

# Business score: base + evidence bonus
business_score = min(base_score + evidence_bonus, 10.0)

# Value score: base + signal bonus
value_score = min(base_score + signal_bonus, 10.0)
```

**Recommendation decision logic:**
```python
# Rules:
# - If validity=fail: not_recommend + drop
# - If priority >= 7.0: recommend + keep
# - If priority >= 5.0: recommend + verify_first
# - If priority < 5.0: defer + backlog
```

**Issues:** None

---

### 5. Scoring Correctness: ✅ PASS

**Findings:**
- ✅ business_score exists and is computed
- ✅ value_score exists and is computed
- ✅ priority exists and is computed
- ✅ priority is RECOMPUTED by program (not trusted from input)
- ✅ priority = max(business_score, value_score) - CORRECT
- ✅ Scores are within valid range (1.0-10.0)
- ✅ Status values are valid (recommend, not_recommend, defer)
- ✅ Action values are valid (keep, merge, drop, backlog, verify_first)
- ✅ Model validation enforces priority rule via Pydantic validator

**Priority computation verification:**
```python
def determine_recommendation(...):
    priority = max(business_score, value_score)  # ✅ CORRECT
```

**Model validation:**
```python
@model_validator(mode="after")
def check_priority(self):
    expected = max(self.business_score, self.value_score)
    if round(self.priority, 6) != round(expected, 6):
        raise ValueError("priority must equal max(business_score, value_score)")
    return self
```

**Test verification:**
```python
def test_priority_computation():
    """Test that priority equals max(business_score, value_score)"""
    for candidate in candidates.get(candidate_type, []):
        rec = generate_recommendation_item(candidate, candidate_type.rstrip('s'))
        expected_priority = max(rec['business_score'], rec['value_score'])
        assert rec['priority'] == expected_priority
```

**Issues:** None

---

### 6. Model Quality: ✅ PASS

**Findings:**
- ✅ `DomainRecommendation` model defined (extends RecommendationItem)
- ✅ `ConceptRecommendation` model defined
- ✅ `RuleRecommendation` model defined
- ✅ `DemandModelRecommendation` model defined
- ✅ `RecommendationsOutput` structure defined
- ✅ `RecommendationItem` base model includes all required fields:
  - id, name, candidate_id
  - semantic_validity, validity_reason
  - business_score, value_score, priority
  - recommendation (status, action, target_layer, target_asset_type)
  - recommended_reasons, not_recommended_reasons
  - needs_evidence_check, evidence_gap, merge_target
  - source_candidate_ids, evidence_refs
- ✅ Type safety via Pydantic
- ✅ Validation logic for priority, merge_target, evidence_gap
- ✅ Models are usable (not placeholders)

**Model structure:**
```python
class RecommendationItem(BaseModel):
    id: str
    name: str
    candidate_id: str
    semantic_validity: SemanticValidity
    validity_reason: str
    business_score: float = Field(ge=1.0, le=10.0)
    value_score: float = Field(ge=1.0, le=10.0)
    priority: float = Field(ge=1.0, le=10.0)
    recommendation: RecommendationBody
    recommended_reasons: List[str]
    not_recommended_reasons: List[str]
    needs_evidence_check: bool = False
    evidence_gap: Optional[str] = None
    merge_target: Optional[str] = None
    source_candidate_ids: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
```

**Issues:** None

---

### 7. Output Correctness: ✅ PASS

**Findings:**
- ✅ Workspace: docs/semantic-foundation/semantic/ (correct)
- ✅ Canonical output: recommendations.yaml (correct)
- ✅ View output: recommendations.md (correct)
- ✅ All 4 recommendation groups present: domains, concepts, rules, demand_models
- ✅ YAML structure valid
- ✅ Required fields present in all recommendations:
  - id, name, candidate_id
  - semantic_validity, validity_reason
  - business_score, value_score, priority
  - recommendation (status, action, target_layer, target_asset_type)
  - recommended_reasons, not_recommended_reasons
  - needs_evidence_check, evidence_gap, merge_target
  - source_candidate_ids, evidence_refs
- ✅ Metadata present: generated_at, candidates_source, recommendation_count
- ✅ Output suitable for downstream semantic-review
- ✅ Functional test: successfully generates 6 recommendations

**Output verification:**
```yaml
domains:
- id: rec_domain_d921991b
  name: Repository Structure
  candidate_id: domain_2aa02a6c
  semantic_validity: pass
  validity_reason: High confidence with strong evidence
  business_score: 8.5
  value_score: 8.3
  priority: 8.5
  recommendation:
    status: recommend
    action: keep
    target_layer: final_asset
    target_asset_type: domain_map
  recommended_reasons: [...]
  not_recommended_reasons: []
  needs_evidence_check: false
  evidence_gap: null
  merge_target: null
  source_candidate_ids: [domain_2aa02a6c]
  evidence_refs: [14 modules observed]
```

**Issues:** None

---

### 8. Traceability: ✅ PASS

**Findings:**
- ✅ candidate_id preserved (links back to source candidate)
- ✅ source_candidate_ids preserved (list format for future merge support)
- ✅ evidence_refs preserved from candidates
- ✅ Recommendations can be traced back to candidates
- ✅ Provenance not discarded

**Traceability verification:**
```python
def generate_recommendation_item(candidate: Dict[str, Any], candidate_type: str) -> Dict[str, Any]:
    # ...
    return {
        'id': rec_id,
        'name': candidate['name'],
        'candidate_id': candidate['id'],  # ✅ Preserved
        # ...
        'source_candidate_ids': [candidate['id']],  # ✅ Preserved
        'evidence_refs': candidate.get('evidence_refs', []),  # ✅ Preserved
    }
```

**Test verification:**
```python
def test_traceability_preservation():
    """Test that candidate traceability is preserved"""
    rec = generate_recommendation_item(candidate, 'domain')
    assert rec['candidate_id'] == candidate['id']
    assert candidate['id'] in rec['source_candidate_ids']
    assert all(ev in rec['evidence_refs'] for ev in candidate['evidence_refs'])
```

**Issues:** None

---

### 9. Template Alignment: ✅ PASS

**Findings:**
- ✅ templates/semantic/recommendations.template.yaml exists and is aligned
- ✅ Template defines all 4 recommendation groups
- ✅ Template defines all required fields
- ✅ Template matches score_recommend.py output structure
- ✅ No drift between template and implementation
- ✅ Template documents field types and constraints

**Template structure:**
```yaml
domains:
  - id: string
    name: string
    candidate_id: string
    semantic_validity: string
    validity_reason: string
    business_score: float
    value_score: float
    priority: float
    recommendation:
      status: string
      action: string
      target_layer: string
      target_asset_type: string
    recommended_reasons: [string]
    not_recommended_reasons: [string]
    needs_evidence_check: boolean
    evidence_gap: string
    merge_target: string
    source_candidate_ids: [string]
    evidence_refs: [string]
```

**Issues:** None

---

### 10. Test Quality: ✅ PASS

**Findings:**
- ✅ 24 real tests implemented
- ✅ All 24 tests passing
- ✅ Tests cover all key behaviors:
  1. ✅ test_load_candidates - tests candidates loading
  2. ✅ test_generate_stable_id - tests ID stability
  3. ✅ test_evaluate_semantic_validity_high_confidence - tests validity for high confidence
  4. ✅ test_evaluate_semantic_validity_medium_with_evidence - tests validity for medium+evidence
  5. ✅ test_evaluate_semantic_validity_medium_without_evidence - tests validity for medium-evidence
  6. ✅ test_evaluate_semantic_validity_low_confidence - tests validity for low confidence
  7. ✅ test_evaluate_semantic_validity_missing_fields - tests validity for missing fields
  8. ✅ test_compute_scores_high_confidence - tests scoring for high confidence
  9. ✅ test_compute_scores_medium_confidence - tests scoring for medium confidence
  10. ✅ test_determine_recommendation_fail_validity - tests recommendation for failed validity
  11. ✅ test_determine_recommendation_high_priority - tests recommendation for high priority
  12. ✅ test_determine_recommendation_medium_priority - tests recommendation for medium priority
  13. ✅ test_determine_recommendation_low_priority - tests recommendation for low priority
  14. ✅ test_generate_reasons_pass - tests reason generation for pass
  15. ✅ test_generate_reasons_fail - tests reason generation for fail
  16. ✅ test_check_evidence_needs_medium_confidence - tests evidence check logic
  17. ✅ test_generate_recommendation_complete - tests complete recommendation generation
  18. ✅ test_recommendations_yaml_structure - tests YAML structure
  19. ✅ test_recommendations_markdown_generation - tests markdown generation
  20. ✅ test_deterministic_recommendation - tests determinism
  21. ✅ test_priority_computation - tests priority = max(business, value)
  22. ✅ test_traceability_preservation - tests traceability
  23. ✅ test_valid_status_values - tests status value constraints
  24. ✅ test_valid_action_values - tests action value constraints

**Test execution:**
```bash
$ python -m pytest tests/semantic/test_score_recommend.py -v
======================== 24 passed in 0.07s ========================
```

**Issues:** None

---

### 11. Capability Boundary: ✅ PASS

**Findings:**
- ✅ Depends on semantic-candidates outputs (candidates.yaml)
- ✅ Does not implement review
- ✅ Does not implement finalize
- ✅ Does not implement demand
- ✅ Remains third semantic capability only
- ✅ No scope creep
- ✅ SKILL.md explicitly states boundary

**Boundary statement from SKILL.md:**
```markdown
## Capability Boundary

**This skill ONLY handles:**
- Recommendation generation from candidates
- Scoring and priority computation
- Recommendation status/action decisions
- Traceability preservation

**This skill does NOT handle:**
- Review/finalize stages (later capabilities)
- Demand layer logic (different layer)
- Signal extraction (earlier stage)
- Candidate synthesis (earlier stage)
```

**Issues:** None

---

## Strengths

1. **Real implementation with meaningful recommendation generation** (not scaffold)
2. **Strong test coverage** (24 tests, all passing)
3. **Clear contract alignment** (candidates.yaml as primary input)
4. **Deterministic scoring logic** (stable, reproducible results)
5. **Correct priority computation** (max(business_score, value_score))
6. **Good traceability** (candidate_id, source_candidate_ids, evidence_refs preserved)
7. **Proper capability boundary** (recommend only, no scope creep)
8. **Stable IDs** (hash-based, deterministic)
9. **Comprehensive field coverage** (all required fields present)
10. **Model validation** (Pydantic enforces priority rule)

---

## Gaps

**None identified**

---

## Contradictions

**None identified**

---

## Blocking Issues

**None**

---

## Recommended Fixes

**None required** (all assessments pass)

---

## Final Decision

### ✅ Explicit Answers

1. **Is semantic-recommend a proper standard skill?** ✅ **YES**
   - Standard omc format
   - Clear decision tree and execution steps
   - Thin skill, calls Python implementation
   - Explicit capability boundary

2. **Is score_recommend.py real implementation or scaffold?** ✅ **REAL IMPLEMENTATION**
   - 429 lines of real logic
   - All functions fully implemented
   - Executable and verified
   - Deterministic scoring and recommendation generation

3. **Is scoring correct enough?** ✅ **YES**
   - Deterministic formulas
   - Priority correctly computed as max(business_score, value_score)
   - Scores within valid range (1.0-10.0)
   - Status/action values valid
   - Model validation enforces rules

4. **Are outputs contract-aligned?** ✅ **YES**
   - Correct workspace, file names, structure
   - All 4 recommendation groups present
   - All required fields present
   - Suitable for downstream use

5. **Are tests strong enough?** ✅ **YES**
   - 24 real tests
   - All passing
   - Cover all key behaviors
   - Test priority computation rule
   - Test traceability preservation
   - Test determinism

6. **Is semantic-recommend ready to be used?** ✅ **YES**
   - All assessments pass
   - No blocking issues
   - Functional verification successful
   - Contract-aligned
   - Test-backed

---

## Conclusion

**semantic-recommend implementation review: ✅ PASS**

This is a real, contract-aligned, scoring-correct, traceability-preserving, test-backed, properly bounded third semantic capability. It is ready to be used immediately as the third semantic execution unit.

---

**Review Complete**: 2026-03-17
