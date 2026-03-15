# IBS 实施与评审计划（多阶段）

## 总体原则

- 只按阶段顺序推进
- 每个阶段必须：
  - 开发
  - 测试
  - review
  - 修复
  - 再测试
  - commit
- 不等待人工确认
- 不重构主 discover/refine 执行器
- 不改 public skill set

---

## Stage 1 — IBS 输出契约建模

目标：
- 建立 IBS 输出模型
- 新增 schema 草案
- 新增 template 草案

主要产出：
- `docs/semantic-design/011-ibs-output-model.md`
- `docs/semantic/schemas/` 下的 IBS 新 schema
- `docs/semantic/templates/` 下的 IBS templates

测试：
- `tests/test_ibs_contracts_stage1.py`

报告：
- `docs/review/ibs_stage1_contract_report.md`

commit:
- `ibs: stage1 output contract and templates`

---

## Stage 2 — Core Baseline 实现

目标：
- 实现最小核心输出：
  - purpose.md
  - pipelines.md
  - domains.md
  - concepts.md

测试：
- `tests/test_ibs_core_stage2.py`

报告：
- `docs/review/ibs_stage2_core_report.md`

commit:
- `ibs: stage2 core baseline generation`

---

## Stage 3 — Intent 扩展

目标：
- 实现：
  - goals.md
  - constraints.md
- 推荐补：
  - non-goals.md
  - success-criteria.md

测试：
- `tests/test_ibs_intent_stage3.py`

报告：
- `docs/review/ibs_stage3_intent_report.md`

commit:
- `ibs: stage3 intent analysis pack`

---

## Stage 4 — Behavior 扩展

目标：
- 实现：
  - workflows.md
  - inputs-outputs.md
- 推荐补：
  - state-transitions.md
  - failure-handling.md

测试：
- `tests/test_ibs_behavior_stage4.py`

报告：
- `docs/review/ibs_stage4_behavior_report.md`

commit:
- `ibs: stage4 behavior analysis pack`

---

## Stage 5 — Structure 扩展

目标：
- 实现：
  - components.md
  - boundaries.md
- 推荐补：
  - data-models.md
  - interfaces.md

测试：
- `tests/test_ibs_structure_stage5.py`

报告：
- `docs/review/ibs_stage5_structure_report.md`

commit:
- `ibs: stage5 structure analysis pack`

---

## Stage 6 — 回归与统一验证

目标：
- 统一 schema / template / validator / runtime context
- 做 IBS 端到端验证

测试：
- `tests/test_ibs_end_to_end_stage6.py`
- 全量 `pytest`

报告：
- `docs/review/ibs_stage6_regression_report.md`

commit:
- `ibs: stage6 regression and validation hardening`

---

## 最终报告

生成：

`docs/review/ibs_implementation_final_report.md`

必须包含：

- stage-by-stage 摘要
- files modified / created
- tests added
- deferred items
- remaining risks
- final verdict
