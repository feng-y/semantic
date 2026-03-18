下面继续，直接给你 **`skills/export_cases/SKILL.md` 的最终增强版**，只聚焦你刚才确认的：

* 严格去重
* 高频模式归并
* pattern 数量控制
* 单业务域 pattern 应高度内聚，通常 < 10~20
* 这些都在 export 阶段实现，不放到 prompt 里

---

# skills/export_cases/SKILL.md（最终增强版）

````md id="skill-export-cases-final"
# export_cases

## Purpose

将已经通过基础校验的 semantic cases 落盘、汇总，并在导出阶段统一完成：

- 严格去重（strict dedup）
- 高频模式归并（pattern aggregation）
- canonical sample 选择
- pattern 数量检查
- summary 报警输出

这是最终资产导出层，不负责重新生成语义，也不负责修改 prompt 输出。

---

## Input

输入为已经通过校验的 semantic cases：

```yaml
case_id: ...
commit_id: ...
module: ...
domain: ...

commit_log: ...
issue_text: ...
development_type: ...

rules: []
invariants: []

split_suggestion:
  needs_split: false
  split_reasons: []
````

以及可选附加字段：

```yaml id="qg5mrf"
semantic_value: high|medium|low
```

---

## Output

输出到：

* `data/semantic_cases/*.yaml`
* `data/exports/cases.jsonl`
* `data/exports/duplicates.jsonl`
* `data/exports/patterns.jsonl`
* `data/exports/summary.json`

---

## Core Responsibility

### 1. 导出全量 valid cases

保留全部通过校验的样本，不在导出阶段重写其核心语义。

### 2. 执行严格去重

去掉几乎相同、模板化重复、轻微文案差异重复的样本。

### 3. 执行模式归并

将不完全相同但属于同一需求模式的样本聚合到少量 pattern 下。

### 4. 选择 canonical case / canonical pattern

为重复组和 pattern 组选择代表样本。

### 5. 控制 pattern 数量

单业务域的 pattern 应高度内聚，通常应少于 10~20 个。

### 6. 输出统计和报警

当 pattern 数过多时，在 summary 中显式报警。

---

## Important Boundaries

### A. prompt 不负责去重

prompt 只生成单个 semantic_case 的结构化语义输出，不承担全局比较、去重或模式归并。

### B. cache 不负责最终去重

cache 只解决“相同输入不要重复生成”，不解决最终资产层的近重复和模式归并。

### C. export 才是最终去重与归并层

最终的 strict dedup 和 pattern aggregation 必须在 export 阶段统一完成。

---

## Layer 1: Strict Dedup

## Goal

识别：

* 完全重复
* 模板化重复
* 轻微文案差异重复

Strict dedup 解决的问题是：

> 这是不是几乎同一条样本？

而不是：

> 这是不是同一需求模式？

---

## Strict Dedup Key

严格去重主键应尽量保守。

第一版建议基于：

* `module`
* `development_type`
* `normalized_issue_text`

推荐：

```text id="bvke9w"
dedup_key = hash(
  normalize(module) +
  "|" +
  normalize(development_type) +
  "|" +
  normalize(issue_text)
)
```

### Optional enhancement

可选加入 `constraint_signature`：

```text id="33myr4"
dedup_key = hash(
  normalize(module) +
  "|" +
  normalize(development_type) +
  "|" +
  normalize(issue_text) +
  "|" +
  normalize(constraint_signature)
)
```

### Important note

不要默认将 `commit_log` 放进严格去重主键。

原因：

* 同一模式下，对不同对象/路径/模块的改动，`commit_log` 通常天然不同
* `commit_log` 更适合做人审阅与 canonical 展示，而不是 strict dedup 主键

---

## Normalization Rules

对 `issue_text` 做轻量归一化：

* trim / strip
* 大小写统一（英文）
* 全角半角统一
* 连续空白折叠
* 标点轻量统一
* 少量同义词归一
* 可选数值占位化

### Numeric placeholder

例如：

* `线程数不要超过32`
* `线程数不要超过64`

可归一到：

* `线程数不要超过<NUM>`

但此规则应保守使用，只建议在 tweak 密集场景中开启。

---

## Strict Dedup Processing

按 `dedup_key` 分组：

* 第一条作为 canonical case
* 其余作为 duplicate cases

导出：

```json
{
  "dedup_key": "abc123",
  "canonical_case_id": "case_001",
  "duplicate_case_ids": ["case_018", "case_042"]
}
```

---

## Canonical Duplicate Selection

严格去重组内 canonical case 选择优先级：

1. `semantic_value` 更高
2. `issue_text` 更清晰且不空泛
3. `rules + invariants` 信息密度更高
4. `case_id` 更稳定（作为最后兜底）

---

## Layer 2: Pattern Aggregation

## Goal

将不完全相同，但属于同一需求模式的 case 聚合到少量 pattern 下。

这里解决的问题是：

> 这两个 case 虽然不是同一句话，但是否属于同一种需求模式？

---

## Domain Compactness Principle

一个业务域的 pattern 集应高度内聚。

目标范围：

* `< 10`：优秀
* `10 ~ 20`：可接受
* `> 20`：需报警
* `> 30`：默认认为归并策略失效或 pattern 抽象粒度过细

### Interpretation

如果 pattern 数量显著过多，优先怀疑：

* 同类近似 case 没有被有效归并
* object/action 抽象层级过细
* 参数 tweak 被误识别为独立模式
* strict dedup 太弱
* issue_text 过于具体

---

## Pattern Aggregation Principle

pattern 归并不依赖 `commit_log` 是否相同。
它依赖更高层的需求模式抽象：

* `development_type`
* `action_class`
* `object_class`
* `constraint_class`

---

## Pattern Fingerprint

推荐 fingerprint：

```text id="d4je4m"
pattern_fingerprint =
  domain +
  "|" +
  development_type +
  "|" +
  action_class +
  "|" +
  object_class +
  "|" +
  constraint_class
```

---

## Field Definitions

### domain

业务域。
pattern 统计必须按 domain 分开做。

### development_type

例如：

* feature
* bugfix
* refactor
* migration
* optimize

### action_class

从 `issue_text` 抽象：

* add
* fix
* refactor
* optimize
* migrate
* control
* align

### object_class

从 `issue_text + rules + invariants` 抽象：

* parser
* feature-extraction
* request-response-alignment
* config-control
* registry
* compatibility-path
* concurrency-control

### constraint_class

从 `rules / invariants` 抽象：

* compatibility
* alignment
* concurrency
* mapping
* contract
* migration
* boundedness

---

## Abstraction Granularity Rule

抽象层级应尽量高，宁可略粗，不要太细。

### Good

* `request-response-alignment`
* `concurrency-control`
* `config-control`

### Bad

* `qserver-score-item-alignment-after-filter`
* `qserver-request-item-alignment-after-conversion`

过细会直接导致 pattern 数暴涨。

---

## Pattern Aggregation Process

### Step 1

按 `pattern_fingerprint` 分桶。

### Step 2

桶内做近似比较：

* `normalized_issue_text`
* `rules_signature`
* `invariants_signature`

### Step 3

将高度相似样本聚成 pattern group。

---

## In-Bucket Similarity Strategy

第一版建议使用轻量相似度：

1. token Jaccard
2. SequenceMatcher
3. 可选 embedding 相似

### Suggested thresholds

* `>= 0.82` → 同模式高相似
* `0.70 ~ 0.82` → 灰区
* `< 0.70` → 不合并

---

## Grey-Zone Review

第一版可不启用模型复核，只做人工抽样。
第二版可对灰区 pair 使用小模型/LLM 复核：

> 这两个 case 是否属于同一语义模式的变体，而不是两个独立模式？

---

## Canonical Pattern Selection

每个 pattern 只保留一个 canonical case 作为代表样本。

优先保留：

1. `issue_text` 最抽象但不空泛
2. `rules / invariants` 最稳定、最有概括力
3. 不依赖具体数值和具体对象名
4. 最能代表“共同模式”的 case

canonical pattern case 不是最具体的，而是最有代表性的。

---

## Pattern Count Check

每个 domain 导出后，必须做 pattern 数量检查。

### summary.json 中必须包含

```json id="hycld8"
{
  "domain": "domainA",
  "pattern_count": 28,
  "pattern_count_status": "too_high",
  "action": "review_pattern_abstraction"
}
```

### 触发后的检查建议

若 pattern 数过高，应优先检查：

1. `object_class` 是否抽得太细
2. `action_class` 是否切得太碎
3. 参数 tweak 是否被误识别为独立模式
4. strict dedup 是否过弱
5. `issue_text` 是否过具体

---

## Output Files

### cases.jsonl

保留全部 valid case，不因 pattern merge 被删除。
每条附加：

* `dedup_key`
* `pattern_fingerprint`
* `canonical_case_id`
* `pattern_id`

### duplicates.jsonl

记录严格去重结果。

### patterns.jsonl

记录模式级资产：

```json id="c80g98"
{
  "pattern_id": "domainA|optimize|optimize|concurrency-control|boundedness#001",
  "pattern_fingerprint": "domainA|optimize|optimize|concurrency-control|boundedness",
  "count": 37,
  "canonical_case_id": "case_00123",
  "variant_case_ids": ["case_00456", "case_00981", "case_01100"],
  "representative_issue_text": "optimize：优化并发控制逻辑",
  "representative_rules": [
    "worker count must remain under configured concurrency bound"
  ],
  "representative_invariants": [
    "concurrency remains bounded by the current scheduling model"
  ]
}
```

### summary.json

必须包含：

* `total_valid_cases`
* `strict_duplicate_groups`
* `strict_duplicate_cases`
* `pattern_count`
* `high_frequency_patterns`
* `pattern_count_status`

---

## Internal Steps

建议在 `run.py` 中固定为：

1. 读取 `data/semantic_cases/*.yaml`
2. 构造内部 `CaseRecord`
3. 文本归一化
4. 生成 `dedup_key`
5. 严格去重分组
6. 为 canonical cases 生成 `pattern_fingerprint`
7. 按 `pattern_fingerprint` 分桶
8. 桶内近似比较，形成 pattern groups
9. 可选灰区复核
10. 导出：

* `cases.jsonl`
* `duplicates.jsonl`
* `patterns.jsonl`
* `summary.json`

---

## Suggested Modules

建议在 `src/` 下新增：

```text
src/
├─ normalize.py
├─ dedup.py
└─ patterning.py
```

### normalize.py

负责：

* 文本归一化
* 同义词轻量归一
* 数值占位化（可选）

### dedup.py

负责：

* `dedup_key` 生成
* 严格重复分组
* duplicate canonical 选择

### patterning.py

负责：

* `pattern_fingerprint` 生成
* object/action/constraint 抽象
* 桶内相似比较
* pattern group 构造
* pattern_count 检查

---

## Non-goals

本 skill 不负责：

* 重新生成语义字段
* 修改 `commit_log`
* 修改 `issue_text`
* 修改 `rules / invariants`
* 在 prompt 阶段做去重

---

## Failure Handling

### 1. dedup 失败

不阻断全量导出，至少保留 `cases.jsonl`

### 2. pattern aggregation 失败

保留 strict dedup 结果，并在 summary 中标注 `pattern_merge_failed`

### 3. pattern count 过高

不阻断导出，但必须在 `summary.json` 中报警

---

## Final Principle

去重与模式归并的最终目标不是“尽量多分 pattern”，而是：

> **把一个业务域内高度相似的 case 收敛成少量高内聚 pattern。**

如果最终 pattern 数明显过高，应优先认为归并策略还不够好，而不是认为业务域天然有那么多模式。

```id="jlwmba"

---

如果你要，我下一条可以继续给你一版 **`src/dedup.py` / `src/patterning.py` 的实现骨架设计**。
```
