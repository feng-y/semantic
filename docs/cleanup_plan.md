# docs 目录清理计划

**目标**: 清理已实现的临时文档，保留设计文档

---

## 📊 当前文档分类

### 🗑️ 需要清理（已实现/临时分析）

#### docs/plan/
- `incremental_signals_implementation.md` - P0-1 实现计划（已完成）
- `incremental_signals_review.md` - P0-1 review（已完成）
- `p0-1_completion_report.md` - P0-1 完成报告（已完成）
- `p0-1_incremental_signals_summary.md` - P0-1 总结（已完成）

#### docs/review/
- `phase2_development_report.md` - Phase 2 开发报告（已完成）
- `phase2_final_review.md` - Phase 2 最终审查（已完成）
- `p0-1_final_review.md` - P0-1 最终审查（已完成）
- `semantic_layer_deep_review.md` - Semantic 初始分析（已修正）
- `semantic_layer_deep_review_corrected.md` - Semantic 修正版（已整合）
- `semantic-layer-review-20260317.md` - Semantic 原始分析（已整合）
- `worktree_p0-1_test_failure_analysis.md` - Worktree 测试分析（已解决）
- `worktree_p0-1_bug_or_sync_ut.md` - Bug 分析（已解决）
- `worktree_p0-1_solution_comparison.md` - 方案对比（已执行）
- `worktree_p0-1_merge_strategy.md` - 合并策略（已执行）
- `worktree_p0-1_merge_final.md` - 最终合并建议（已执行）

---

### ✅ 保留（设计文档/活跃问题）

#### docs/architecture/ (设计文档)
- `fact-layer-design.md` - FACT 层设计 ✅
- `semantic-layer-design.md` - Semantic 层设计 ✅
- `demand-layer-design.md` - Demand 层设计 ✅

#### docs/review/ (活跃分析)
- `semantic_layer_review_final.md` - Semantic 层最终分析（包含待修复问题）✅
- `fix_plan_prioritized.md` - 修复计划（待执行）✅

---

## 🎯 清理操作

### 创建归档目录
```bash
mkdir -p docs/archive/phase2
mkdir -p docs/archive/p0-1
mkdir -p docs/archive/worktree-analysis
```

### 归档 Phase 2 文档
```bash
mv docs/review/phase2_development_report.md docs/archive/phase2/
mv docs/review/phase2_final_review.md docs/archive/phase2/
```

### 归档 P0-1 文档
```bash
mv docs/plan/incremental_signals_implementation.md docs/archive/p0-1/
mv docs/plan/incremental_signals_review.md docs/archive/p0-1/
mv docs/plan/p0-1_completion_report.md docs/archive/p0-1/
mv docs/plan/p0-1_incremental_signals_summary.md docs/archive/p0-1/
mv docs/review/p0-1_final_review.md docs/archive/p0-1/
```

### 归档 Worktree 分析文档
```bash
mv docs/review/worktree_p0-1_test_failure_analysis.md docs/archive/worktree-analysis/
mv docs/review/worktree_p0-1_bug_or_sync_ut.md docs/archive/worktree-analysis/
mv docs/review/worktree_p0-1_solution_comparison.md docs/archive/worktree-analysis/
mv docs/review/worktree_p0-1_merge_strategy.md docs/archive/worktree-analysis/
mv docs/review/worktree_p0-1_merge_final.md docs/archive/worktree-analysis/
```

### 归档 Semantic 旧分析
```bash
mv docs/review/semantic_layer_deep_review.md docs/archive/semantic-analysis/
mv docs/review/semantic_layer_deep_review_corrected.md docs/archive/semantic-analysis/
mv docs/review/semantic-layer-review-20260317.md docs/archive/semantic-analysis/
```

---

## 📁 清理后的目录结构

```
docs/
├── architecture/          # 设计文档（保留）
│   ├── fact-layer-design.md
│   ├── semantic-layer-design.md
│   └── demand-layer-design.md
│
├── review/               # 活跃分析（保留）
│   ├── semantic_layer_review_final.md
│   └── fix_plan_prioritized.md
│
└── archive/              # 归档（已完成的文档）
    ├── phase2/
    │   ├── phase2_development_report.md
    │   └── phase2_final_review.md
    ├── p0-1/
    │   ├── incremental_signals_implementation.md
    │   ├── incremental_signals_review.md
    │   ├── p0-1_completion_report.md
    │   ├── p0-1_incremental_signals_summary.md
    │   └── p0-1_final_review.md
    ├── worktree-analysis/
    │   ├── worktree_p0-1_test_failure_analysis.md
    │   ├── worktree_p0-1_bug_or_sync_ut.md
    │   ├── worktree_p0-1_solution_comparison.md
    │   ├── worktree_p0-1_merge_strategy.md
    │   └── worktree_p0-1_merge_final.md
    └── semantic-analysis/
        ├── semantic_layer_deep_review.md
        ├── semantic_layer_deep_review_corrected.md
        └── semantic-layer-review-20260317.md
```

---

## ✅ 保留的文档说明

### docs/architecture/ (设计文档)
- **fact-layer-design.md** - FACT 层架构设计，长期参考
- **semantic-layer-design.md** - Semantic 层架构设计，长期参考
- **demand-layer-design.md** - Demand 层架构设计，长期参考

### docs/review/ (活跃问题)
- **semantic_layer_review_final.md** - 包含待修复的问题（Issue S1-S6）
- **fix_plan_prioritized.md** - 修复计划，待执行

---

## 🗑️ 归档的文档说明

### Phase 2 归档
- 已完成的 Phase 2 开发和审查文档
- 保留作为历史记录

### P0-1 归档
- P0-1 增量信号提取的实现和审查文档
- 功能已合并到 main

### Worktree 分析归档
- Worktree 测试失败分析和解决方案
- 问题已解决，保留作为参考

### Semantic 分析归档
- 早期的 Semantic 层分析（有误判）
- 已被 semantic_layer_review_final.md 替代

---

## 📝 执行清理

执行上述归档操作后，提交：

```bash
git add docs/
git commit -m "docs: reorganize documentation - archive completed work

Archived:
- Phase 2 reports (completed)
- P0-1 implementation docs (merged)
- Worktree analysis (resolved)
- Old semantic analysis (superseded)

Kept:
- Architecture designs (fact/semantic/demand)
- Active issue analysis (semantic_layer_review_final.md)
- Fix plan (fix_plan_prioritized.md)

Result: Cleaner docs structure, easier to find active documents"
git push
```

