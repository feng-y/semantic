# Code Review Action Plan - 2026-03-17

Based on the comprehensive code review in `docs/review/code-review-20260317.md`

---

## Summary

**Total Issues**: 10
- 🔴 High Priority (Correctness/Bugs): 3
- 🟡 Medium Priority (Design): 4
- 🟢 Low Priority (Readability): 3

---

## 🔴 High Priority Issues

### Issue #1: `_next_version` lock file residue problem
**Location**: `src/artifact_writer.py:65-91`
**Status**: ⏳ To Fix
**Priority**: P1

**Problem**:
- Empty lock files left by failed `_atomic_write` are not filtered by `_find_versions`
- Causes version number gaps (v1, v3, v5...)
- Functionally works but wastes version numbers

**Solution**:
- Add empty file filtering in `_find_versions` or `_next_version`
- Skip files with `st_size == 0` when calculating next version

**Estimated Effort**: 30 minutes

---

### Issue #2: `plugin.json` parsed with `yaml.safe_load` instead of `json.loads`
**Location**: `src/skill_loader.py:135`
**Status**: ⏳ To Fix
**Priority**: P1

**Problem**:
- JSON file parsed as YAML (works but confusing)
- Error messages say "Invalid JSON... YAML error"
- Comments contradict actual behavior

**Solution**:
```python
# Change from:
plugin_data = yaml.safe_load(plugin_json_path.read_text())

# To:
import json
plugin_data = json.loads(plugin_json_path.read_text())
```

**Estimated Effort**: 15 minutes

---

### Issue #3: `_find_bullets_after_label` unclear break logic
**Location**: `src/change_analysis_generator.py:116`
**Status**: ⏳ To Fix
**Priority**: P2

**Problem**:
- Inner `break` semantics unclear
- Breaks on any non-bullet line (but empty lines already filtered)
- Correct but hard to read

**Solution**:
- Use explicit `else` branch or clearer conditions
- Add comments explaining the logic

**Estimated Effort**: 20 minutes

---

## 🟡 Medium Priority Issues

### Issue #4: `artifact_validation.py` validation too weak
**Location**: `src/artifact_validation.py`
**Status**: ⏳ To Fix
**Priority**: P0 (affects quality)

**Problem**:
- Uses OR logic (any one section passes)
- `repo-facts` only needs 1 of 5 sections to pass
- Accepts structurally incomplete outputs

**Solution**:
- Distinguish `required_sections` (AND) vs `optional_sections` (OR)
- For critical artifacts like repo-facts, require all sections
- Update validation logic and tests

**Estimated Effort**: 2-3 hours

---

### Issue #5: `VALIDATION_STEP_TARGETS` hardcoded indices
**Location**: `src/discovery_executor.py:64-67`
**Status**: ⏳ To Fix
**Priority**: P0 (silent bugs)

**Problem**:
- Validation targets tied to absolute step indices
- Reordering steps in SKILL.md breaks validation silently
- No validation if index doesn't match

**Solution**:
- Add `validate: <artifact-name>` field to SKILL.md steps
- Read validation target from step declaration
- Remove hardcoded index mapping

**Estimated Effort**: 1-2 hours

---

### Issue #6: FACT/Semantic layer integration boundary unclear
**Location**: Design level
**Status**: ⏳ To Document/Fix
**Priority**: P1

**Problem**:
- No programmatic interface between FACT and Semantic layers
- Semantic reads `fact_canonical_sample.yaml` (looks like placeholder)
- No formal "FACT baseline complete" event
- Independent state machines

**Solution**:
- Document integration approach in README
- Check for `baseline/checkpoint.json` before semantic layer
- Remove `_sample` suffix dependencies
- Or formalize the interface

**Estimated Effort**: 2-3 hours

---

### Issue #7: `_execute_patch_step` is dead code
**Location**: `src/refine_executor.py:312-361`
**Status**: ⏳ To Fix
**Priority**: P2

**Problem**:
- Function exists but has no callers
- Replaced by `_execute_staged_patches()`
- Unclear if intentionally kept

**Solution**:
- Delete the function
- Or add comment explaining it's kept for single-artifact patching

**Estimated Effort**: 10 minutes

---

## 🟢 Low Priority Issues

### Issue #8: Circular import workaround in `context_builder`
**Location**: `src/context_builder.py:271`
**Status**: ⏳ To Refactor
**Priority**: P2

**Problem**:
- Lazy import to avoid circular dependency
- `validate_artifact_content` belongs in `artifact_validation.py`
- Indicates coupling issue

**Solution**:
- Move dispatch logic to `artifact_validation.py`
- Eliminate circular dependency at root

**Estimated Effort**: 1 hour

---

### Issue #9: `_check_sampling_timeout` update timing
**Location**: `src/discovery_executor.py:441-448`
**Status**: ⏳ To Document
**Priority**: P3

**Problem**:
- Logic correct but not intuitive
- Once switched, subsequent calls don't re-set `sampling_mode_switched`
- Needs clarifying comment

**Solution**:
- Add comment explaining the behavior
- No code change needed

**Estimated Effort**: 5 minutes

---

### Issue #10: Test code duplication
**Location**: `tests/` directory
**Status**: ⏳ To Refactor
**Priority**: P3

**Problem**:
- `test_system.py` (24KB), `test_step8_verification.py` (26KB) have repetitive setup
- Duplicate `tmp_path` initialization, `fake_executor` construction

**Solution**:
- Extract common fixtures to `conftest.py`
- Centralize test utilities

**Estimated Effort**: 2-3 hours

---

## Recommended Execution Order

### Phase 1: Quick Wins (1 hour)
1. Issue #2: JSON parsing (15 min)
2. Issue #7: Remove dead code (10 min)
3. Issue #9: Add comment (5 min)
4. Issue #3: Clarify break logic (20 min)

### Phase 2: Critical Quality (3-4 hours)
5. Issue #5: Fix hardcoded validation indices (1-2 hours) ⚠️ **HIGHEST PRIORITY**
6. Issue #4: Strengthen validation logic (2-3 hours)

### Phase 3: Design Improvements (3-4 hours)
7. Issue #6: Document/fix FACT-Semantic integration (2-3 hours)
8. Issue #8: Eliminate circular import (1 hour)

### Phase 4: Code Quality (3-4 hours)
9. Issue #1: Fix version number gaps (30 min)
10. Issue #10: Refactor test fixtures (2-3 hours)

---

## Total Estimated Effort

- **Phase 1**: 1 hour
- **Phase 2**: 3-4 hours (CRITICAL)
- **Phase 3**: 3-4 hours
- **Phase 4**: 3-4 hours

**Total**: 10-13 hours

---

## Next Actions

1. ✅ Create this action plan
2. ⏳ Start with Phase 1 (quick wins)
3. ⏳ Then Phase 2 (critical quality issues)
4. ⏳ Document decisions and trade-offs

---

**Status**: Plan Created
**Date**: 2026-03-17
**Owner**: Development Team
