# IBS Stage Acceptance Checklist

## Stage 1 — 输出契约建模

必须满足：
- IBS 输出模型文档存在
- goals / constraints / workflows / inputs-outputs / components / boundaries 的 schema 草案存在
- core + minimum analysis pack 的 template 草案存在
- contract tests 存在
- stage1 report 已生成

---

## Stage 2 — Core Baseline

必须满足：
- 能产出：
  - purpose.md
  - pipelines.md
  - domains.md
  - concepts.md
- 有 validator
- 有 tests
- 有 report

---

## Stage 3 — Intent Pack

必须满足：
- 至少实现：
  - goals.md
  - constraints.md
- 有 validator
- 有 tests
- 有 report

---

## Stage 4 — Behavior Pack

必须满足：
- 至少实现：
  - workflows.md
  - inputs-outputs.md
- 有 validator
- 有 tests
- 有 report

---

## Stage 5 — Structure Pack

必须满足：
- 至少实现：
  - components.md
  - boundaries.md
- 有 validator
- 有 tests
- 有 report

---

## Stage 6 — 回归与统一验证

必须满足：
- schema / template / validator / runtime context 无明显 drift
- acceptance 后 baseline 输出路径可用
- 全量 pytest 通过
- IBS e2e tests 通过
- regression report 生成

---

## 最低交付标准

### Core Baseline
- purpose
- pipelines
- domains
- concepts

### Minimum Analysis Pack
- goals
- constraints
- workflows
- inputs-outputs
- components
- boundaries

如果低于此标准，最终报告必须明确写：

`FULL IBS IMPLEMENTATION INCOMPLETE`
