# Semantic Foundation

**目的**: 语义层设计文档和合约定义

**状态**: 设计参考文档

---

## 目录结构

### semantic/
语义层设计文档、合约定义和实现指南

**保留的设计文档**:
- `semantic_stage_contracts.md` - 5阶段语义层合约（核心）
- `semantic_design.md` - 整体语义层设计
- `semantic_input_contract.md` - 输入消费规则
- `semantic_output_contract.md` - 输出规范
- `semantic_runner_design.md` - 运行器设计
- `semantic_normalization_rules.md` - 规范化规则
- `00_overall_design.md` - 总体设计（中文，历史参考）
- `01_step1_signal_inference.md` - Step1 信号推断设计
- `01_step2_candidate_synthesis.md` - Step2 候选合成设计
- `03_step4_review_and_evidence_design.md` - Step4 审查和证据设计
- `04_step5_finalize_design.md` - Step5 最终化设计
- `README.md` - 语义层文档索引

**示例文件**:
- `domain-map.md`, `concept-map.md`, `rule-map.md`, `demand-model-map.md` - 输出示例
- `signals.md`, `candidates.md` - 中间产物示例

---

## 与 docs/fact/ 的区别

### docs/fact/ (运行时工件)
- **用途**: FACT 层运行时生成的版本化工件
- **内容**: 实际的发现、审查、精炼和基线工件
- **生成**: 由 `semantic-harness` 插件在运行时生成
- **结构**:
  - `schemas/` - 工件模式定义
  - `discovery/` - 版本化发现工件 (*.vN.md)
  - `review/` - 审查总结和架构师反馈
  - `baseline/` - 已接受的不可变基线

### docs/semantic-foundation/ (设计文档)
- **用途**: 语义层的设计文档和合约
- **内容**: 架构决策、合约定义、实现指南
- **维护**: 手动维护的设计文档
- **结构**:
  - `semantic/` - 语义层设计和合约

---

## 归档内容

临时审查文件、修复结果和过时的 FACT 样本已归档到:
`docs/archive/semantic-foundation-legacy/`

查看归档说明: [docs/archive/semantic-foundation-legacy/README.md](../archive/semantic-foundation-legacy/README.md)

---

## 相关文档

- [USER_GUIDE.md](../../USER_GUIDE.md) - 用户指南
- [README.md](../../README.md) - 项目说明
- [docs/semantic-design/](../semantic-design/) - 语义设计 ADR
