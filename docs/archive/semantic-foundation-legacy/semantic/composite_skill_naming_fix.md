# Composite Skill Naming Fix

**Fix Date**: 2026-03-17
**Executor**: Claude Opus 4.6
**Fix Type**: Naming Normalization

---

## Fix Target

Normalize composite skill naming to use clear, task-oriented names that follow Claude Code skill conventions.

---

## Naming Decisions Applied

### Final Canonical Names

1. **semantic-fact-pipeline**
   - Purpose: Run FACT pipeline workflow
   - Sequence: discover → review → refine → baseline
   - Scope: FACT layer only

2. **semantic-pipeline**
   - Purpose: Run semantic workflow
   - Sequence: signals → candidates → recommend → review → finalize
   - Scope: Semantic layer only

### Deprecated Names

- **semantic-layer-pipeline** ❌
  - Reason: "layer" is redundant and architecture-focused
  - Replacement: `semantic-pipeline`

---

## Rationale

### Why These Names?

**Task-Oriented:**
- Names express what the user wants to do (run a pipeline)
- Not architecture labels (layer, stage, etc.)

**Clear Scope:**
- `semantic-fact-pipeline` = FACT workflow
- `semantic-pipeline` = Semantic workflow
- No ambiguity about which layer

**Consistent Pattern:**
- Both use `-pipeline` suffix
- Both use `semantic-` prefix (repo context)
- Parallel structure

**Claude Code Conventions:**
- Task/workflow skills should be action-oriented
- Avoid architecture terminology in skill names
- Keep names concise and clear

---

## Files Created

### 1. skills/semantic-pipeline/SKILL.md

**Purpose**: Composite skill for semantic workflow

**Key Features:**
- Sequences 5 semantic capabilities
- Clear gating conditions (stops if verify_first unresolved)
- `disable-model-invocation: true`
- Task-oriented description

**Pipeline:**
```
signals → candidates → recommend → review → finalize
```

---

### 2. skills/semantic-fact-pipeline/SKILL.md

**Purpose**: Composite skill for FACT workflow

**Key Features:**
- Sequences 4 FACT stages
- Stops for human review
- `disable-model-invocation: true`
- Task-oriented description

**Pipeline:**
```
discover → review (manual) → refine → baseline
```

---

## Files Updated

None (composite skills did not previously exist)

---

## Applied Changes

### Change 1: Created Composite Skills
**Issue**: No composite skills existed
**Resolution**: Created both with final canonical names

### Change 2: Task-Oriented Naming
**Issue**: Naming needed to be task-oriented
**Resolution**: Used clear workflow names without "layer"

### Change 3: Proper Frontmatter
**Issue**: Skills needed proper configuration
**Resolution**: Added `disable-model-invocation: true` and clear metadata

### Change 4: Gating Conditions
**Issue**: Skills needed clear stop conditions
**Resolution**: Documented when pipeline stops and requires manual intervention

---

## Skill Design Principles Applied

### 1. Thin Orchestration
- Skills describe sequence, not implementation
- Delegate to individual capability skills
- No business logic in composite skills

### 2. Clear Gating
- **semantic-fact-pipeline**: Stops for human review
- **semantic-pipeline**: Stops if verify_first items unresolved

### 3. Manual Invocation
- Both skills use `disable-model-invocation: true`
- Intended for direct user invocation
- Not auto-triggered

### 4. Success Criteria
- Each skill lists expected artifacts
- Clear checklist for completion
- Easy to verify success

---

## Remaining Risks

### Risk 1: Untested in Real Workflow
**Severity**: Low
**Mitigation**: Skills are thin orchestration, low complexity

### Risk 2: May Need Adjustment
**Severity**: Low
**Mitigation**: Can iterate based on usage patterns

---

## Final Decision

### ✅ naming_aligned: true

**Confirmation:**
- ✅ `semantic-fact-pipeline` is the final FACT composite skill name
- ✅ `semantic-pipeline` is the final semantic composite skill name
- ✅ `semantic-layer-pipeline` has been deprecated (never created)
- ✅ Naming and references are now aligned
- ✅ Names are task-oriented and clear

---

## Explicit Confirmations

### No New Semantic Business Logic
✅ **Confirmed** - Only created orchestration skills, no new logic

### Old FACT Runtime Behavior Unchanged
✅ **Confirmed** - No modifications to existing FACT skills

### Unrelated Skills Not Renamed
✅ **Confirmed** - Only created new composite skills, no renames

---

## Usage Examples

### Run FACT Pipeline
```bash
/semantic-fact-pipeline
```

### Run Semantic Pipeline
```bash
/semantic-pipeline
```

---

## Next Steps

1. Test composite skills in real workflow
2. Adjust gating conditions if needed
3. Add more detailed error handling if needed
4. Consider adding progress tracking

---

## Summary

Successfully created two composite skills with clean, task-oriented names:
- `semantic-fact-pipeline` for FACT workflow
- `semantic-pipeline` for semantic workflow

Both skills follow Claude Code conventions, use thin orchestration, and have clear gating conditions. No existing code was modified, and naming is now aligned across the repository.
