# FACT 和 SEMANTIC 两阶段分析

**分析日期**: 2026-03-16
**分析者**: Claude Opus 4.6
**目标**: 理解 FACT 和 SEMANTIC 两阶段的关系、职责和当前状态

---

## 执行摘要

**层次关系**: FACT (事实层) → SEMANTIC (语义层) → DEMAND (需求层，未实现)

**FACT 状态**: ✅ 已实现流程，✅ 已定义契约，❌ baseline 文件未生成

**SEMANTIC 状态**: ✅ 已定义契约，✅ 已完成设计，✅ 已创建骨架，❌ 逻辑未实现

**关键发现**: 两阶段职责清晰分离，当前阻塞是 baseline 文件缺失，但可通过使用 canonical YAML 绕过

---

## 一、FACT 阶段（事实层）

### 1.1 角色定位

**核心职责**: 提取和验证可观察的仓库事实

**定位**: "是什么" (What IS)

**特点**:
- 基于证据（file:line 引用）
- 可追溯
- 低解释性
- 版本化
- 人工验证

### 1.2 输入

**主要输入**:
- 仓库代码（.py, .yaml, .md, .skill, .prompt 等）
- 配置文件（manifest.yaml, pyproject.toml）
- Git 历史（可选）

**辅助输入**:
- 现有 baseline（如果存在，用于变更分析）

### 1.3 输出

**发现阶段输出** (`docs/fact/discovery/`):
- `repo-facts.vN.md` - 可观察的仓库结构
- `repo-understanding.vN.md` - 目的、流程、概念（带证据）
- `domain-candidates.vN.md` - 候选域边界
- `knowledge-confidence.vN.md` - 置信度评估

**审核阶段输出** (`docs/fact/review/`):
- `review-summary.vN.md` - 审核总结
- `architect-feedback.md` - 架构师反馈

**基线阶段输出** (`docs/fact/baseline/`):
- `purpose.md` - 系统目的和非目标
- `pipelines.md` - 关键执行流程
- `domains.md` - 域边界
- `concepts.md` - 核心概念
- `checkpoint.json` - 版本元数据

**规范化输出** (`docs/semantic-foundation/fact/`):
- `fact_canonical_sample.yaml` - 纯可观察事实（11.8KB）
- `fact_working_summary_sample.yaml` - 解释性内容（11.8KB）

### 1.4 流程

```
discover (提取) → review (验证) → refine (修正) → baseline (固化)
```

**discover**: 扫描仓库，提取事实
**review**: 呈现给架构师审核
**refine**: 应用修正，重新生成
**baseline**: 合成不可变的基线

### 1.5 FACT 不负责

❌ 语义建模（domain boundaries, concept relationships）
❌ 业务规则提取
❌ 需求模型结构
❌ 变更影响分析
❌ 架构设计决策

### 1.6 当前状态

✅ **已实现**:
- discover/review/refine/baseline 流程
- 技能注册（semantic-discover, semantic-review, semantic-refine, semantic-baseline）
- 版本化输出
- 架构师反馈循环

✅ **已定义**:
- canonical/working 分离契约
- fact_canonical_contract.md（冻结的规范契约）
- fact_contract_mapping.md（canonical/working 边界规则）

✅ **已生成**:
- fact_canonical_sample.yaml（11.8KB，高质量）
- fact_working_summary_sample.yaml（11.8KB，高质量）

❌ **未生成**:
- docs/fact/baseline/*.md（目录存在但为空，只有 .keep 文件）

### 1.7 FACT 输出质量

**fact_canonical_sample.yaml** (11.8KB):
- ✅ 包含：repo_identity, modules, entrypoints, core_entities, configuration, dependencies, execution_flows
- ✅ 所有字段都有证据引用（file:line）
- ✅ 结构清晰，schema 友好
- ✅ 低歧义，低解释性

**fact_working_summary_sample.yaml** (11.8KB):
- ✅ 包含：system_purpose, pipelines, concepts, domain_proposals, relationships, open_questions
- ✅ 解释性内容，置信度评级
- ✅ 为 SEMANTIC 提供引导上下文

---

## 二、SEMANTIC 阶段（语义层）

### 2.1 角色定位

**核心职责**: 从 FACT 推断语义信号，合成语义模型

**定位**: "意味着什么" (What MEANS)

**特点**:
- 语义抽象
- 关系提取
- 模型合成
- 人工审核
- 最终固化

### 2.2 输入

**主要硬输入** (Primary Hard Input):
- `fact_canonical_sample.yaml` - 可观察事实（主要）
- `docs/fact/baseline/*.md` - 稳定基线（主要，但当前缺失）

**辅助软输入** (Auxiliary Soft Input):
- `fact_working_summary_sample.yaml` - 解释性内容（辅助）

**参考输入** (Reference Input):
- `docs/fact/discovery/*.vN.md` - 发现阶段工件
- `docs/fact/review/*.vN.md` - 审核阶段工件

**消费规则**:
- 信任 canonical 为真实来源
- 使用 working summary 作为引导，而非硬真相
- 冲突时：canonical wins, evidence wins, baseline wins, explicit wins

### 2.3 输出

**Step1 输出** (Signal Inference):
- `signals.yaml` - 语义信号（canonical）
- `signals.md` - 信号摘要（view）

**Step2 输出** (Candidate Synthesis):
- `candidates.yaml` - 候选模型（canonical）
- `candidates.md` - 候选摘要（view）

**Step3 输出** (Scoring & Recommendation):
- `recommendations.yaml` - 评分推荐（canonical）
- `recommendations.md` - 推荐摘要（view）

**Step4 输出** (Review & Evidence):
- `review-decisions.yaml` - 审核决策（canonical）
- `evidence-checks.yaml` - 证据检查（canonical）
- `review-note.md` - 审核笔记（view）

**Step5 输出** (Finalize):
- `domain-map.yaml` - 域映射（canonical）
- `concept-map.yaml` - 概念映射（canonical）
- `rule-map.yaml` - 规则映射（canonical）
- `demand-model-map.yaml` - 需求模型映射（canonical）
- `change-log.yaml` - 变更日志（canonical）
- `run-state.yaml` - 运行状态（canonical）
- `domain-map.md`, `concept-map.md`, `rule-map.md`, `demand-model-map.md` - 最终视图（view）

**输出位置**: `docs/semantic/`

### 2.4 流程

```
Step1 (signals) → Step2 (candidates) → Step3 (recommend) → Step4 (review) → Step5 (finalize)
```

**Step1**: 从 FACT 提取语义信号
**Step2**: 合成候选域/概念/规则
**Step3**: 评分和推荐
**Step4**: 架构师审核 + 证据验证
**Step5**: 生成最终语义模型

### 2.5 信号类型

**domain_signals**: 域边界指示器
- 模块分组模式
- 入口点聚类
- 配置边界
- 依赖隔离

**concept_signals**: 概念定义指示器
- 核心实体定义
- 重复术语
- 显式概念文档
- 实体关系模式

**rule_signals**: 业务规则指示器
- 验证逻辑
- 约束执行模式
- 接受门控
- Schema 验证要求

**demand_pattern_signals**: 需求模式指示器
- 变更分析模式
- 影响评估结构
- Diff 生成逻辑
- 版本比较机制

### 2.6 SEMANTIC 不负责

❌ 重新提取事实
❌ 重新扫描仓库
❌ 修改 FACT 输出
❌ 实现代码生成
❌ 执行重构

### 2.7 当前状态

✅ **已定义**:
- 5 个阶段契约（semantic_stage_contracts.md）
- 输入契约（semantic_input_contract.md）
- 输出契约（semantic_output_contract.md）
- 运行器设计（semantic_runner_design.md）
- 开发计划（semantic_dev_plan.md）

✅ **已创建**:
- Step1 设计文档（01_step1_signal_inference.md，359 行）
- Step3 设计文档（02_step3_scoring_design.md）
- Step4 设计文档（03_step4_review_and_evidence_design.md）
- Step5 设计文档（04_step5_finalize_design.md）

✅ **已创建**:
- Prompt 文件（prompts/semantic/*.prompt.md，8 个文件）
- Template 文件（templates/semantic/*.template.yaml，11 个文件）
- 代码骨架（src/semantic/*.py，14 个文件）
- 测试骨架（tests/semantic/，2 个测试文件）

❌ **未实现**:
- 实际的信号提取逻辑（extract_signals.py 只是脚手架）
- Signal 模型定义（models.py 缺少 Signal 相关模型）
- Step1-5 的完整实现

❌ **未创建**:
- 输出工作区（docs/semantic/ 目录不存在）

---

## 三、两阶段关系

### 3.1 数据流

```
Repository Code
    ↓
[FACT Layer]
    ↓
fact_canonical_sample.yaml (primary hard input)
fact_working_summary_sample.yaml (auxiliary soft input)
docs/fact/baseline/*.md (reference input, currently missing)
    ↓
[SEMANTIC Layer]
    ↓
signals.yaml → candidates.yaml → recommendations.yaml → review-decisions.yaml → final maps
    ↓
[DEMAND Layer] (not implemented)
```

### 3.2 职责边界

| 维度 | FACT | SEMANTIC |
|------|------|----------|
| **角色** | 提取可观察事实 | 推断语义模型 |
| **定位** | "是什么" (What IS) | "意味着什么" (What MEANS) |
| **输入** | 仓库代码 | FACT 输出 |
| **输出** | 事实 + 证据 | 模型 + 关系 |
| **解释性** | 低 | 高 |
| **人工角色** | 验证事实 | 审核模型 |
| **稳定性** | 高（基于证据） | 中（基于推断） |

### 3.3 分离原则

**FACT 必须**:
- 保持低解释性
- 提供证据引用
- 版本化输出
- 不泄漏语义判断

**SEMANTIC 必须**:
- 不重新提取事实
- 信任 canonical 为真实来源
- 使用 working summary 作为引导
- 不修改 FACT 输出

### 3.4 冲突解决

当 FACT 和 SEMANTIC 之间存在冲突时：
1. **Canonical wins**: 优先使用 canonical facts
2. **Evidence wins**: 优先使用有证据的声明
3. **Baseline wins**: 优先使用 baseline（架构师接受的）
4. **Explicit wins**: 优先使用显式声明

---

## 四、当前阻塞分析

### 4.1 阻塞点

**问题**: Step1 契约要求 `docs/fact/baseline/*.md` 作为主要输入，但这些文件不存在

**影响**: 无法按照当前契约实现 Step1

**根本原因**: FACT pipeline 尚未运行到 baseline 阶段，或 baseline 文件未生成

### 4.2 可用资源

✅ **已有**:
- `fact_canonical_sample.yaml` (11.8KB) - 包含所有必要的可观察事实
- `fact_working_summary_sample.yaml` (11.8KB) - 包含解释性内容
- 完整的 SEMANTIC 契约和设计文档
- Prompt 和 template 文件
- 代码骨架

❌ **缺失**:
- `docs/fact/baseline/*.md` 文件
- `docs/semantic/` 输出目录

### 4.3 解决方案

**选项 A: 运行 FACT pipeline 生成 baseline 文件**
- 优点：完全符合当前契约
- 缺点：需要先实现或运行完整的 FACT pipeline
- 时间：取决于 FACT pipeline 的实现状态

**选项 B: 修改 Step1 契约，使 baseline 文件可选** ⭐ 推荐
- 优点：可以立即开始实现，canonical YAML 包含所有必要信息
- 缺点：需要更新契约文档
- 时间：立即可行

**选项 C: 从 canonical YAML 生成示例 baseline 文件**
- 优点：满足当前契约，提供测试数据
- 缺点：生成的文件可能不完全符合 FACT baseline 的预期格式
- 时间：需要编写生成脚本

### 4.4 推荐路径

**推荐选项 B**：修改 Step1 契约，使 baseline 文件可选

**理由**:
1. `fact_canonical_sample.yaml` 已经包含所有必要信息
2. 可以立即开始 Step1 实现
3. 契约更新成本低
4. 不依赖 FACT pipeline 的运行状态

**具体步骤**:
1. 更新 `semantic_stage_contracts.md`，将 `docs/fact/baseline/*.md` 标记为可选
2. 更新 `01_step1_signal_inference.md`，明确 canonical YAML 是充分的
3. 创建 `docs/semantic/` 输出目录
4. 实现 `extract_signals.py`，直接从 canonical YAML 提取信号
5. 开始 Step1 实现

---

## 五、实现就绪度评估

### 5.1 FACT 阶段

| 维度 | 状态 | 评分 |
|------|------|------|
| 流程实现 | ✅ 已实现 | 100% |
| 契约定义 | ✅ 已定义 | 100% |
| 输出质量 | ✅ 高质量 | 100% |
| Baseline 文件 | ❌ 未生成 | 0% |
| **总体** | **部分就绪** | **75%** |

### 5.2 SEMANTIC 阶段

| 维度 | 状态 | 评分 |
|------|------|------|
| 契约定义 | ✅ 已定义 | 100% |
| 设计文档 | ✅ 已完成 | 100% |
| Prompt/Template | ✅ 已创建 | 100% |
| 代码骨架 | ✅ 已创建 | 100% |
| 逻辑实现 | ❌ 未实现 | 0% |
| 输出目录 | ❌ 未创建 | 0% |
| **总体** | **文档就绪，代码未就绪** | **67%** |

### 5.3 Step1 实现就绪度

| 检查项 | 状态 | 备注 |
|--------|------|------|
| FACT 输入存在 | ⚠️ 部分 | canonical YAML 存在，baseline MD 缺失 |
| 语义文档就绪 | ✅ 是 | 契约和设计文档完整 |
| Prompt 对齐 | ✅ 是 | Prompt 与契约匹配 |
| Template 对齐 | ✅ 是 | Template 与输出结构匹配 |
| 代码骨架存在 | ✅ 是 | extract_signals.py 存在 |
| 输出目录存在 | ❌ 否 | docs/semantic/ 不存在 |
| **可以开始实现** | ⚠️ **需调整** | 修改契约后可立即开始 |

---

## 六、下一步行动

### 6.1 立即行动（高优先级）

1. **创建输出目录**
   ```bash
   mkdir -p docs/semantic/
   ```

2. **更新 Step1 契约**
   - 文件：`semantic_stage_contracts.md`
   - 修改：将 `docs/fact/baseline/*.md` 标记为可选
   - 明确：`fact_canonical_sample.yaml` 是充分的主要输入

3. **更新 Step1 设计文档**
   - 文件：`01_step1_signal_inference.md`
   - 修改：明确 canonical YAML 提取路径
   - 添加：从 YAML 提取信号的具体指导

### 6.2 实现阶段（中优先级）

4. **实现 Signal 模型**
   - 文件：`src/semantic/models.py`
   - 添加：`Signal`, `DomainSignal`, `ConceptSignal`, `RuleSignal`, `DemandPatternSignal`

5. **实现信号提取逻辑**
   - 文件：`src/semantic/extract_signals.py`
   - 实现：从 canonical YAML 提取四类信号
   - 实现：置信度评级
   - 实现：证据引用保留

6. **添加 Step1 测试**
   - 文件：`tests/semantic/test_extract_signals.py`
   - 测试：信号提取逻辑
   - 测试：输出格式验证

### 6.3 验证阶段（低优先级）

7. **运行 Step1**
   ```bash
   python -m semantic.run next
   ```

8. **验证输出**
   - 检查：`docs/semantic/signals.yaml` 生成
   - 检查：`docs/semantic/signals.md` 生成
   - 验证：输出结构符合契约

9. **迭代改进**
   - 根据输出质量调整提取逻辑
   - 优化置信度评级算法
   - 改进信号分类准确性

---

## 七、总结

### 7.1 关键发现

1. **职责清晰**: FACT 提供"是什么"，SEMANTIC 提供"意味着什么"
2. **分离良好**: 两阶段职责边界明确，无重叠
3. **文档完整**: 契约、设计、prompt、template 都已就绪
4. **阻塞可解**: baseline 文件缺失，但可通过使用 canonical YAML 绕过
5. **实现就绪**: 调整契约后可立即开始 Step1 实现

### 7.2 推荐路径

**最佳路径**: 修改 Step1 契约 → 创建输出目录 → 实现信号提取 → 开始 Step1

**时间估算**:
- 契约更新：30 分钟
- 目录创建：1 分钟
- Signal 模型：1 小时
- 提取逻辑：3-4 小时
- 测试编写：1-2 小时
- **总计**: 约 6-8 小时可完成 Step1 实现

### 7.3 风险评估

**低风险**:
- 文档完整，契约清晰
- canonical YAML 质量高
- 代码骨架已存在

**中风险**:
- 信号提取逻辑的准确性需要迭代
- 置信度评级算法需要调优

**无高风险项**

---

**分析完成日期**: 2026-03-16
**分析者**: Claude Opus 4.6