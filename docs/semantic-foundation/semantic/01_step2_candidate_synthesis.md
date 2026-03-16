# semantic_asset_build · 第二步（候选合成）实施手册

---

**⚠️ TRANSITIONAL DOCUMENT NOTICE**

**Status**: Transitional / Chinese Language / Legacy Naming

**Current Canonical Documents** (English):
- `semantic_stage_contracts.md` - Canonical stage definitions (includes Step2)
- `semantic_output_contract.md` - Canonical output specifications

**Current Canonical Layer Name**: `semantic` (not `semantic_asset_build`)

**Current Canonical Output Names**: `candidates.yaml` (not `step2_candidates.yaml`)

**For Implementation**: Use `semantic_stage_contracts.md` as the canonical reference for Step2 (Candidate Synthesis).

This document is in Chinese and uses legacy naming. It is kept for historical context only.

---

## 目标

第二步的目标不是“再提取一次信息”，而是：

> 把第一步产出的 `signals.yaml` 收束成可评审、可打分、可固化的 `candidates.yaml`。

这一步的本质是 **candidate synthesis**，不是 extraction。

---

## 先说清楚：哪些动作是规则，哪些动作是模型

第二步采用：

```text
规则预处理
→ 模型归并与定名
→ 规则校验与落盘
```

### 规则 / 程序负责
- 读取 `signals.yaml`
- 基础去重与格式规范化
- 保证只能输出四类 candidate
- 校验字段完整性
- 校验 ID 唯一性
- 写 `candidates.yaml`
- 渲染 `candidates.md`

### 模型负责
- 判断哪些 signal 应归成同一个 candidate
- 给 candidate 起稳定名字
- 写 `summary`
- 写 `boundary`
- 决定某个 candidate 属于 domain / concept / rule / demand_model 哪一类
- 控制 candidate 粒度，不要太碎也不要太大

### 人工在这一步不介入
第二步只做候选合成，不做最终收口。

---

# 一、第二步解决什么问题

## 1. 名称漂移
同一个对象会有多种表述，必须合并成同一个 candidate。

## 2. 粒度失衡
signal 可能很大，也可能很小，必须统一到“可评审粒度”。

## 3. 重复与遮蔽
有些 signal 只是另一个对象的局部说明，不该单独保留。

## 4. 为第三步打分推荐准备输入
第三步需要的是 candidate，不是 signal。

---

# 二、输入与输出

## 输入
- `docs/semantic-foundation/semantic-asset-build/signals.yaml`

## 输出

### canonical output
- `docs/semantic-foundation/semantic-asset-build/candidates.yaml`

### human-readable view
- `docs/semantic-foundation/semantic-asset-build/candidates.md`

---

# 三、第二步最终流程

```text
2.1 规则预处理
2.2 模型归并成候选簇
2.3 模型定名与边界收束
2.4 规则校验与落盘
```

---

# 四、2.1 规则预处理

## 目标
先把信号输入整理到适合模型归并的状态。

## 类型
**纯规则 / 程序动作**

## 输入
- `signals.yaml`

## 输出
- 内存态 `normalized_signals`
- 可选调试文件：`normalized-signals.yaml`

## 做什么
1. 读取 `signals.yaml`
2. 校验顶层结构是否包含：
   - `domain_signals`
   - `concept_signals`
   - `rule_signals`
   - `demand_pattern_signals`
3. 给每条 signal 补齐默认字段：
   - `notes: []`
4. 标准化：
   - `name`
   - `evidence_refs`
   - `source cluster / source refs`
5. 做基础去重：
   - 同 ID 直接报错
   - 同 name + 同 evidence 归并
6. 输出 normalized 信号列表

## 为什么程序做
这一步没有语义判断，只有结构和格式处理。

## 错误处理
### 不可恢复错误
- `signals.yaml` 缺字段
- 顶层 key 缺失
- signal 没有 `id`
- signal 没有 `evidence_refs`

输出：
```yaml
error:
  stage: candidate_preprocess
  type: schema_error
  detail: ...
```

---

# 五、2.2 模型归并成候选簇

## 目标
把多个相近 signal 归成一个 candidate cluster。

## 类型
**模型推理主导**

## 输入
- normalized signals
- `prompts/candidate_synthesis.prompt.md`

## 输出
- `candidate-clusters.yaml`

## 模型要完成的动作
1. 判断哪些 signal 说的是同一个对象
2. 将相近 signal 归到同一个 cluster
3. 不要把明显不同粒度的对象强行合并
4. 不要把局部细节随意升格成独立 cluster

## 产出结构

```yaml
domain_candidate_clusters:
  - cluster_id: domain_cluster_001
    source_signal_ids:
      - domain_signal_001
      - domain_signal_004
    provisional_name: Semantic Artifact Construction
    evidence_refs:
      - docs/semantic/discovery/repo-understanding.v3.md
    notes:
      - Stable business domain around semantic artifact generation

concept_candidate_clusters: []
rule_candidate_clusters: []
demand_model_candidate_clusters: []
```

## 规则护栏
程序在模型输出后只检查：
- cluster_id 唯一
- source_signal_ids 非空
- evidence_refs 非空
- 只能输出四类 cluster
- 每个 cluster 必须有 provisional_name

## 失败处理
### 可恢复
- 某些 signal 未被吸纳进 cluster  
处理：保留单独 cluster，标记 weak_cluster

### 不可恢复
- 大量 signal 一对一原样复制  
处理：判定 synthesis 失败，因为没有发生真正归并

---

# 六、2.3 模型定名与边界收束

## 目标
把 cluster 变成真正 candidate。

## 类型
**模型推理主导**

## 输入
- `candidate-clusters.yaml`

## 输出
- candidate 草稿（进入 `candidates.yaml` 前）

## 模型要完成的动作
对每个 cluster，输出：

### 通用字段
- `id`
- `type`
- `name`
- `summary`
- `boundary`
- `source_signal_ids`
- `evidence_refs`
- `notes`

### 不同类型附加字段
#### domain
- `role`
- `not_responsible_for`

#### concept
- `domain`
- `why_it_matters`

#### rule
- `statement`
- `rule_type`
- `consequence_hint`

#### demand_model
- `typical_scenario`
- `handling_hint`

## 这里模型真正要做的是什么
### 1. 稳定命名
名字不能只是复制 signal wording，而要是一个可复用、可评审的正式名字。

### 2. 边界收束
candidate 必须说明它是什么，也说明它不是什么。

### 3. 粒度控制
一个 candidate 必须能被单独引用：
- 太小就并入上位对象
- 太大就拆出更稳定边界

## 推荐的最小结构

```yaml
domains:
  - id: domain_candidate_001
    name: Semantic Artifact Construction
    summary: Core business domain responsible for generating and evolving semantic artifacts from fact inputs.
    boundary: Focuses on asset production logic, not runtime validation gating or version storage policy.
    role: Main business domain for semantic asset generation.
    not_responsible_for:
      - Runtime validation enforcement
      - Accepted baseline immutability management
    source_signal_ids:
      - domain_signal_001
      - domain_signal_004
    evidence_refs:
      - docs/semantic/discovery/repo-understanding.v3.md
    notes: []
```

## 为什么必须模型做
这一步本质是“建模”，不是规则映射。

## 失败处理
### 可恢复
- 某些 candidate summary 太弱  
处理：允许标记 weak_summary，进入第三步时再由 AI 打分阶段压低

### 不可恢复
- 无法给出 boundary
- 无法稳定命名
- 大量 candidate 只是在重复 signal wording

处理：终止，并输出：
```yaml
error:
  stage: candidate_synthesis
  type: weak_semantic_consolidation
  detail: ...
```

---

# 七、2.4 规则校验与落盘

## 目标
把模型输出的 candidate 草稿变成 agent-friendly canonical output。

## 类型
**纯规则 / 程序动作**

## 输入
- candidate draft（模型输出）

## 输出
- `candidates.yaml`
- `candidates.md`

## 程序必须校验的东西

### 通用必填字段
- `id`
- `type`
- `name`
- `summary`
- `boundary`
- `source_signal_ids`
- `evidence_refs`

### 类型特定字段
#### concept
- `domain`
- `why_it_matters`

#### rule
- `statement`
- `rule_type`
- `consequence_hint`

#### demand_model
- `typical_scenario`
- `handling_hint`

## 还要做什么
1. 校验 ID 唯一
2. 校验引用 signal id 都存在
3. 校验同名冲突
4. 写 canonical YAML
5. 从 canonical YAML 渲染 Markdown 视图

## 错误处理

### 可自动修复
- `notes` 缺失 → 自动补 `[]`
- 单个字段缺失但可推空默认值 → 填默认值并 warning

### 必须失败
- 无 `id`
- 无 `source_signal_ids`
- 无 `evidence_refs`
- 类型字段不合法
- YAML schema 不合法

输出：
```yaml
error:
  stage: candidate_finalize
  type: validation_error
  detail: ...
```

---

# 八、最终输出规范

## candidates.yaml

```yaml
domains: []
concepts: []
rules: []
demand_models: []
```

### 每个 domain candidate
必须包含：
- id
- name
- summary
- boundary
- role
- not_responsible_for
- source_signal_ids
- evidence_refs
- notes

### 每个 concept candidate
必须包含：
- id
- name
- summary
- boundary
- domain
- why_it_matters
- source_signal_ids
- evidence_refs
- notes

### 每个 rule candidate
必须包含：
- id
- name
- summary
- boundary
- statement
- rule_type
- consequence_hint
- source_signal_ids
- evidence_refs
- notes

### 每个 demand model candidate
必须包含：
- id
- name
- summary
- boundary
- typical_scenario
- handling_hint
- source_signal_ids
- evidence_refs
- notes

---

# 九、CC / Codex 可执行 prompt

## candidate_synthesis.prompt.md

```md
You are implementing candidate synthesis for semantic_asset_build.

Goal:
Convert signals.yaml into candidates.yaml.

You must perform:
1. Cluster similar signals into candidate clusters
2. Give each cluster a stable canonical name
3. Write summary and boundary
4. Produce candidates in exactly four groups:
   - domains
   - concepts
   - rules
   - demand_models

Important constraints:
- Do not copy raw signals one-to-one unless necessary
- Prefer fewer, stronger candidates over many fragmented ones
- Every candidate must be:
  - nameable
  - explainable
  - traceable to source signals
- Exclude noisy implementation trivia
- Preserve source_signal_ids and evidence_refs
```

---

# 十、执行命令

```bash
python -m semantic_asset_build.build_candidates   --input docs/semantic-foundation/semantic-asset-build/signals.yaml   --prompt docs/semantic-foundation/semantic-asset-build/prompts/candidate_synthesis.prompt.md   --cluster-output docs/semantic-foundation/semantic-asset-build/candidate-clusters.yaml   --output docs/semantic-foundation/semantic-asset-build/candidates.yaml   --render-md docs/semantic-foundation/semantic-asset-build/candidates.md
```

---

# 十一、给你的新人实施建议

如果你是第一次做这一步，就按这个优先级来：

## 第一优先
先让 `candidates.yaml` 稳定生成，字段全、结构稳。

## 第二优先
再让 cluster 归并更聪明。

## 第三优先
最后再优化命名和 boundary 文案。

不要一开始就追求模型“很聪明”，先保证：
- candidate 不碎
- 字段完整
- source_signal_ids 可追溯

---

# 十二、一句话总结第二步

> 第二步不是“把信号抄一遍”，而是“用模型把信号压成少量、稳定、可评审的 candidate，再用程序把它校验成 agent-friendly 的 canonical output”。
