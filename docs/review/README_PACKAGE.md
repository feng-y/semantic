# 纯 IBS 实施包

这个包只用于 **IBS（Intent / Behavior / Structure）实施**，不包含当前 repo 的稳定性修复任务。

适用前提：

- 当前 repo 的 runtime / contract / validation 修复正在单独推进
- 本包只负责后续的 IBS 设计与实现
- 不扩展 scope，不处理 repo stabilization

## 包内文件

1. `ibs_requirements_and_constraints.md`
   - IBS 的完整需求与约束设计

2. `ibs_implementation_plan.md`
   - 多阶段实施与 review 计划

3. `ibs_stage_acceptance_checklist.md`
   - 每个 stage 的最小通过条件

4. `ibs_team_execution_model.md`
   - 面向 OMC Teams 的执行模型与职责分工

5. `omc_ibs_activation_prompt.md`
   - 可直接交给 OMC / Claude Code 的完整 IBS 激活 prompt

## 建议放置位置

建议将这些文件放到 repo：

```text
docs/review/
```

例如：

```text
docs/review/ibs_requirements_and_constraints.md
docs/review/ibs_implementation_plan.md
docs/review/ibs_stage_acceptance_checklist.md
docs/review/ibs_team_execution_model.md
docs/review/omc_ibs_activation_prompt.md
```

## 执行顺序

1. Stage 1 — IBS Contract
2. Stage 2 — Core Baseline
3. Stage 3 — Intent Pack
4. Stage 4 — Behavior Pack
5. Stage 5 — Structure Pack
6. Stage 6 — Regression and Validation

## 注意

这个包不要求 OMC 拥有固定命名的 agent。
只要求 OMC 使用其可用的 team 能力完成：

- 分析
- 实现
- 测试
- review
- 文档
