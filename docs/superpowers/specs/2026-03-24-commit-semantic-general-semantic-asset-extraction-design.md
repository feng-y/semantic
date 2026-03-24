# Commit-Semantic Commit-First Semantic Asset Extraction Spec

**Status:** Draft
**Scope:** General reusable capability
**Primary Objective:** 从 commit 历史中提取可被下游消费的领域知识
**Design Stance:** Commit-first, LLM-first semantic synthesis, evidence-backed, lightly adapted by repo-local understanding documents

---

## 1. Problem

当前 `commit-semantic` 容易退化成“提交分类器”，而不是“领域知识提取器”。常见失败模式包括：

- 把 repo-local capability、工程活动类型、fallback bucket 混在同一层 taxonomy
- 过度依赖路径、关键词、summary 规则匹配
- 用单条 commit 的表面词汇直接决定 domain
- 把 mixed commit 强行压成单标签
- 让 `Modified N file(s)`、`Changes in:` 这类低信息摘要主导结果
- 把上游依赖提及误判成主语义归属

这类输出可以用于粗粒度 summary，但不足以支撑：

- 领域知识补全
- semantic / demand 下游消费
- harness engineering
- 长期演化分析

问题的本质不是“分类不够精细”，而是：

> 系统还没有稳定地从 commit 视角提取领域知识。

---

## 2. System Definition

`commit-semantic` 是一个 **commit-first semantic asset extraction capability**。

它的核心任务不是给 commit 找桶，而是：

> 以 commit 及其演化序列为观察单元，提取 capability、domain、concept、rule 等语义资产；repo 文档只作为辅助先验，用来帮助理解 commit，而不是替代 commit 成为主语义来源。

它不是：

- repository-specific taxonomy generator
- work-type classifier
- zero-config black box
- heavy per-repo ontology project

---

## 3. Goals

### 3.1 Primary Goal
从 commit 历史中提取 **business capability map**。

### 3.2 Secondary Goal
围绕 capability 提取混合语义资产：

- domains
- concepts
- rules

### 3.3 Tertiary Goal
基于已验证资产构建派生视图：

- hotspots
- demand-like signals
- evolution summaries

### 3.4 Operational Goal
作为一个可迭代、可跨 repo 复用的通用能力存在，只需要轻量 repo 适配。

---

## 4. Non-Goals

### 4.1 Not a Work-Type Taxonomy
以下内容不是主语义输出：

- testing
- documentation
- refactoring
- cleanup
- CI quality
- release

它们只能作为 secondary tags。

### 4.2 Not a Hardcoded Current-Repo Model
`fact`、`semantic`、`demand`、`commit-extract`、`commit-semantic` 这类名字只属于当前 repo 的 local context，不是通用 taxonomy 本体。

### 4.3 Not Rule-First Classification
系统不应以规则匹配作为主策略，尤其不应靠 path/keyword/summary rule 直接决定最终领域知识。

### 4.4 Not Repo-First Interpretation
repo docs 和 architecture 信息很重要，但它们是 prior，不是主语义来源。

---

## 5. Current Repo’s Role

当前 repo 是 **calibration case**，不是通用模型。

它的价值在于暴露了真实失败模式：

- mixed commits
- owner / consumer ambiguity
- docs-as-prior behavior
- low-signal summary failure
- catch-all bucket failure
- naming drift

因此它适合作为第一批校准样本，但不应被硬编码进系统的通用 taxonomy。

---

## 6. Core Abstraction

系统有三层：

### 6.1 Commit Signal Layer
把 commit / commit unit 当成最小观察单元，提取 commit-level semantic signals。

### 6.2 Semantic Synthesis Layer
跨 commit 聚合这些 signals，形成 capability / domain / concept / rule 资产。

### 6.3 Derived View Layer
基于已验证资产导出热点、需求信号和演化摘要。

---

## 7. Input Model

### 7.1 Required Inputs
- commit history artifacts
- commit-extract outputs
- commit summaries / sections / units
- file path evidence

### 7.2 Optional but Preferred Inputs
repo-local understanding docs，例如：

- architecture docs
- specs / design docs
- ADRs
- README capability descriptions
- module overviews
- AI-generated repo summaries

在 V1 中，hints synthesis 应优先选择与当前实现契约更接近、更新更近、且能被 commit/code evidence 交叉验证的文档；明显过时或与当前输出契约冲突的 docs 只能作为弱 prior，而不能主导 repo hints。若 docs 与当前 commit/code evidence 直接冲突，commit/code evidence 优先，docs 只保留为解释性背景，不进入高置信 hint。
### 7.3 Input Principle
所有 docs 都是 priors。系统必须假设它们可能：

- 不完整
- 过时
- 互相冲突
- 来自 human / AI / mixed

它们只用于帮助 LLM 更好理解 commit，不直接替代 commit 证据。

---

## 8. Upstream Dependency: Commit-Extract

`commit-semantic` 不是直接从原始 git diff 提取领域知识，它依赖 `commit-extract` 提供上游结构化 commit 表达。当前阶段，`commit-extract` 的本质是一个 **prompt-driven structured commit extractor**，因此它对 `commit-semantic` 的约束主要不是系统形态问题，而是 **prompt fidelity** 问题。

### 8.1 Current Support Level
当前 `commit-extract` 已经能提供一版可用的语义输入，至少包括：

- commit-level structured records (`sha`, `author`, `date`)
- `sections` / `items` 结构
- `theme`, `importance`, `summary`, `op`
- `is_mixed`
- `is_large_aggregate`
- `rules_invariants`

这些信息已经足够支撑 `commit-semantic` 在 V1 启动 commit-first、capability-first 的语义提取。

### 8.2 Current Limitation Type
当前 `commit-extract` 的主要限制不是缺少另一套复杂架构，而是它作为 prompt 产出层的 **语义保真度还不够高**。主要表现包括：

- 大量 `other` / `Modified N file(s)` 这类低信息 item
- `rules_invariants` 通道存在，但当前信息密度偏低
- 缺少稳定的 file/hunk-level evidence anchors
- `sections` 更偏 summary-friendly，而不是 semantic-signal-friendly

这意味着 `commit-semantic` 虽然可以开始做 capability 提取，但 concept / rule / high-confidence domain synthesis 的质量会受到上游 prompt 产出粒度的限制。

### 8.3 Design Implication
因此本设计采用以下约束：

- V1 允许在当前 `commit-extract` 输出之上启动 capability-first semantic extraction
- `commit-extract` 的后续提升主要通过 prompt 迭代来完成，而不是预设一个更重的上游重构前提
- `commit-semantic` 在设计和评估时必须把 `commit-extract` 视为持续可优化的 upstream prompt layer，而不是透明输入层

### 8.4 Guiding Principle
`commit-extract` 决定 semantic evidence 的质量上限，`commit-semantic` 决定 semantic synthesis 的质量上限。前者主要通过 prompt fidelity 提升单 commit 表达质量，后者主要通过 LLM synthesis 提升跨 commit 领域提取能力。两者必须被视为同一条语义提取链的上下游。

---

## 9. Docs as Domain Knowledge Expression

Docs are not operation manuals — they are **expressions of domain abstraction and knowledge**.

This distinction is fundamental:

- A doc does not describe "what files changed"
- A doc expresses "how this repo abstracts its problem space"
- A doc names the core entities, boundaries, constraints, and invariants
- A doc encodes the vocabulary the team uses to reason about the system

Therefore, reading docs is not merely extracting capability hints — it is **understanding the domain's abstraction layer before parsing commit semantics**.

### 9.1 Domain Abstraction Components

When reading docs, the system should extract:

**Vocabulary table** — how the repo names things:
- Core domain terms and their meanings
- Distinction between core entities and implementation details
- Aliases and naming conventions

**Architecture layers** — the structure of the system:
- Major subsystems and their boundaries
- Ownership and responsibility zones
- Key interfaces between components

**Key concepts** — the domain's mental model:
- What are the core abstractions?
- What invariants hold across the system?
- What are the operational constraints?

**Boundary rules** — where the system ends:
- What is internal vs external?
- What changes require coordination?
- What are the failure isolation boundaries?

### 9.2 Why This Matters for Extract

Without domain understanding, a commit like "update model setting" has ambiguous semantics — it could be config-only noise or an inference path capability change.

With domain understanding, the extractor can ground the question: **"In this repo's domain, what does changing this setting mean at the capability level?"** — and get a grounded answer rather than guessing from keywords or file paths.

### 9.3 The Corrected Claim

Evidence from A/B testing (DaVinci commits) suggests:

> **Minimal domain hints, distilled from docs, improve extraction quality on ambiguity-sensitive commits by helping the LLM recover the dominant semantic center and latent boundary/invariant semantics — when commit/code evidence overrides the hints.**

This is **not** the same as "docs improve extraction in general." The distinction matters:

- Docs help when **commit meaning is underdetermined** by the record alone
- Docs can **hurt** when the prior steers instead of grounds (see 9.4)
- The measure of success is **output quality**, not "better questions asked"
- Output quality is measurable: semantic center accuracy, invariant recovery rate, fragmentation reduction, evidence grounding ratio

### 9.4 Failure Modes (Hard Constraints)

Domain prior can actively degrade extraction. These are not theoretical — they are observed failure patterns:

**Outdated docs** — docs describe old architecture; prior imports obsolete vocabulary and misreads current commits. Counter: commit/code evidence must override prior when they conflict.

**Idealized docs** — docs describe intended design, not actual behavior; extraction becomes normative ("what should have happened") rather than empirical ("what was done"). Counter: extraction is always from commit/code evidence, never from doc inference.

**Anchoring bias** — prior suggests "this repo is about X," model forces commits into that frame and misses novel or cross-cutting changes. Counter: secondary signals and mixed flags must be preserved even when dominant frame is clear.

**Overcompression** — prior makes the model collapse a mixed commit into one narrative and drops important secondary semantics. Evidence: A/B test showed 14→7 items on a mixed metrics migration; the cleaner storyline could mean better abstraction OR lost secondary signal. Counter: low-confidence secondary signals must be preserved, not suppressed for narrative elegance.

**Hallucinated invariants** — model emits doc-shaped rules that sound correct but lack commit-level evidence. Counter: all rules must have explicit evidence_refs; doc-shaped without commit evidence = rejected.

**Context dilution** — raw docs consume token budget and reduce sensitivity to commit-specific details. Counter: only synthesized minimal hints enter the analysis context; raw docs are only consulted on remaining ambiguity, not the default input.

### 9.5 The Inference Chain

```
Read docs → Build domain abstraction → Use abstraction as prior for extract
```

This is why Section 8 says `commit-extract` is an upstream prompt layer — but more precisely, it should be: **extract uses domain abstraction as semantic prior, not just file/keyword matching**.

---

## 10. Repo Hints Contract

repo-local docs 应被合成为最小 hint layer。

### 9.1 V1 Minimal Hints
V1 只抽四类：

1. `local_capabilities`
2. `aliases`
3. `ownership_hints`
4. `seed_concepts`

### 9.2 Their Role
这些 hints 的作用是：

- 给 commit 语义理解提供 prior
- 帮助 LLM resolve naming / ownership ambiguity
- 帮助 concept grounding

它们不是 deterministic rule set，更不是最终 semantic asset。

`repo-hints.json` 是从 docs 中提炼出的 prior 输入层；`repo-context.json` 是当前运行基于 hints 与 commit/code evidence 形成的 grounding view。前者是输入，后者是解释性上下文，两者不应被视为同一个 artifact。

### 9.3 Design Constraint
在 V1 中，repo hints 只允许作为 **语义先验** 参与 commit 理解，不允许退化成以路径匹配、关键词匹配为主的硬编码 routing 规则体系。它们的主要作用是提升 LLM 对 commit 的解释质量，而不是提前替代 LLM 做语义判断。

进入 `commit-semantic` 主分析阶段时，应优先把 repo understanding docs 压缩成 synthesized repo hints 再进入 LLM context；只有在 naming、ownership、concept grounding 仍然存在歧义时，才回看原始 docs 片段作为补充证据。也就是说，原始 docs 不是每轮分析的默认主上下文，结构化 hints 才是。

---

## 10. Output Model

顶层输出：

```yaml
repo_context:
semantic_assets:
evidence:
derived_views:
```

### 10.1 `repo_context`
repo-local grounding layer，用于解释当前 repo 的局部能力结构。它提供 repo-local prior 与局部解释，但**不能直接等价替代最终 semantic asset**；最终资产必须经过 commit-level signals 与 cross-commit synthesis 验证。

### 10.2 `semantic_assets`
主语义输出层：

- `capabilities`
- `domains`
- `concepts`
- `rules`

这是**完整模型**中的逻辑层，不等于 V1 必须落地为独立文件。V1 只正式交付 capability-first 相关 artifacts；`semantic_assets`、`evidence`、`derived_views` 在 V1 中更多是结构性目标，而不是全部独立导出的稳定产物。

### 10.3 `evidence`
所有正式资产的证据层。

### 10.4 `derived_views`
基于已验证资产生成的消费视图。

---

## 11. Repo Context

`repo_context` 是 repo-local grounding layer，不是最终通用语义模型。

示例：

```yaml
repo_context:
  local_capabilities: [...]
  ownership_hints: [...]
  aliases: [...]
  seed_concepts: [...]
  confidence: high|medium|low
```

它的作用不是直接分类 commit，而是帮助 LLM 在分析 commit 时理解：

- repo 自己如何描述自己
- 路径和能力之间的大致关系
- 本地词汇和别名如何归一

---

## 12. Semantic Assets

`semantic_assets` 是主输出层，设计上采用 **B + D**：

- capability 是骨架
- domain / concept / rule 是挂靠资产

但这些资产都必须来自 **commit-first semantic synthesis**，而不是静态 repo taxonomy 投影。

---

## 13. Capability

Capability 是主骨架。

定义：

> Capability 是一类在多个 commits 中被反复表达、修改、强化、修正或扩展的功能性语义单元。

Capability 不等于：

- 单个目录名
- 单个模块名
- 工程活动类型
- 临时实现措辞

### 13.1 Capability V1 Schema

```yaml
capability:
  capability_id:
  canonical_name:
  observed_names: []
  description:
  evidence_refs: []
  repo_context_refs: []
  confidence: high|medium|low
  status: stable|candidate|provisional
  naming_source: repo-hint|observed-pattern|synthesized
```

`capability_id` 是稳定身份，不应与 `canonical_name` 强绑定。命名变化、observed name 漂移、或后续 rename 不应直接改变 capability identity。

### 13.2 Why Capability-First
因为 capability 是最适合从 commit 序列中稳定归纳出来的骨架层，也是下游最容易消费的主层。

---

## 14. Domain, Concept, Rule

### Domain
Domain 是多个 capability 聚合后形成的问题空间，不应主要由单条 commit 直接决定。

### Concept
Concept 是 commit 历史里被反复操作、引用、修正的对象、工件或语义实体。

### Rule
Rule 是在 commit 演化中反复显现的约束、判断逻辑、不变量或治理条件。Rule 必须有规范性证据支撑。

---

## 15. Evidence Model

正式 semantic asset 必须 evidence-backed。

Evidence kinds may include:

- `commit-summary`
- `file-path-set`
- `rules-invariant`
- `aggregated-pattern`
- `cross-commit-cluster`
- `doc-hint`

核心原则：

> 没有 evidence refs 的资产，不能进入高置信正式层。

对于 `medium` 及以上置信度资产，至少应有跨 commit 或跨证据类型的支撑，而不是单条低信息摘要单独支撑。

---

## 16. Naming Strategy

每个 capability 保留两层命名：

- `canonical_name`
- `observed_names`

### Canonical Name
提供给下游稳定消费。

### Observed Names
保留 commit summaries、docs、artifacts 中真实出现过的名字。

### Arbitration Rule
默认采用：

> **结构上双轨，默认仲裁偏 repo hints，但 commit history 拥有最终纠偏权。**

也就是：

- docs/hints 提供优先 canonical naming 候选
- commit history 提供 observed naming 和持续验证
- docs 弱/旧/冲突时，可退到 observed pattern
- 两者都不稳时，生成 provisional canonical name
- 若长期偏离，标记 naming drift

---

## 17. Core Pipeline

新 pipeline 采用 **LLM-first semantic synthesis + deterministic validation**。

### Stage 0 — Context Preparation
准备：
- commit units
- file paths
- repo docs priors
- synthesized repo hints

输出：供 LLM 分析的 context package。

### Stage 1 — Commit-Level Semantic Signal Extraction
以 commit / unit 为观察单元，用 LLM 提取：

- capability signals
- concept signals
- rule signals
- domain hints

注意：这一阶段提的是 signals，不是最终资产。

V1 虽然只正式输出 capability 层，但内部应有明确的 commit-level signal representation。最小应至少区分：

- `kind` (`capability` / `concept` / `rule` / `domain_hint`)
- `name`
- `description`
- `source_commit`
- `evidence_refs`
- `confidence`
- `flags` (`mixed`, `shared_support`, `low_signal` 等)
- `related_capability_names`（当单个 commit signal 明显跨多个 capability 时）

其中 `domain_hint` 只表示 commit-level 的弱领域线索，不等于正式 domain 资产；正式 domain 层只应在 capability aggregation 之后形成。

这层 signal 是后续跨 commit synthesis 的直接输入，不应在实现中隐式存在。

### Stage 2 — Cross-Commit Semantic Synthesis
跨 commit 聚合 signals，用 LLM 归纳：

- capability candidates
- concept candidates
- rule candidates
- domain candidates

这是主工作阶段。

### Stage 3 — Deterministic Validation
代码负责：

- schema validation
- evidence binding
- 去重
- 基础一致性检查
- confidence normalization

### Stage 4 — LLM Refine
如果 validation 暴露出：

- 重复
- 冲突
- 命名漂移
- 证据不足
- 边界模糊

则进入 targeted refine，由 LLM 做二次收敛。

### Stage 5 — Export
在 validated assets 之上导出：

- `semantic_assets`
- `derived_views`
- `summary`

---

## 18. Role Split: LLM vs Deterministic Code

### LLM Main Responsibilities
- capability extraction
- domain synthesis
- concept extraction
- rule inference
- naming synthesis
- merge / split judgment
- ambiguity handling

### Deterministic Code Responsibilities
- input preparation
- artifact lifecycle
- evidence linkage
- schema validation
- confidence normalization
- export / summary
- state management

原则：

> 代码负责结构与护栏，LLM 负责语义理解与归纳。

---

## 19. Confidence Model

### 19.1 Repo Context Confidence
由以下因素决定：
- docs 质量
- path evidence
- alias consistency
- local capability clarity

### 19.2 Semantic Asset Confidence
由以下因素决定：
- evidence 数量
- 跨 commit 重复性
- 与 repo context 的一致性
- 低信息摘要占比
- LLM synthesis 收敛程度

V1 最低操作化要求：
- `high`：需要跨 commit 且非低信息摘要主导的证据支撑
- `medium`：至少需要多条证据，或跨 commit / 跨证据类型支撑之一
- `low`：允许单条弱证据或仍存在明显歧义的候选

建议标签：
- `high`
- `medium`
- `low`

---

## 20. Mixed and Low-Signal Handling

### Mixed Changes
必须显式支持：
- secondary capability refs
- mixed flags
- shared-support flags

### Low-Signal Units
以下内容视为 low-signal：

- `Modified N file(s)`
- `Changes in:`
- review-feedback summaries
- vague quality-fix summaries

这些可以作为弱证据，但不能主导 semantic synthesis。

---

## 21. Secondary Tags / Facets

以下只作为 secondary tags，不进入主 semantic taxonomy：

- feature
- bugfix
- test
- docs
- refactor
- cleanup
- ci
- release
- marketplace
- migration

---

## 22. V1 Boundary

V1 应保持严格收敛，目标是验证 **commit-first + capability-first + LLM-first semantic synthesis** 这条主链是否成立，而不是一次性完成完整 mixed semantic asset 体系。

### 22.1 V1 Includes
- `repo-context.json`
- `repo-hints.json`
- `capabilities-candidates.jsonl`
- `capabilities.jsonl`
- `summary.json`

其中 `summary.json` 在 V1 中的定位是 **capability-first extraction 的健康检查与消费概览**，不是最终领域知识资产本体。V1 不要求单独产出独立 `evidence` 文件；`evidence_refs` 默认解析到 `capabilities-candidates.jsonl` / `capabilities.jsonl` 中随记录携带的证据引用。

它至少应回答：

- 抽出了多少 capability candidates
- 最终稳定 capability 有多少
- mixed / low-signal 占比如何
- evidence coverage 是否足够
- naming drift 是否明显

### 22.2 V1 Does Not Yet Require Full Formalization Of
- domains
- concepts
- rules
- hotspots
- demand signals

这些可以在设计上存在，但不要求在 V1 形成正式稳定输出层。

### 22.3 V1 Success Condition
V1 的成功标准不是“已经得到完整领域知识图谱”，而是以下几点：

- 五个 V1 artifacts 都存在且非空：`repo-context.json`、`repo-hints.json`、`capabilities-candidates.jsonl`、`capabilities.jsonl`、`summary.json`
- `capabilities-candidates.jsonl` 非空
- `capabilities.jsonl` 非空
- stable capability count > 0
- 每个 stable capability 都有 `capability_id`
- 每个 stable capability 都有 `evidence_refs`
- `summary.json` 至少包含 candidate count、stable count、mixed ratio、low-signal ratio、evidence coverage、naming drift count
- `evidence coverage` > 0

### 22.4 Reason
第一件必须稳定下来的事情是 **capability-first semantic backbone**。如果这一层不稳，后续 domain / concept / rule / derived views 都只会放大不稳定性。

## 23. Migration Strategy

Legacy flat labels such as `project-infrastructure` and `semantic-pipeline` should be phased out from the primary semantic layer.

本设计默认 `commit-semantic` 允许 **breaking redesign**：当前能力尚未正式上线，因此 V1 不以长期兼容旧 domain-first artifacts 为前提。旧输出（如 `domains-aggregated.jsonl`、`canonical-demands.jsonl`）可以被直接移除、重命名或重构，只需同步更新当前 repo 内的测试与消费者引用。

迁移方向：
- 从 flat labels
- 到 commit-first、capability-first、evidence-backed semantic assets

---

## 24. Success Criteria

### Quality Success
- catch-all buckets 不再主导结果
- mixed commits 不再被错误单标签化
- low-signal summaries 不再控制主语义
- owner / consumer confusion 明显下降
- medium/high-confidence assets 都能回溯到 evidence

### Product Success
- 引擎可跨 repo 使用
- 新 repo 只需轻量 understanding docs 即可接入
- 当前 repo 保持 calibration case 身份
- 下游可稳定消费 capability-first outputs

### Iteration Success
- repo priors 可持续更新
- emergent capabilities 可被发现
- naming drift 可被显式检测
- 后续可自然扩展到完整 mixed semantic assets

---

## 25. Open Questions

1. domain 是否必须总是由 capability aggregation 产生，还是允许直接从 commit synthesis 中生成高置信 domain？
2. `shared-runtime` 是否应始终停留在 repo context 层？
3. docs prior 与 commit evidence 冲突时，如何量化仲裁？
4. concept / rule 升格到 medium confidence 的最小 evidence threshold 是什么？
5. demand-like signals 是否应长期保持 derived view，而不是 first-class semantic asset？
6. 弱或冲突的 repo docs 应如何在跨 repo 场景中规范化？

---

## 26. Final Summary

This spec defines `commit-semantic` as:

> 一个以 commit 为观察单元、以跨 commit 归纳为核心、以 repo docs 为辅助先验、以 LLM 分析为主引擎、以 deterministic validation 为护栏的通用领域知识提取系统。

当前 repo 不是通用 taxonomy。
它只是第一个 calibration example。

系统的目的不是把 commit 塞进粗粒度桶里。

它的目的是把 commit 历史转成可复用的 semantic knowledge layer。
