# semantic_asset_build MVP 实施设计（可编码、可运行）

## 背景与约束

当前仓库已经有稳定的 plugin-facing 结构：`manifest.yaml` 注册了 `init / discover / review / refine / baseline / status / reset` 等 skill；README 说明生成态写在 `docs/semantic/`，而内部 runtime 组织在 `src/` 下。现有 discover 阶段会产出 `repo-facts.vN.md`、`domain-candidates.vN.md`、`repo-understanding.vN.md`、`knowledge-confidence.vN.md` 和 `review-summary.vN.md`；baseline 会合成 `purpose.md / domains.md / concepts.md / pipelines.md`。这些都是 `semantic_asset_build` 的输入，不应被重做，也不应打穿现有主链。citeturn305275view0turn305275view1turn305275view2turn305275view3

## 目标

`semantic_asset_build` 的目标是：

> 基于现有 fact layer，离线生产 Step3 可直接消费的正式语义资产：
- Domain Map
- Concept Map
- Rule Map
- Demand Model Map

并形成一条最小可闭环链路：

```text
docs/semantic/* (fact layer)
→ semantic_asset_build
→ docs/semantic-foundation/semantic-asset-build/*
→ Step3 demand_card_build
```

## MVP 范围

### 业务域
只收敛 1 个主业务域：
- Semantic Artifact Construction

### 价值域 / 底线域
收敛 3 个：
- Runtime Orchestration
- Validation & Schema Contract
- Versioning & State Integrity

### 正式资产配额
- Domain：4–5
- Concept：12–18
- Rule：10–15
- Demand Model：4–6

---

# 一、总流程（最终执行版）

## 主流程
```text
A. 输入收束与候选生成
B. AI 初筛、打分与推荐
C. 人工辅助决策与局部补证回路
D. 正式固化与发布
```

## 关键固定规则
- 不重新全量扫描 repo
- 只消费 Step1 的 fact layer 和少量 review 工件
- 优先级固定为：`priority = max(business_score, value_score)`
- AI 负责推荐，不负责最终固化
- 人工只做辅助决策与收口
- 局部补证只在明确证据缺口时触发

---

# 二、代码结构

建议新增：

```text
src/semantic_asset_build/
  __init__.py
  config.py
  models.py
  io_utils.py
  collect_inputs.py
  build_candidates.py
  score_recommend.py
  apply_review.py
  evidence_check.py
  finalize_assets.py
  run.py
```

以及文档与模板：

```text
docs/semantic-foundation/semantic-asset-build/
  prompts/
    candidate_generation.prompt.md
    scoring_recommendation.prompt.md
    evidence_check.prompt.md
  templates/
    domain-map.template.md
    concept-map.template.md
    rule-map.template.md
    demand-model-map.template.md
    review-note.template.md
  step2_input_bundle.md
  step2_candidates.yaml
  step2_recommendations.yaml
  step2_candidate_review_note.md
  evidence_checks.yaml
  domain-map.md
  concept-map.md
  rule-map.md
  demand-model-map.md
  change-log.md
```

---

# 三、数据模型

## Candidate

```python
from dataclasses import dataclass, field
from typing import List, Literal, Optional

CandidateType = Literal["domain", "concept", "rule", "demand_model"]

@dataclass
class Candidate:
    name: str
    type: CandidateType
    source_signals: List[str]
    evidence_refs: List[str]
    notes: List[str] = field(default_factory=list)
```

## Recommendation

```python
RecommendationStatus = Literal["recommend", "not_recommend", "defer"]
RecommendationAction = Literal["keep", "merge", "drop", "backlog", "verify_first"]

@dataclass
class Recommendation:
    name: str
    type: CandidateType

    semantic_validity: Literal["pass", "fail"]
    validity_reason: str

    business_score: int
    value_score: int
    priority: int  # fixed = max(business_score, value_score)

    status: RecommendationStatus
    action: RecommendationAction
    target_layer: Literal["final_asset", "candidate_pool"]
    target_asset_type: Literal["domain_map", "concept_map", "rule_map", "demand_model_map", "none"]

    recommended_reasons: List[str]
    not_recommended_reasons: List[str]

    needs_evidence_check: bool = False
    evidence_gap: Optional[str] = None
    merge_target: Optional[str] = None
```

## ReviewDecision

```python
ReviewAction = Literal["keep", "merge", "drop", "backlog", "verify_first"]

@dataclass
class ReviewDecision:
    name: str
    type: CandidateType
    final_action: ReviewAction
    final_reason: str
    merge_target: Optional[str] = None
```

---

# 四、A. 输入收束与候选生成

## 解决的问题
把 `docs/semantic/` 下版本化工件整理成 Step2 可消费输入，并生成候选层，避免 facts 直接跳成正式资产。现有 discover 工件和 review 工件的位置、命名、职责在 USER_GUIDE 中已明确。citeturn305275view2

## 输入
- `docs/semantic/discovery/repo-facts.vN.md`
- `docs/semantic/discovery/domain-candidates.vN.md`
- `docs/semantic/discovery/repo-understanding.vN.md`
- `docs/semantic/discovery/knowledge-confidence.vN.md`
- `docs/semantic/review/review-summary.vN.md`
- `docs/semantic/review/architect-feedback.md`（可选）
- `docs/semantic/review/semantic-change-log.md`（可选）

## 输出
- `step2_input_bundle.md`
- `step2_candidates.yaml`

## 脚本 1：collect_inputs.py
### 职责
1. 找到最新 discovery / review 工件
2. 归并为轻量输入包
3. 输出 `step2_input_bundle.md`

### 运行命令
```bash
python -m semantic_asset_build.collect_inputs   --semantic-root docs/semantic   --output docs/semantic-foundation/semantic-asset-build/step2_input_bundle.md
```

### 最小实现逻辑
1. 在 `docs/semantic/discovery/` 下查找每类 `*.vN.md`
2. 取最新版本
3. 摘出：
   - high-confidence facts
   - domain signals
   - concept signals
   - rule signals
   - demand-pattern signals
   - ambiguities
4. 写入 bundle

### 输出格式
```md
# Step2 Input Bundle

## High-Confidence Facts
- ...

## Domain Signals
- ...

## Concept Signals
- ...

## Rule Signals
- ...

## Demand Pattern Signals
- ...

## Known Ambiguities
- ...

## Review-Derived Constraints
- ...
```

## 脚本 2：build_candidates.py
### 职责
1. 读取 input bundle
2. 调用 prompt 生成四类候选
3. 输出 `step2_candidates.yaml`

### 运行命令
```bash
python -m semantic_asset_build.build_candidates   --input docs/semantic-foundation/semantic-asset-build/step2_input_bundle.md   --prompt docs/semantic-foundation/semantic-asset-build/prompts/candidate_generation.prompt.md   --output docs/semantic-foundation/semantic-asset-build/step2_candidates.yaml
```

### 关键判断
- 这一步偏 recall
- 允许候选池稍广
- 但不输出最终资产

### 输出格式
```yaml
domains:
  - name: Semantic Artifact Construction
    source_signals: []
    evidence_refs: []
    notes: []

concepts: []
rules: []
demand_models: []
```

---

# 五、B. AI 初筛、打分与推荐

## 解决的问题
把候选层变成可 review 的推荐清单，而不是让人工直接面对大候选池。

## 输入
- `step2_candidates.yaml`
- MVP 配额（domain 4–5 / concept 12–18 / rule 10–15 / demand model 4–6）
- `scoring_recommendation.prompt.md`

## 输出
- `step2_recommendations.yaml`

## 实现脚本：score_recommend.py
### 职责
1. 对每个候选做语义有效性判断
2. 给出 `business_score`
3. 给出 `value_score`
4. 计算 `priority = max(business_score, value_score)`
5. 生成推荐状态、动作、推荐理由、不推荐理由
6. 标记是否需要补证

### 运行命令
```bash
python -m semantic_asset_build.score_recommend   --input docs/semantic-foundation/semantic-asset-build/step2_candidates.yaml   --prompt docs/semantic-foundation/semantic-asset-build/prompts/scoring_recommendation.prompt.md   --output docs/semantic-foundation/semantic-asset-build/step2_recommendations.yaml
```

### 输出格式
```yaml
domains:
  - name: Runtime Orchestration
    type: domain
    semantic_validity: pass
    validity_reason: Stable structural domain
    business_score: 2
    value_score: 5
    priority: 5
    status: recommend
    action: keep
    target_layer: final_asset
    target_asset_type: domain_map
    recommended_reasons:
      - Core foundation domain
      - Carries execution constraints
    not_recommended_reasons:
      - Not a high-frequency business entry domain
    needs_evidence_check: false
```

### 固定约束
- 先做 semantic_validity
- `priority` 必须等于 `max(business_score, value_score)`
- 推荐必须包含：
  - 推荐哪些
  - 推荐原因
  - 哪些不推荐
  - 不推荐原因

---

# 六、C. 人工辅助决策与局部补证回路

## 解决的问题
AI 推荐不是最终结果，必须人工收口；对重要但证据不足的对象，必须允许局部补证。

## 输入
- `step2_recommendations.yaml`

## 输出
- `step2_candidate_review_note.md`
- （可选）`evidence_checks.yaml`

## 实现脚本 1：apply_review.py
### 职责
1. 读取推荐结果
2. 生成 review skeleton
3. 由人工填写最终动作：
   - keep
   - merge
   - drop
   - backlog
   - verify_first

### 运行命令
```bash
python -m semantic_asset_build.apply_review   --input docs/semantic-foundation/semantic-asset-build/step2_recommendations.yaml   --template docs/semantic-foundation/semantic-asset-build/templates/review-note.template.md   --output docs/semantic-foundation/semantic-asset-build/step2_candidate_review_note.md
```

### review-note 最小格式
```md
# Step2 Candidate Review Note

## Keep
- <candidate>: <reason>

## Merge
- <candidate> -> <merge_target>: <reason>

## Drop
- <candidate>: <reason>

## Backlog
- <candidate>: <reason>

## Verify First
- <candidate>: <reason>
```

## 实现脚本 2：evidence_check.py
### 触发条件
只有 `verify_first` 才触发。

### 职责
1. 读取需要补证的候选
2. 调用 evidence prompt
3. 只做局部补证，不重扫 repo

### 运行命令
```bash
python -m semantic_asset_build.evidence_check   --input docs/semantic-foundation/semantic-asset-build/step2_recommendations.yaml   --prompt docs/semantic-foundation/semantic-asset-build/prompts/evidence_check.prompt.md   --output docs/semantic-foundation/semantic-asset-build/evidence_checks.yaml
```

### evidence_checks 最小格式
```yaml
checks:
  - target: SchemaValidationMustGateArtifacts
    reason: Validation evidence too weak
    expected_evidence: explicit validation gate references
    result: confirmed
    notes: confirmed from schema contract and write path
```

### 严格限制
- 允许：
  - Clarify domain boundary
  - Find code anchor for concept
  - Find validation/evidence for rule
  - Find representative scenario for demand model
- 禁止：
  - Full repository rescan
  - Broad exploration for completeness
  - Re-running Step1 behavior

---

# 七、D. 正式固化与发布

## 解决的问题
把 review 后的结果发布成 Step3 可直接消费的正式资产。

## 输入
- `step2_recommendations.yaml`
- `step2_candidate_review_note.md`
- `evidence_checks.yaml`（如果有）

## 输出
- `domain-map.md`
- `concept-map.md`
- `rule-map.md`
- `demand-model-map.md`
- `change-log.md`

## 实现脚本：finalize_assets.py
### 职责
1. 读取最终 review 结果
2. 按模板渲染四类正式资产
3. 写变更日志

### 运行命令
```bash
python -m semantic_asset_build.finalize_assets   --recommendations docs/semantic-foundation/semantic-asset-build/step2_recommendations.yaml   --review-note docs/semantic-foundation/semantic-asset-build/step2_candidate_review_note.md   --evidence-checks docs/semantic-foundation/semantic-asset-build/evidence_checks.yaml   --template-root docs/semantic-foundation/semantic-asset-build/templates   --output-root docs/semantic-foundation/semantic-asset-build
```

### 最小模板要求

#### Domain Map
- Purpose
- Boundary
- Related Concepts
- Evidence
- BusinessScore
- ValueScore

#### Concept Map
- Definition
- Domain
- Relationships
- Code Anchors
- Why It Matters
- Evidence
- BusinessScore
- ValueScore

#### Rule Map
- Scope
- Statement
- RuleType
- Consequence
- Validation
- Evidence
- BusinessImpact
- ValueImpact

#### Demand Model Map
- Typical Scenario
- Typical Domains
- Typical Concepts
- Typical Rules
- Recommended Handling
- Validation Focus
- Common Risks
- BusinessCoverage
- ValueCoverage

#### Change Log
```md
# Change Log

## Scope
- Business domain(s):
- Value domain(s):

## Added
- ...

## Merged
- ...

## Dropped
- ...

## Deferred
- ...

## Evidence Checks
- ...
```

---

# 八、总控入口

## run.py
支持一条命令跑完整个 MVP：

```bash
python -m semantic_asset_build.run   --semantic-root docs/semantic   --output-root docs/semantic-foundation/semantic-asset-build   --mode mvp
```

### 建议行为
- 自动执行 A、B
- 自动生成 C 的 review skeleton
- 等待人工填写 review
- 如果存在 verify_first，则执行 evidence_check
- 最后执行 D

---

# 九、Claude Code / Codex 分阶段实施方式

## 第一阶段：搭骨架
```text
Implement semantic_asset_build scaffolding under src/semantic_asset_build and docs/semantic-foundation/semantic-asset-build.
Create directories, module files, templates, and prompt files only.
Do not modify the current discover/refine/baseline pipeline.
```

## 第二阶段：实现 A + B
```text
Implement:
- collect_inputs.py
- build_candidates.py
- score_recommend.py

These scripts must read existing semantic artifacts under docs/semantic and produce:
- step2_input_bundle.md
- step2_candidates.yaml
- step2_recommendations.yaml
```

## 第三阶段：实现 C + D + run.py
```text
Implement:
- apply_review.py
- evidence_check.py
- finalize_assets.py
- run.py

Support:
- review skeleton generation
- verify_first evidence check loop
- final asset rendering
- change-log output
```

---

# 十、验证规则

## 文件验证
必须生成：
- step2_input_bundle.md
- step2_candidates.yaml
- step2_recommendations.yaml
- step2_candidate_review_note.md
- domain-map.md
- concept-map.md
- rule-map.md
- demand-model-map.md
- change-log.md

## 结构验证
- `priority == max(business_score, value_score)`
- Rule 必须带 Validation
- Demand Model 必须引用 Domain / Concept / Rule
- 正式资产必须落在配额范围内

## 范围验证
- 业务域：1 个（MVP 当前默认）
- 价值域：3 个
- 不允许正式资产层无限扩张

---

# 十一、最终推荐

`semantic_asset_build` 的 MVP，直接按 4 个主步骤落地：

1. 输入收束与候选生成
2. AI 初筛、打分与推荐
3. 人工辅助决策与局部补证回路
4. 正式固化与发布

这套已经可以直接编码实现，不需要再继续抽象讨论。
