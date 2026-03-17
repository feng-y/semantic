# Semantic Foundation Legacy Archive

**归档日期**: 2026-03-17  
**原因**: 路径标准化 - 统一使用 `docs/fact/` 作为运行时工件标准路径

---

## 归档内容

本目录包含 `docs/semantic-foundation/` 的历史内容，这些内容在项目重构过程中被替代或过时。

### 归档分类

#### 1. 设计文档（已保留在原位置）
以下设计文档**未归档**，保留在 `docs/semantic-foundation/semantic/` 用于参考：
- `semantic_stage_contracts.md` - 5阶段语义层合约定义 ✓
- `semantic_design.md` - 整体语义层设计 ✓
- `semantic_input_contract.md` - 输入消费规则 ✓
- `semantic_output_contract.md` - 输出规范 ✓
- `semantic_runner_design.md` - 运行器设计 ✓
- `semantic_normalization_rules.md` - 规范化规则 ✓
- `00_overall_design.md` - 总体设计（中文，历史参考）✓
- `01_step1_signal_inference.md` - Step1 设计 ✓
- `01_step2_candidate_synthesis.md` - Step2 设计 ✓
- `03_step4_review_and_evidence_design.md` - Step4 设计 ✓
- `04_step5_finalize_design.md` - Step5 设计 ✓
- `README.md` - 文档索引 ✓

#### 2. 临时审查文件（已归档）
归档到 `semantic/`:
- `*_review.md`, `*_review.yaml` - 各种审查文档
- `*_fix_result.md`, `*_fix_result.yaml` - 修复结果文档
- `*_check.md`, `*_check.yaml` - 检查文档
- `*_implementation_complete.md` - 实现完成报告
- `P0-1_*.md` - P0-1 实现总结
- `composite_skill_naming_fix.yaml` - 临时修复数据

#### 3. FACT 样本文件（已归档）
归档到 `fact/`:
- `fact_canonical_sample.yaml` - FACT 规范样本
- `fact_working_summary_sample.yaml` - FACT 工作总结样本
- `fact_*.md` - FACT 相关文档
- `FACT_ASSESSMENT.md` - FACT 层评估

这些内容已被 `docs/fact/` 中的实际实现替代。

---

## 当前标准路径

### FACT 层（运行时工件）
**路径**: `docs/fact/`  
**用途**: FACT 层运行时生成的版本化工件  
**包含**:
- `schemas/` - 工件模式定义
- `discovery/` - 版本化发现工件 (*.vN.md)
- `review/` - 审查总结和架构师反馈
- `baseline/` - 已接受的不可变基线

### 语义层设计（设计文档）
**路径**: `docs/semantic-foundation/semantic/`  
**用途**: 语义层设计文档和合约  
**包含**: 设计文档、合约定义、实现指南

---

## 归档统计

- **semantic/** 子目录: ~35 个临时文件
- **fact/** 子目录: ~11 个样本文件
- **根目录**: 1 个评估文档

**总计**: 约 47 个文件已归档

---

## 迁移说明

如果你需要引用旧内容：

1. **设计文档** - 仍在 `docs/semantic-foundation/semantic/`
2. **临时文件** - 已归档到此目录的 `semantic/` 子目录
3. **FACT 样本** - 已归档到此目录的 `fact/` 子目录
4. **实际运行时工件** - 在 `docs/fact/`

---

## 相关文档

- [docs/semantic-foundation/README.md](../semantic-foundation/README.md) - 语义基础说明
- [USER_GUIDE.md](../../USER_GUIDE.md) - 用户指南
- [README.md](../../README.md) - 项目说明
- [CHANGELOG.md](../../CHANGELOG.md) - 变更日志
