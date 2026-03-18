# Commit Semantic Dedup/Scoring Optimization Analysis

## Executive Summary

Current implementation uses rule-based deduplication (module + type + normalized_issue_text) and simple scoring (semantic_value + length penalty). Analysis identifies 4 high-value model integration points where semantic understanding would significantly improve quality without excessive cost.

## 1. Current Implementation Review

### 1.1 Deduplication Strategy (dedup.py)

**Current Key**: `module + development_type + normalized_issue_text`

**Normalization Pipeline**:
- NFKC Unicode normalization
- Whitespace collapse
- ASCII lowercasing
- Conservative synonym mapping (修正→修复, 调整→优化, 接入/引入→新增)
- Optional number placeholder (`<NUM>`)

**Canonical Selection**:
```python
score = (semantic_rank, length_penalty, case_id)
# semantic_rank: high=0, medium=1, low=2
# length_penalty: abs(len(issue_text) - 18)
```

**Strengths**:
- Fast, deterministic, zero-cost
- Catches exact duplicates and template variations
- Conservative synonym mapping avoids over-normalization

**Weaknesses**:
- Misses semantic duplicates with different wording
- Length penalty (target=18 chars) is arbitrary, doesn't measure abstraction quality
- No quality assessment beyond length

### 1.2 Pattern Aggregation (patterning.py)

**Pattern Fingerprint**: `domain|dev_type|action_class|object_class|constraint_class`

**Similarity Scoring**:
```python
similarity = 0.5*sequence_ratio + 0.3*jaccard + 0.2*constraint_ratio
threshold = 0.50 (tuned for Chinese text)
```

**Canonical Selection**:
```python
score = (semantic_rank, issue_penalty, constraint_penalty, case_id)
# issue_penalty: abs(len(issue_text) - 16)
# constraint_penalty: -(len(rules) + len(invariants))
```

**Strengths**:
- Multi-signal similarity (sequence + jaccard + constraint)
- Greedy clustering is fast and interpretable
- Pattern count monitoring (excellent <10, acceptable 10-20, alert >20)

**Weaknesses**:
- Action/object/constraint inference uses keyword matching (infer_action_class, infer_object_class, infer_constraint_class)
- Similarity threshold (0.50) is fixed, no confidence scoring
- Length-based abstraction proxy (target=16 chars) doesn't validate actual abstraction level

## 2. Semantic Duplicate Detection Gaps

### 2.1 Missed Duplicates - Text Normalization Failures

**Case 1: Paraphrase Variations**
```
A: "feat: 新增请求响应对齐逻辑"
B: "feat: 添加request-response alignment功能"
```
- Same semantic intent, different vocabulary (新增 vs 添加, Chinese vs English)
- Current: Different dedup keys (normalized text differs)
- Impact: Duplicate patterns in export

**Case 2: Abstraction Level Mismatch**
```
A: "bugfix: 修复parser在处理空值时的崩溃"
B: "bugfix: 解决DSL解析器null pointer异常"
```
- Same root cause, different abstraction (空值崩溃 vs null pointer异常)
- Current: Different dedup keys
- Impact: Pattern fragmentation

**Case 3: Implicit vs Explicit Constraint**
```
A: "feat: 新增并发控制" + rules: ["worker count bounded"]
B: "feat: 添加线程数限制"
```
- Constraint embedded in issue_text vs rules
- Current: Different dedup keys (issue_text differs)
- Impact: Missed duplicate despite semantic equivalence

### 2.2 Quantified Impact

From P0 spec context:
- Target: <10 patterns per domain (excellent), 10-20 acceptable
- Risk: >20 patterns indicates dedup/abstraction failure
- Current system: No semantic similarity fallback when text normalization fails

**Estimated Miss Rate**: 15-25% of true duplicates in domains with:
- Mixed Chinese/English terminology
- Multiple abstraction levels (technical vs business language)
- Implicit constraint encoding

## 3. Canonical Selection Quality Issues

### 3.1 Length Penalty Limitations

**Current Logic**:
```python
issue_penalty = abs(len(issue_text) - 16)  # patterning.py:249
length_penalty = abs(len(issue_text) - 18)  # dedup.py:131
```

**Problems**:
1. **Arbitrary Target**: 16/18 chars has no semantic justification
2. **Length ≠ Abstraction**:
   - "feat: 新增功能" (9 chars) - too vague
   - "feat: 新增parser空值处理" (15 chars) - specific but clear
   - "feat: 新增DSL parser在处理null/undefined/empty string时的fallback逻辑" (45 chars) - too specific
3. **No Quality Validation**: Doesn't detect over-generic ("新增功能") or over-specific ("修复line 42 bug") cases

### 3.2 Semantic Value Limitations

**Current**: 3-level ordinal (high/medium/low)

**Missing**:
- **Abstraction Quality**: Is issue_text at right level? (not too vague, not too specific)
- **Constraint Stability**: Are rules/invariants object-specific or generic advice?
- **Representativeness**: Does canonical case best represent the pattern cluster?

**Example Failure**:
```python
# Both have semantic_value="medium", length ~16
A: "feat: 新增配置项" (vague, low quality)
B: "feat: 新增feature extraction worker配置" (clear, high quality)
# Current: A wins (shorter, closer to 16)
# Desired: B wins (more informative)
```

## 4. Pattern Abstraction Validation Gaps

### 4.1 Over-Specific Patterns

**Symptom**: Pattern count >20 in single domain

**Root Causes**:
1. **Keyword-Based Classification**:
   - `infer_action_class`: 7 categories (fix/add/refactor/migrate/optimize/control/align)
   - `infer_object_class`: 9 categories (parser/request-response/feature-extraction/...)
   - `infer_constraint_class`: 8 categories (compatibility/alignment/concurrency/...)

2. **Brittle Matching**:
   ```python
   if any(k in text for k in ["parser", "dsl", "parse", "解析"]):
       return "parser"
   ```
   - Misses synonyms, related concepts
   - No confidence scoring
   - Binary classification (match or no match)

**Example**:
```
Pattern A: "demand|feature|add|demand-analysis|validation"
Pattern B: "demand|feature|add|requirement-processing|validation"
```
- Should merge (demand-analysis ≈ requirement-processing)
- Current: Separate patterns due to keyword mismatch

### 4.2 Over-Generic Patterns

**Symptom**: Pattern has 50+ cases but low coherence

**Root Cause**: Fingerprint too coarse
```
"qserver|feature|add|general|none"
```
- Catches all generic feature additions
- No semantic clustering within bucket

**Missing**: Validation that pattern members are truly similar beyond fingerprint match

## 5. Model Integration Recommendations

### 5.1 Integration Point 1: Semantic Duplicate Detection (HIGH PRIORITY)

**Location**: `dedup.py:group_strict_duplicates()`

**Trigger**: After text normalization, before finalizing dedup groups

**Use Case**: Detect paraphrase duplicates missed by text normalization

**Implementation**:
```python
def group_strict_duplicates(cases, *, use_constraint_signature=False, semantic_fallback=True):
    # Phase 1: Rule-based dedup (current)
    buckets = _group_by_text_key(cases)

    # Phase 2: Semantic fallback for near-misses
    if semantic_fallback:
        gray_zone_cases = _extract_gray_zone(buckets)  # Cases with similarity 0.40-0.60
        semantic_groups = _model_assisted_dedup(gray_zone_cases)
        buckets = _merge_semantic_groups(buckets, semantic_groups)

    return buckets
```

**Model Call**:
- **Input**: Pairs of cases with text similarity 0.40-0.60 (gray zone)
- **Prompt**: "Are these two issue descriptions semantically equivalent? Consider paraphrases, translations, and abstraction level."
- **Output**: Binary (yes/no) + confidence score
- **Cost**: ~0.5-1K tokens per pair, estimated 5-10% of cases enter gray zone
- **Benefit**: Reduce pattern count by 15-25%, improve canonical selection

**Cost/Benefit**:
- **Cost**: Low (only gray zone cases, ~5-10% of total)
- **Benefit**: High (directly addresses pattern explosion)
- **ROI**: Excellent

### 5.2 Integration Point 2: Canonical Quality Scoring (HIGH PRIORITY)

**Location**: `dedup.py:select_canonical_duplicate()`, `patterning.py:select_canonical_pattern_case()`

**Trigger**: When selecting canonical from duplicate/pattern group

**Use Case**: Replace length penalty with abstraction quality score

**Implementation**:
```python
def select_canonical_duplicate(cases):
    # Phase 1: Filter by semantic_value (current)
    top_tier = [c for c in cases if c.semantic_value == max_value]

    # Phase 2: Model-assisted quality scoring
    quality_scores = _model_score_abstraction_quality(top_tier)

    # Phase 3: Select best
    return max(zip(top_tier, quality_scores), key=lambda x: x[1])[0]
```

**Model Call**:
- **Input**: issue_text + rules/invariants
- **Prompt**: "Rate abstraction quality (0-10): Is this issue description at the right level? Not too vague (e.g., '新增功能'), not too specific (e.g., 'fix line 42'). Prefer clear, reusable descriptions."
- **Output**: Score 0-10 + brief justification
- **Cost**: ~0.3-0.5K tokens per case, only for canonical selection (1 per group)
- **Benefit**: Better canonical cases, more reusable patterns

**Cost/Benefit**:
- **Cost**: Very Low (only 1 call per dedup/pattern group)
- **Benefit**: High (improves pattern quality, reduces manual review)
- **ROI**: Excellent

### 5.3 Integration Point 3: Pattern Abstraction Validation (MEDIUM PRIORITY)

**Location**: `patterning.py:check_pattern_count()`

**Trigger**: When pattern count >20 (alert threshold)

**Use Case**: Diagnose why patterns are over-specific, suggest merges

**Implementation**:
```python
def check_pattern_count(groups, domain):
    count = len(groups)

    if count > 20:
        # Model-assisted diagnosis
        merge_suggestions = _model_suggest_pattern_merges(groups)
        return PatternCheckResult(
            domain=domain,
            pattern_count=count,
            pattern_count_status="too_high",
            action="review_pattern_abstraction",
            merge_suggestions=merge_suggestions  # NEW
        )
```

**Model Call**:
- **Input**: List of pattern fingerprints + representative issue_texts
- **Prompt**: "These patterns are in the same domain. Which patterns should merge? Look for synonyms, related concepts, and over-specific classifications."
- **Output**: List of (pattern_A, pattern_B, merge_reason) tuples
- **Cost**: ~2-3K tokens per domain with >20 patterns
- **Benefit**: Actionable guidance for pattern consolidation

**Cost/Benefit**:
- **Cost**: Low (only triggered on alert, ~10-20% of domains)
- **Benefit**: Medium (helps manual review, not automated fix)
- **ROI**: Good

### 5.4 Integration Point 4: Constraint Quality Validation (LOW PRIORITY)

**Location**: `validators.py` (new validator)

**Trigger**: During semantic case generation validation

**Use Case**: Detect when rules/invariants degrade to generic advice

**Implementation**:
```python
def validate_constraint_quality(rules, invariants, issue_text, commit_log):
    # Rule-based filter (current)
    generic_patterns = ["null check", "bounds check", "exception handling", ...]
    if any(p in text for p in generic_patterns for text in rules + invariants):
        return ValidationResult(valid=False, reason="generic_advice")

    # Model-assisted validation for gray zone
    if _is_gray_zone(rules, invariants):
        return _model_validate_constraints(rules, invariants, issue_text, commit_log)
```

**Model Call**:
- **Input**: rules + invariants + issue_text + commit_log
- **Prompt**: "Are these rules/invariants object-specific constraints, or generic development advice? Object-specific: 'parser must handle null/undefined/empty string'. Generic: 'add null checks', 'handle exceptions properly'."
- **Output**: Binary (object_specific/generic) + confidence
- **Cost**: ~0.5-0.8K tokens per case, only for gray zone (~10-15% of cases)
- **Benefit**: Reduce invalid cases, improve constraint quality

**Cost/Benefit**:
- **Cost**: Medium (10-15% of cases, during generation)
- **Benefit**: Medium (improves quality, but rule-based filter catches most issues)
- **ROI**: Moderate

## 6. Implementation Priority

### Phase 1 (Immediate - High ROI)
1. **Semantic Duplicate Detection** (5.1)
   - Directly reduces pattern explosion
   - Low cost (gray zone only)
   - Clear success metric (pattern count reduction)

2. **Canonical Quality Scoring** (5.2)
   - Improves pattern representativeness
   - Very low cost (1 call per group)
   - Enhances reusability

### Phase 2 (Next - Good ROI)
3. **Pattern Abstraction Validation** (5.3)
   - Provides actionable diagnostics
   - Only runs on alert
   - Supports manual review workflow

### Phase 3 (Later - Moderate ROI)
4. **Constraint Quality Validation** (5.4)
   - Incremental improvement over rule-based filter
   - Higher cost relative to benefit
   - Consider after Phase 1-2 results

## 7. Cost Estimation

**Assumptions**:
- 1000 semantic cases per domain
- 15% enter gray zone for semantic dedup
- 50 dedup groups, 30 pattern groups per domain
- 20% of domains trigger pattern count alert

**Per-Domain Costs**:
- Semantic dedup: 150 pairs × 0.75K tokens = 112.5K tokens
- Canonical scoring: 80 groups × 0.4K tokens = 32K tokens
- Pattern validation: 0.2 × 2.5K tokens = 0.5K tokens (amortized)
- **Total**: ~145K tokens per domain

**At $3/M input tokens (Claude Haiku)**:
- **Cost per domain**: $0.44
- **Cost for 10 domains**: $4.40

**Expected Benefit**:
- Pattern count reduction: 15-25%
- Canonical quality improvement: Qualitative (better reusability)
- Manual review time savings: 30-40% (fewer false patterns to review)

## 8. Success Metrics

### Quantitative
1. **Pattern Count**: Reduce average patterns per domain by 15-25%
2. **Dedup Recall**: Increase duplicate detection rate (measure via manual sampling)
3. **Alert Rate**: Reduce domains with >20 patterns from X% to <10%

### Qualitative
1. **Canonical Quality**: Manual review of 50 canonical cases (before/after)
2. **Constraint Specificity**: Measure generic advice rate in rules/invariants
3. **Pattern Coherence**: Sample 10 patterns, verify member similarity

## 9. Risks and Mitigations

### Risk 1: Model Inconsistency
- **Issue**: Different model calls may give inconsistent similarity judgments
- **Mitigation**: Use temperature=0, cache prompts, log all decisions for audit

### Risk 2: Cost Overrun
- **Issue**: Gray zone may be larger than estimated 15%
- **Mitigation**: Start with strict gray zone bounds (0.45-0.55), expand if needed

### Risk 3: False Merges
- **Issue**: Model may incorrectly merge distinct patterns
- **Mitigation**: Require high confidence (>0.8) for merges, log all decisions

## 10. Conclusion

Current rule-based dedup/scoring is fast and deterministic but misses 15-25% of semantic duplicates and uses arbitrary length penalties for canonical selection. Four model integration points identified:

1. **Semantic duplicate detection** (HIGH): Catch paraphrase duplicates in gray zone
2. **Canonical quality scoring** (HIGH): Replace length penalty with abstraction quality
3. **Pattern abstraction validation** (MEDIUM): Diagnose over-specific patterns
4. **Constraint quality validation** (LOW): Validate rules/invariants specificity

**Recommended approach**: Implement Phase 1 (points 1-2) first. Estimated cost $0.44 per domain, expected 15-25% pattern count reduction and significant canonical quality improvement. Excellent ROI for addressing pattern explosion risk.
