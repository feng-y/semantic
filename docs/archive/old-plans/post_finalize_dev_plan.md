# Post-Finalize Semantic Development Plan

**Planning Target**: Post-finalize semantic workflow system development

**Date**: 2026-03-17

**Status**: Development Roadmap

---

## Executive Summary

The five semantic capabilities (signals → candidates → recommend → review → finalize) now exist as individual skills. The immediate challenge is **not** implementing more semantic logic, but rather **turning the capability chain into a reliable, controllable, validated workflow system**.

**Immediate Next Priority**: Build semantic-runner with finalize guard integration and validation layer.

---

## Current Semantic Chain State

### ✅ Capabilities Present

1. **semantic-signals** - Extract semantic signals from FACT
2. **semantic-candidates** - Synthesize candidates from signals
3. **semantic-recommend** - Score and recommend candidates
4. **semantic-review** - Generate review decisions
5. **semantic-finalize** - Produce final semantic assets

### ✅ Composite Skills Present

- **semantic-pipeline** - Composite workflow skill
- **semantic-fact-pipeline** - FACT workflow skill

### ⚠️ Infrastructure Present But Minimal

- **src/semantic/run.py** - Basic runner (next/all modes only)
- **src/semantic/runner_models.py** - RunState model
- **src/semantic/stage_registry.py** - Stage registry
- **semantic-status** - Basic status reporting

### ❌ Critical Gaps

1. **No validation layer** - Schema drift, invalid actions, missing fields not caught
2. **No finalize guard integration** - Runner doesn't enforce verify_first blocking
3. **No incremental execution** - Full re-analysis every time
4. **No cache layer** - Expensive operations repeated
5. **No feedback loop** - Can't learn from usage
6. **Runner too minimal** - No resume, no blocking conditions, no error recovery
7. **Status not actionable** - Doesn't recommend next command

---

## Key Post-Finalize Challenges

### Challenge 1: Manual Orchestration Burden

**Problem**: Users must manually run 5 commands in sequence:
```bash
semantic-signals
semantic-candidates
semantic-recommend
semantic-review
semantic-finalize
```

**Impact**: 
- High friction
- Easy to skip steps
- No guidance on errors
- No resume after interruption

**Solution**: semantic-runner with proper orchestration

---

### Challenge 2: No Validation Guardrails

**Problem**: Invalid outputs can propagate through the chain:
- Schema drift not caught
- Invalid review actions (e.g., "reject" instead of "drop")
- Missing required fields
- Broken evidence references

**Impact**:
- Errors discovered late
- Manual debugging required
- Downstream stages fail mysteriously

**Solution**: semantic-validate capability

---

### Challenge 3: Finalize Guard Not Enforced

**Problem**: finalize_assets.py blocks on unresolved verify_first, but:
- Runner doesn't know about this
- Users don't get clear error messages
- No guidance on how to resolve

**Impact**:
- Finalize fails with unclear error
- Users don't know what to fix
- Workflow stalls

**Solution**: Integrate finalize guard into runner control flow

---

### Challenge 4: No Incremental Execution

**Problem**: Every semantic-signals run re-analyzes entire FACT baseline:
- Expensive token cost
- Long execution time
- Wasteful for small changes

**Impact**:
- High cost per iteration
- Slow feedback loop
- Users avoid re-running

**Solution**: Incremental signals extraction with change detection

---

### Challenge 5: No Status Guidance

**Problem**: semantic-status shows current state but doesn't recommend next action:
- Users must interpret state manually
- No clear guidance after errors
- No explanation of blocking conditions

**Impact**:
- Users stuck after interruptions
- Manual workflow knowledge required
- Poor user experience

**Solution**: semantic-status --next with actionable recommendations

---

## Immediate Next Priority

**Build semantic-runner with finalize guard integration and validation layer.**

### Why This Is P0

1. **Workflow coherence** - Turn 5 manual commands into 1 reliable workflow
2. **Error prevention** - Catch invalid outputs before they propagate
3. **Clear blocking** - Users understand why finalize is blocked
4. **Resume capability** - Recover from interruptions gracefully

### What This Enables

- `semantic-runner --mode all` - Run full chain with proper gating
- `semantic-runner --mode next` - Run next stage only
- `semantic-runner --resume` - Continue after interruption
- Automatic validation at stage boundaries
- Clear error messages on finalize guard violations

---

## P0 Roadmap: Workflow Reliability

### P0-1: Enhance semantic-runner

**Goal**: Turn basic runner into proper orchestration engine

**Current State**:
- `src/semantic/run.py` exists with next/all modes
- No blocking condition enforcement
- No resume capability
- No validation integration
- Minimal error handling

**Required Enhancements**:

1. **Blocking Conditions**
   - Check required inputs before each stage
   - Enforce finalize guard (verify_first blocking)
   - Show clear error messages

2. **Resume Capability**
   - Persist run-state.yaml
   - Detect completed stages
   - Skip already-completed work
   - Resume from interruption point

3. **Validation Integration**
   - Call semantic-validate before/after each stage
   - Block on validation failures
   - Show validation errors clearly

4. **Error Recovery**
   - Detect stage failures
   - Mark failed stages in state
   - Allow retry of failed stages
   - Don't proceed if upstream failed

**Implementation**:
```python
# Enhanced runner modes
semantic-runner --mode all          # Run full chain
semantic-runner --mode next         # Run next stage only
semantic-runner --resume            # Continue from last state
semantic-runner --validate-only     # Dry-run with validation
```

**Success Criteria**:
- ✅ Runner enforces finalize guard
- ✅ Runner blocks on missing required inputs
- ✅ Runner can resume after interruption
- ✅ Runner integrates validation
- ✅ Clear error messages on blocking conditions

---

### P0-2: Build semantic-validate

**Goal**: Create validation layer to catch errors early

**Validation Scope**:

1. **Schema Validation**
   - signals.yaml matches signals schema
   - candidates.yaml matches candidates schema
   - recommendations.yaml matches recommendations schema
   - review-decisions.yaml matches review-decisions schema
   - Final asset maps match output contracts

2. **Action Validation**
   - final_action in [keep, merge, drop, backlog, verify_first]
   - merge actions have merge_target
   - No invalid status values

3. **Reference Validation**
   - evidence_refs point to real evidence
   - source_recommendation_id exists
   - source_candidate_id exists
   - merge_target exists

4. **Required Field Validation**
   - All required fields present
   - No null values where not allowed
   - Metadata complete

**Implementation**:
```bash
semantic-validate --stage signals
semantic-validate --stage candidates
semantic-validate --stage recommend
semantic-validate --stage review
semantic-validate --stage finalize
semantic-validate --all
```

**Success Criteria**:
- ✅ Catches schema drift
- ✅ Catches invalid actions
- ✅ Catches missing required fields
- ✅ Catches broken references
- ✅ Clear error messages with file:line

---

### P0-3: Integrate Finalize Guard

**Goal**: Make finalize guard part of runner control flow

**Current State**:
- finalize_assets.py checks unresolved verify_first
- Blocks with print statement
- Runner doesn't know about this

**Required Integration**:

1. **Pre-Finalize Check**
   - Runner checks evidence-checks.yaml before finalize
   - Detects unresolved verify_first items
   - Blocks finalize stage
   - Shows clear error message

2. **Status Integration**
   - semantic-status shows verify_first blocking
   - Lists unresolved items
   - Explains how to resolve

3. **Error Messages**
   ```
   ⚠ Finalize blocked: 3 unresolved verify_first items
   
   Unresolved items:
   - Domain: "Proposed Domains" (check_abc123)
   - Concept: "Identified Concepts" (check_def456)
   - Demand Model: "Change Analysis Model" (check_ghi789)
   
   To resolve:
   1. Review evidence-checks.yaml
   2. Complete evidence verification
   3. Update status to "completed" or "failed"
   4. Re-run semantic-finalize
   ```

**Success Criteria**:
- ✅ Runner blocks finalize on unresolved verify_first
- ✅ Clear error message with item list
- ✅ Status shows blocking condition
- ✅ Users know how to resolve

---

### P0-4: Add semantic-status --next

**Goal**: Make status actionable with next-step recommendations

**Current State**:
- semantic-status shows current state
- No next-step recommendation
- No blocking condition explanation

**Required Enhancements**:

1. **Next Command Recommendation**
   ```bash
   $ semantic-status --next
   
   Current Stage: step3_recommend
   Completed: signals, candidates, recommend
   
   Next Command: semantic-review
   Reason: Recommendations generated, ready for review decision generation
   
   Blocking Conditions: None
   ```

2. **Blocking Condition Detection**
   ```bash
   $ semantic-status --next
   
   Current Stage: step4_review
   Completed: signals, candidates, recommend, review
   
   Next Command: BLOCKED
   Reason: Finalize blocked by 3 unresolved verify_first items
   
   To Unblock:
   1. Review evidence-checks.yaml
   2. Complete evidence verification
   3. Update status to "completed"
   ```

3. **Error Recovery Guidance**
   ```bash
   $ semantic-status --next
   
   Current Stage: step2_candidates (FAILED)
   
   Next Command: semantic-candidates --retry
   Reason: Previous candidates run failed, retry recommended
   
   Error: candidates.yaml validation failed (missing required field: evidence_refs)
   ```

**Implementation**:
```bash
semantic-status                    # Show current state
semantic-status --next             # Recommend next command
semantic-status --blocking         # Show only blocking conditions
semantic-status --errors           # Show only errors
```

**Success Criteria**:
- ✅ Recommends correct next command
- ✅ Explains blocking conditions
- ✅ Guides error recovery
- ✅ Shows clear reasoning

---

## P1 Roadmap: Efficiency & Quality

### P1-1: Incremental Signals Extraction

**Goal**: Reduce cost by only re-analyzing changed areas

**Problem**:
- semantic-signals re-analyzes entire FACT baseline
- Expensive for large repos
- Wasteful for small changes

**Solution**:

1. **Change Detection**
   - Compare current FACT baseline with previous
   - Detect added/modified/deleted facts
   - Identify affected signal categories

2. **Selective Re-Extraction**
   - Re-extract signals only from changed facts
   - Reuse cached signals for unchanged facts
   - Merge new signals with cached signals

3. **Cache Management**
   - Store signals by fact source
   - Hash-based invalidation
   - Incremental cache updates

**Implementation**:
```bash
semantic-signals --incremental     # Default: incremental mode
semantic-signals --full            # Force full re-analysis
```

**Success Criteria**:
- ✅ Incremental run 5-10x faster than full
- ✅ Incremental output equivalent to full
- ✅ Cache invalidation correct
- ✅ Token cost reduced significantly

---

### P1-2: Confidence-Based Auto-Accept

**Goal**: Reduce human review bottleneck for high-confidence items

**Problem**:
- All recommendations require manual review
- High-confidence items are obvious
- Human time wasted on low-risk decisions

**Solution**:

1. **Confidence Thresholds**
   - High confidence (>0.8): Auto-accept
   - Medium confidence (0.5-0.8): Async review
   - Low confidence (<0.5): Blocking review

2. **Auto-Accept with Audit**
   - High-confidence items auto-accepted
   - Logged in review-decisions.yaml
   - Marked as auto_accepted: true
   - Human can override later

3. **Review Priority**
   - Low-confidence items shown first
   - Medium-confidence items batched
   - High-confidence items logged only

**Implementation**:
```bash
semantic-recommend --auto-accept high
semantic-review --priority low
semantic-review --show-auto-accepted
```

**Success Criteria**:
- ✅ High-confidence items auto-accepted
- ✅ Audit log complete
- ✅ Human review time reduced 50-70%
- ✅ No loss of control

---

### P1-3: End-to-End Golden Fixture Tests

**Goal**: Verify full semantic chain with golden test suite

**Problem**:
- No end-to-end tests
- Regressions not caught
- Manual testing required

**Solution**:

1. **Golden Fixtures**
   - Sample FACT baseline
   - Expected signals.yaml
   - Expected candidates.yaml
   - Expected recommendations.yaml
   - Expected review-decisions.yaml
   - Expected final asset maps

2. **End-to-End Test**
   ```python
   def test_semantic_chain_golden():
       # Given: FACT baseline
       fact_baseline = load_fixture("fact_baseline.yaml")
       
       # When: Run full semantic chain
       result = run_semantic_pipeline(fact_baseline)
       
       # Then: Outputs match golden fixtures
       assert_yaml_equivalent(result.signals, golden_signals)
       assert_yaml_equivalent(result.candidates, golden_candidates)
       assert_yaml_equivalent(result.recommendations, golden_recommendations)
       assert_yaml_equivalent(result.review_decisions, golden_review_decisions)
       assert_yaml_equivalent(result.domain_map, golden_domain_map)
   ```

3. **Regression Detection**
   - Run on every commit
   - Catch output drift
   - Validate schema compliance

**Success Criteria**:
- ✅ Golden test suite covers full chain
- ✅ Tests catch regressions
- ✅ Tests run in CI
- ✅ Clear failure messages

---

### P1-4: Cache Layer

**Goal**: Cache expensive operations to improve performance

**Caching Targets**:

1. **AST Parsing**
   - Parse each file once
   - Cache AST by file hash
   - Reuse on unchanged files

2. **Fact Extraction**
   - Cache extracted facts by file
   - Invalidate on file change
   - Merge cached + new facts

3. **Signal Inference**
   - Cache signals by fact source
   - Invalidate on fact change
   - Reuse unchanged signals

4. **Candidate Synthesis**
   - Cache candidates by signal set
   - Invalidate on signal change
   - Reuse unchanged candidates

**Implementation**:
```python
# Cache structure
.semantic-cache/
  ast/
    {file_hash}.json
  facts/
    {file_hash}.yaml
  signals/
    {fact_hash}.yaml
  candidates/
    {signal_hash}.yaml
```

**Success Criteria**:
- ✅ Cache hit rate >80% on incremental runs
- ✅ Performance improvement 5-10x
- ✅ Cache invalidation correct
- ✅ No stale data issues

---

## Later-Stage Ideas

### Feedback Loop from Usage

**Goal**: Learn from real usage to improve semantic quality

**What to Track**:
- Which domains/concepts/rules are queried most
- Which evidence is referenced most
- Which recommendations are accepted/rejected
- Which validation errors occur most

**What to Improve**:
- Signal extraction patterns
- Candidate synthesis heuristics
- Recommendation scoring weights
- Review criteria

**Why Later**: Need stable workflow and usage data first

---

### LSP Integration

**Goal**: Improve symbol extraction accuracy using LSP

**Benefits**:
- Better domain boundary detection
- More accurate concept definitions
- Precise dependency tracking

**Why Later**: Current extraction is good enough, LSP adds complexity

---

### Multi-Format Export

**Goal**: Export semantic assets in multiple formats

**Formats**:
- JSON (machine-consumable)
- GraphQL (queryable)
- Markdown (human-readable, already exists)

**Why Later**: YAML is sufficient for now, focus on workflow first

---

### Interactive Review UI

**Goal**: Better review experience than YAML editing

**Features**:
- Visual diff of recommendations
- One-click accept/reject
- Bulk operations
- Evidence preview

**Why Later**: YAML editing works, UI is polish not necessity

---

### Distributed Execution

**Goal**: Parallelize expensive stages across workers

**Benefits**:
- Faster execution on large repos
- Better resource utilization

**Why Later**: Single-machine execution is fast enough for now

---

## What Should NOT Be Prioritized Yet

### ❌ Full GraphQL API Platform

**Why Not**: Premature platformization. Need stable workflow first.

**When**: After P1 complete and usage patterns understood.

---

### ❌ Heavy Visualization Dashboard

**Why Not**: Markdown views are sufficient. Visualization is polish.

**When**: After workflow is proven and user demand is clear.

---

### ❌ Generalized Plugin Ecosystem

**Why Not**: Don't know what plugins are needed yet.

**When**: After semantic layer is stable and extension points are clear.

---

### ❌ Multi-Agent Orchestration Framework

**Why Not**: Single-agent workflow is simpler and sufficient.

**When**: Only if distributed execution becomes necessary.

---

### ❌ Interactive Shell with REPL

**Why Not**: CLI commands are sufficient. REPL adds complexity.

**When**: Only if interactive exploration becomes a common use case.

---

### ❌ Broad Platformization

**Why Not**: Platform features are premature before workflow stability.

**When**: After P0 and P1 complete, usage patterns clear, and demand proven.

---

## Why Runner Matters Now

### Problem Without Runner

Users must:
1. Manually run 5 commands in sequence
2. Remember correct order
3. Check outputs manually
4. Interpret errors manually
5. Decide what to run next manually

### Solution With Runner

Runner:
1. Runs full chain automatically
2. Enforces correct order
3. Validates outputs automatically
4. Shows clear error messages
5. Recommends next action automatically

### Impact

- **Friction reduced**: 5 commands → 1 command
- **Errors caught early**: Validation at stage boundaries
- **Clear guidance**: Users know what to do next
- **Resume capability**: Recover from interruptions
- **Finalize guard enforced**: No invalid finalizations

---

## Why Validation Matters Now

### Problem Without Validation

Invalid outputs propagate:
- Schema drift not caught
- Invalid actions accepted
- Missing fields ignored
- Broken references undetected

Errors discovered late:
- Finalize fails mysteriously
- Manual debugging required
- Wasted execution time

### Solution With Validation

Validation catches errors early:
- Schema violations at stage boundaries
- Invalid actions before propagation
- Missing fields before downstream use
- Broken references before finalize

Clear error messages:
- File:line location
- Expected vs actual
- How to fix

### Impact

- **Errors caught early**: Before propagation
- **Clear diagnostics**: Know exactly what's wrong
- **Faster debugging**: No mystery failures
- **Higher quality**: Invalid outputs blocked

---

## Why Status/Control Surface Matters Now

### Problem Without Status Guidance

Users stuck after interruptions:
- Don't know current stage
- Don't know what to run next
- Don't understand blocking conditions
- Manual workflow knowledge required

### Solution With Status --next

Status provides guidance:
- Shows current stage
- Recommends next command
- Explains blocking conditions
- Guides error recovery

### Impact

- **Reduced friction**: Users know what to do
- **Faster recovery**: Clear guidance after errors
- **Better UX**: No manual workflow knowledge needed
- **Lower support burden**: Self-service troubleshooting

---

## Why Composite Pipeline Skills Matter (But Are Secondary)

### Composite Skills Exist

- semantic-pipeline (signals → finalize)
- semantic-fact-pipeline (discover → baseline)

### Why They Matter

- **User convenience**: Single command for full workflow
- **Discoverability**: Clear entry points
- **Documentation**: Self-documenting workflow

### Why They're Secondary to Runner

Composite skills are **invocation convenience**, not **orchestration engine**.

- Composite skill: "Run these 5 skills in sequence"
- Runner: "Orchestrate stages with validation, blocking, resume, error recovery"

Composite skills **delegate to runner** for actual orchestration.

### Relationship

```
User invokes: semantic-pipeline
  ↓
Composite skill delegates to: semantic-runner --mode all
  ↓
Runner orchestrates: signals → candidates → recommend → review → finalize
  ↓
Runner enforces: validation, blocking, finalize guard
```

---

## Final Recommendation

### Summary

**Build semantic-runner with validation and finalize guard integration first (P0).** This turns the five semantic capabilities into a reliable, controllable workflow system. **Then add incremental execution and auto-accept to reduce cost and friction (P1).** Defer platformization until workflow is proven stable.

### Rationale

The semantic chain exists but lacks:
1. **Orchestration** - Manual 5-command sequence
2. **Validation** - Errors propagate uncaught
3. **Control** - No guidance on next steps
4. **Efficiency** - Full re-analysis every time

P0 fixes orchestration, validation, and control.
P1 fixes efficiency and quality.
Later stages add polish and platform features.

### Execution Risk

**Highest Risk**: Building platform features before workflow is stable.

**Mitigation**: Strict P0 focus on workflow reliability. Defer all platformization to later stages.

### Success Criteria

**P0 Complete When**:
- ✅ semantic-runner --mode all runs full chain with validation
- ✅ Finalize guard integrated and enforced
- ✅ semantic-status --next provides actionable guidance
- ✅ Clear error messages on all blocking conditions

**P1 Complete When**:
- ✅ Incremental execution reduces cost 5-10x
- ✅ Auto-accept reduces human review time 50-70%
- ✅ Golden test suite catches regressions
- ✅ Cache layer improves performance 5-10x

**Ready for Later Stages When**:
- ✅ P0 and P1 complete
- ✅ Workflow proven stable in production use
- ✅ Usage patterns understood
- ✅ Clear demand for platform features

---

## Recommended Execution Sequence

1. **P0-1**: Enhance semantic-runner (2-3 weeks)
2. **P0-2**: Build semantic-validate (1-2 weeks)
3. **P0-3**: Integrate finalize guard (1 week)
4. **P0-4**: Add semantic-status --next (1 week)
5. **P1-1**: Incremental signals extraction (2-3 weeks)
6. **P1-2**: Confidence-based auto-accept (1-2 weeks)
7. **P1-3**: End-to-end golden tests (1 week)
8. **P1-4**: Cache layer (2-3 weeks)
9. **Later**: Feedback loop, LSP, multi-format export (as needed)

**Total P0**: 5-7 weeks
**Total P1**: 6-9 weeks
**Total P0+P1**: 11-16 weeks

---

**Plan Status**: Ready for Execution

**Next Action**: Begin P0-1 (semantic-runner enhancement)

**Plan Owner**: Semantic Layer Development Team

**Review Date**: 2026-03-17
