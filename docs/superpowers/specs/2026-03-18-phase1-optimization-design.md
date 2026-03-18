# Phase 1 Dedup/Scoring Optimization Design

**Date:** 2026-03-18
**Status:** Approved
**Priority:** High ROI

## Executive Summary

Add model-assisted semantic understanding to deduplication and canonical selection. Model has **final authority** on what's duplicate and what's canonical, with rule-based logic as efficiency pre-filter.

**Key Principle:** Model优先 (Model-first) - rules reduce cost, model decides quality.

**Expected Impact:**
- Pattern count reduction: 15-25%
- Canonical quality improvement: Qualitative (better reusability)
- Cost: ~$0.44 per domain (1000 cases)

## 1. Architecture Overview

### 1.1 Core Principle

Model calls are **opt-in enhancements** that have final authority when enabled. The system works without models; models improve quality when available.

### 1.2 Two Integration Points

**Integration Point 1: Semantic Duplicate Detection** (`dedup.py`)
- After rule-based dedup groups cases by normalized text
- Extract "gray zone" pairs with similarity 0.40-0.60
- Use model to determine if they're semantic duplicates
- Model decision overrides rule-based grouping

**Integration Point 2: Canonical Quality Scoring** (`dedup.py` + `patterning.py`)
- When selecting canonical from duplicate/pattern group
- Replace arbitrary length penalty with model-scored abstraction quality
- Model rates: "Is this issue_text at the right abstraction level?"
- Score 0-10, highest score wins

### 1.3 Control Flags

- Single flag: `--use-model-optimization` (default: False)
- When `True`: model has final authority on dedup + quality
- When `False`: pure rule-based (current behavior)

### 1.4 Cost Control

- Rule-based pre-filter reduces model calls by 85-90%
- Gray zone filtering limits semantic dedup to ~5-10% of cases
- Quality scoring: 1 call per group (not per case)
- Estimated cost: $0.44 per domain (1000 cases)

## 2. Semantic Duplicate Detection (Model-Driven)

### 2.1 Process Flow

```python
def group_strict_duplicates(cases, *, use_model_optimization=False):
    # Phase 1: Rule-based pre-filter (efficiency)
    rule_buckets = _group_by_text_key(cases)  # Fast exact match

    if not use_model_optimization:
        return rule_buckets  # Stop here if model disabled

    # Phase 2: Model-driven gray zone resolution
    gray_zone_pairs = _extract_gray_zone_pairs(rule_buckets)  # similarity 0.40-0.60

    # Phase 3: Model decides which pairs are semantic duplicates
    semantic_merges = _model_check_semantic_duplicates(gray_zone_pairs)

    # Phase 4: Apply model decisions (merge groups)
    final_buckets = _apply_semantic_merges(rule_buckets, semantic_merges)

    return final_buckets
```

### 2.2 Gray Zone Detection

- Compare all pairs across different rule-based buckets
- Calculate text similarity using existing `pair_similarity()` from patterning.py
- Extract pairs with similarity 0.40-0.60 (uncertain zone)
- This is where model judgment is most valuable

### 2.3 Model Call

**Prompt:**
```
Compare these two issue descriptions:
A: {issue_text_a}
B: {issue_text_b}

Are they semantically equivalent? Consider:
- Paraphrases (新增 vs 添加)
- Translations (Chinese vs English)
- Abstraction level (空值崩溃 vs null pointer异常)

Answer: yes/no
Confidence: 0.0-1.0
```

**Response Format:**
```json
{
  "is_duplicate": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}
```

### 2.4 Merge Strategy

- Only merge if model says "yes" AND confidence > 0.8
- Log all merge decisions to audit log
- Preserve both case_ids in merged group

## 3. Canonical Quality Scoring (Model-Driven)

### 3.1 Process Flow

```python
def select_canonical_duplicate(cases, *, use_model_optimization=False):
    if not use_model_optimization:
        return _select_by_rules(cases)  # Fallback to length penalty

    # Phase 1: Filter by semantic_value (keep only top tier)
    top_tier = _filter_by_semantic_value(cases)

    # Phase 2: Model scores abstraction quality for all candidates
    quality_scores = _model_score_abstraction_quality(top_tier)

    # Phase 3: Select highest quality score
    best_idx = quality_scores.index(max(quality_scores))
    return top_tier[best_idx]
```

### 3.2 Model Call

**Prompt:**
```
Rate the abstraction quality of this issue description (0-10):

Issue: {issue_text}
Rules: {rules}
Invariants: {invariants}

Criteria:
- Not too vague (e.g., "feat: 新增功能" = bad, score 2-3)
- Not too specific (e.g., "fix line 42 bug" = bad, score 2-3)
- Clear and reusable (e.g., "feat: 新增parser空值处理" = good, score 8-9)
- Appropriate detail level for the domain

Score: 0-10 (integer)
Reason: brief explanation
```

**Response Format:**
```json
[
  {"case_id": "...", "score": 8, "reason": "..."},
  ...
]
```

### 3.3 Scoring Strategy

- Model scores ALL candidates in the group (not just top 2-3)
- Batch scoring in single request for efficiency
- Cache scores by (issue_text, rules, invariants) tuple
- Log score + reason for each candidate

### 3.4 Fallback Behavior

- If model call fails: fall back to rule-based selection (length penalty)
- If model returns invalid score: use median score (5.0)
- Always log fallback events for monitoring

## 4. Implementation Details

### 4.1 File Structure

```
src/commit_semantic/
├── dedup.py                    # Modified: add model-driven dedup
├── patterning.py               # Modified: add model-driven canonical selection
├── model_optimizer.py          # NEW: model call logic
└── prompt_runner.py            # Existing: reuse for caching + error handling
```

### 4.2 New Module: `model_optimizer.py`

**Core Functions:**

```python
def check_semantic_duplicates(
    pairs: List[Tuple[DedupInput, DedupInput]]
) -> List[SemanticDuplicateResult]:
    """Check if pairs are semantic duplicates using model."""

def score_abstraction_quality(
    cases: List[DedupInput]
) -> List[QualityScore]:
    """Score abstraction quality of issue_text using model."""
```

**Data Structures:**

```python
@dataclass
class SemanticDuplicateResult:
    case_a_id: str
    case_b_id: str
    is_duplicate: bool
    confidence: float
    reason: str

@dataclass
class QualityScore:
    case_id: str
    score: float  # 0-10
    reason: str
```

### 4.3 Integration with `dedup.py`

```python
from .model_optimizer import check_semantic_duplicates, score_abstraction_quality

def group_strict_duplicates(
    cases: Iterable[DedupInput],
    *,
    use_constraint_signature: bool = False,
    use_model_optimization: bool = False,  # NEW
) -> list[DedupGroup]:
    # Phase 1: Rule-based grouping
    buckets = _group_by_text_key(cases, use_constraint_signature)

    if not use_model_optimization:
        return _finalize_groups(buckets)

    # Phase 2: Model-driven gray zone resolution
    gray_pairs = _extract_gray_zone_pairs(buckets)
    if gray_pairs:
        dup_results = check_semantic_duplicates(gray_pairs)
        buckets = _apply_semantic_merges(buckets, dup_results)

    return _finalize_groups(buckets)
```

### 4.4 CLI Integration

```bash
# Enable model optimization
python skills/commit-semantic-export/run.py \
  --input-dir data/semantic_cases \
  --use-model-optimization
```

```python
# skills/commit-semantic-export/run.py
parser.add_argument(
    '--use-model-optimization',
    action='store_true',
    help='Enable model-assisted dedup and canonical selection (costs API tokens)'
)
```

### 4.5 Caching Strategy

- Use `prompt_runner.py` existing cache mechanism
- Cache key format: `"dup_{case_a_id}_{case_b_id}"` for duplicate checks
- Cache key format: `"quality_{issue_text_hash}"` for quality scores
- Cache persists across runs

## 5. Error Handling and Logging

### 5.1 Error Handling Strategy

**Error Types:**

| Error Type | Strategy | Fallback Behavior |
|------------|----------|-------------------|
| Rate limit | Exponential backoff retry (3 attempts) | If exhausted: use safe default |
| Auth error | Fail fast, log error | Use safe default for remaining calls |
| Parse error | Log raw response, skip retry | Use safe default |
| Timeout | Retry once with longer timeout | Use safe default |
| Network error | Retry with backoff | Use safe default |

**Safe Defaults:**

- Duplicate check: `is_duplicate=False` (conservative, avoids false merges)
- Quality score: `score=5.0` (neutral, doesn't bias selection)

### 5.2 Retry Logic

```python
def _check_pair_with_retry(
    case_a: DedupInput,
    case_b: DedupInput,
    max_retries: int = 3
) -> SemanticDuplicateResult:
    """Check pair with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return _check_pair(case_a, case_b)
        except ModelAPIError as e:
            if e.is_retryable and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise
```

### 5.3 Logging Levels

- **DEBUG**: Detailed model I/O (prompt, response)
- **INFO**: Normal operations (pairs checked, scores computed)
- **WARNING**: Recoverable issues (low confidence, parse errors)
- **ERROR**: Failed operations (API errors, max retries exceeded)

### 5.4 Audit Log

**Location:** `data/exports/model_decisions.jsonl`

**Format:**
```json
{
  "timestamp": "2026-03-18T10:30:00Z",
  "decision_type": "duplicate_check",
  "input": {
    "case_a_id": "...",
    "case_a_issue": "...",
    "case_b_id": "...",
    "case_b_issue": "..."
  },
  "output": {
    "is_duplicate": true,
    "confidence": 0.9,
    "reason": "paraphrase"
  },
  "metadata": {
    "model": "claude-haiku",
    "tokens": 150,
    "cost_usd": 0.0005
  }
}
```

### 5.5 Metrics Reporting

**Metrics Tracked:**
- Total calls
- Successful calls
- Failed calls
- Cache hits
- Total tokens
- Total cost (USD)

**Output:**
```
Model Optimization Metrics:
---------------------------
Total calls:      150
Successful:       145 (96.7%)
Failed:           5 (3.3%)
Cache hits:       30 (20.0%)
Total tokens:     112,500
Total cost:       $0.44
```

### 5.6 Summary Export Enhancement

Add to `data/exports/summary.json`:

```json
{
  "model_optimization": {
    "enabled": true,
    "metrics": {
      "total_calls": 150,
      "successful_calls": 145,
      "failed_calls": 5,
      "cache_hits": 30,
      "total_tokens": 112500,
      "total_cost_usd": 0.44
    },
    "duplicate_checks": {
      "total_pairs": 150,
      "duplicates_found": 23,
      "avg_confidence": 0.87
    },
    "quality_scoring": {
      "total_cases": 80,
      "avg_score": 7.2
    }
  }
}
```

## 6. Testing Strategy

### 6.1 Test Structure

```
tests/
├── test_model_optimizer.py           # Unit tests for model calls
├── test_dedup_model_integration.py   # Integration tests for dedup
├── test_patterning_model_integration.py  # Integration tests for patterning
└── test_model_optimization_e2e.py    # End-to-end with real cases
```

### 6.2 Unit Tests

**Coverage:**
- Model response parsing (valid/invalid JSON)
- Error handling (API errors, timeouts, parse errors)
- Safe defaults (duplicate=False, score=5.0)
- Retry logic (exponential backoff)
- Caching behavior

### 6.3 Integration Tests

**Coverage:**
- Gray zone extraction (similarity 0.40-0.60)
- Semantic merge application
- Canonical selection by quality score
- Model disabled fallback
- Error recovery

### 6.4 End-to-End Tests

**Coverage:**
- Full pipeline with model optimization enabled
- Cost estimation (verify model call count)
- Pattern count reduction (15-25% expected)
- Canonical quality improvement

### 6.5 Test Coverage Goals

- Unit tests: 100% coverage of `model_optimizer.py`
- Integration tests: All code paths in modified `dedup.py` and `patterning.py`
- E2E tests: Full pipeline with real commit history (HEAD~50..HEAD)

## 7. Configuration

```python
@dataclass
class ModelOptimizerConfig:
    """Configuration for model optimization."""

    # Retry settings
    max_retries: int = 3
    retry_backoff_base: float = 2.0

    # Confidence thresholds
    duplicate_confidence_threshold: float = 0.8
    quality_score_min: float = 0.0
    quality_score_max: float = 10.0

    # Gray zone bounds
    gray_zone_similarity_min: float = 0.40
    gray_zone_similarity_max: float = 0.60

    # Model settings
    model_name: str = "claude-haiku"
    temperature: float = 0.0  # Deterministic
    max_tokens: int = 500

    # Logging
    audit_log_path: str = "data/exports/model_decisions.jsonl"
    enable_audit_log: bool = True
    log_level: str = "INFO"
```

## 8. Success Metrics

### 8.1 Quantitative

1. **Pattern Count**: Reduce average patterns per domain by 15-25%
2. **Dedup Recall**: Increase duplicate detection rate (measure via manual sampling)
3. **Cost**: Verify actual cost matches estimate ($0.44 per domain)

### 8.2 Qualitative

1. **Canonical Quality**: Manual review of 50 canonical cases (before/after)
2. **Pattern Coherence**: Sample 10 patterns, verify member similarity
3. **User Feedback**: Collect feedback on pattern reusability

## 9. Risks and Mitigations

### 9.1 Model Inconsistency

**Risk:** Different model calls may give inconsistent similarity judgments

**Mitigation:**
- Use temperature=0 for deterministic responses
- Cache all model responses
- Log all decisions to audit log for review

### 9.2 Cost Overrun

**Risk:** Gray zone may be larger than estimated 15%

**Mitigation:**
- Start with strict gray zone bounds (0.45-0.55)
- Monitor actual gray zone percentage
- Expand bounds gradually if needed

### 9.3 False Merges

**Risk:** Model may incorrectly merge distinct patterns

**Mitigation:**
- Require high confidence (>0.8) for merges
- Log all merge decisions
- Provide manual review tool for audit log

## 10. Implementation Plan

### Phase 1: Core Implementation (3-4 days)

1. Create `model_optimizer.py` with core functions
2. Modify `dedup.py` to integrate semantic duplicate detection
3. Modify `patterning.py` to integrate quality scoring
4. Add CLI flag `--use-model-optimization`

### Phase 2: Error Handling & Logging (1-2 days)

1. Implement retry logic with exponential backoff
2. Add comprehensive error handling
3. Implement audit log
4. Add metrics tracking and reporting

### Phase 3: Testing (2-3 days)

1. Write unit tests for `model_optimizer.py`
2. Write integration tests for dedup and patterning
3. Write end-to-end tests
4. Manual testing on real repository

### Phase 4: Documentation & Review (1 day)

1. Update README with `--use-model-optimization` flag
2. Document cost estimates and success metrics
3. Code review and refinement

**Total Estimated Time:** 7-10 days

## 11. Backward Compatibility

- Default behavior unchanged (`use_model_optimization=False`)
- Existing tests continue to pass
- No breaking changes to API or data formats
- Model optimization is purely additive feature

## 12. Future Enhancements (Out of Scope)

- Integration Point 3: Pattern abstraction validation (MEDIUM priority)
- Integration Point 4: Constraint quality validation (LOW priority)
- Async/parallel model calls for better performance
- Support for multiple model providers (OpenAI, etc.)
