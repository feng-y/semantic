# IBS 需求与约束设计文档

## 1. 目标

本文档定义 Semantic Harness 后续要实现的 **IBS（Intent / Behavior / Structure）输出体系**，作为实现、评审、测试、验收的正式需求基线。

IBS 的目标不是只生成少量语义摘要文件，而是生成一套可用于：

- 后续需求分析
- 变更影响分析
- 架构设计与方案比选
- Agent 任务拆解
- baseline 沉淀
- 长期演进中的语义一致性维护

的 **分层输出包**。

---

## 2. 当前问题

当前系统已经能产出 working artifacts：

- repo-facts
- repo-understanding
- knowledge-confidence
- domain-candidates
- review-summary

但这些仍然主要是 **工作态语义产物**，不是最适合后续需求分析的 **最终语义输出模型**。

现状问题：

1. 最终输出还没有明确围绕 IBS 三层组织。
2. baseline 产物过少，无法充分支撑后续需求分析。
3. Intent 层最弱，缺少 goals / constraints / non-goals / success-criteria。
4. Behavior / Structure 虽有基础，但没有收敛成正式分析包。
5. 尚未形成“Core Baseline + Analysis Pack”的正式输出契约。

---

## 3. 总体目标

在现有 discover → review → refine → baseline 流水线基础上，新增并固化 **IBS 输出体系**：

- I = Intent
- B = Behavior
- S = Structure

使系统最终能够输出：

- 可审阅
- 可追踪
- 可验证
- 可供需求分析直接使用

的语义基线与分析包。

---

## 4. 输出模型

### 4.1 双层输出

IBS 最终输出分两层：

#### Level 1 — Core Baseline
用于快速理解系统、对外交付、轻量知识沉淀。

#### Level 2 — Analysis Pack
用于需求分析、架构设计、变更规划、Agent 任务分解。

---

### 4.2 Intent（意图层）

回答：

- 系统为什么存在
- 核心目标是什么
- 成功标准是什么
- 约束是什么
- 明确不做什么

#### Core Baseline
- `purpose.md`

#### Analysis Pack
- `goals.md`
- `constraints.md`
- `non-goals.md`
- `success-criteria.md`

---

### 4.3 Behavior（行为层）

回答：

- 系统实际做什么
- 关键流程是什么
- 输入输出如何流动
- 状态如何变化
- 异常如何处理

#### Core Baseline
- `pipelines.md`

#### Analysis Pack
- `workflows.md`
- `inputs-outputs.md`
- `state-transitions.md`
- `failure-handling.md`

---

### 4.4 Structure（结构层）

回答：

- 系统由什么组成
- 核心概念与领域是什么
- 模块边界是什么
- 数据与接口如何组织

#### Core Baseline
- `domains.md`
- `concepts.md`

#### Analysis Pack
- `components.md`
- `boundaries.md`
- `data-models.md`
- `interfaces.md`

---

## 5. 推荐产出目录

```text
docs/semantic/baseline/

  core/
    purpose.md
    pipelines.md
    domains.md
    concepts.md

  intent/
    goals.md
    constraints.md
    non-goals.md
    success-criteria.md

  behavior/
    workflows.md
    inputs-outputs.md
    state-transitions.md
    failure-handling.md

  structure/
    components.md
    boundaries.md
    data-models.md
    interfaces.md
```

---

## 6. 核心约束

1. 不推翻现有 runtime，只在 baseline synthesis、schema、template、validation 上扩展。
2. 先补模型，再补实现。
3. Core Baseline 与 Analysis Pack 必须显式分层。
4. 每个文件必须最终拥有：
   - schema
   - template
   - validator
5. 不改变现有 public skill set。
6. 不迁移 `docs/semantic/` 路径。
7. 不引入新的外部依赖。
