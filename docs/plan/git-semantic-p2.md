明白，这里只收敛 **“去重与模式归并策略”**，不再展开整套方案。

你新增的这个判断很关键：

> **一个业务域的需求模式应该高度内聚，最终抽取出来的 pattern 数量通常不应太多，理想上 < 10~20。**
> 如果 pattern 数过多，往往说明系统里存在大量同类近似 commit/case，没有被有效归并。

这个会直接改变去重与模式归并的目标函数。

---

# 去重与模式归并策略（最终版）

## 1. 目标

对已经生成好的 `semantic_case` 结果做两件事：

### 1）严格去重

去掉几乎相同、模板化重复、轻微文案差异重复的样本。

### 2）模式归并

把不完全相同但属于同一**需求模式**的样本归并成少量高内聚 pattern。

最终目标不是得到很多 pattern，而是得到：

> **少量、稳定、可解释、业务域内高度内聚的 pattern 集合**

对一个单业务域来说，理想 pattern 数量应该控制在：

* **优选：< 10**
* **可接受：10 ~ 20**
* **明显异常：> 20**

如果明显超过这个范围，优先怀疑：

* 同类近似 case 没有被并到一起
* pattern 抽象层级过细
* 把参数微调 / 配置 tweak 当成独立模式
* 去重太弱
* object/action 抽象不稳定

---

## 2. 实现位置

这部分统一放在：

> **`export_cases` 的 merge/export 子阶段**

不要放在 prompt 里。
不要依赖 cache 顺带解决。
不要在 `collect_cases` 阶段做最终语义级归并。

### 原因

* prompt 没有全局视角
* cache 只能防重复生成，不能防语义近重复
* 只有 export 阶段拿到了完整语义字段，才适合做模式级判断

---

## 3. 两层目标必须分开

这里最重要的是：

> **严格去重 ≠ 模式归并**

这两个目标要分开实现。

---

## 4. 第一层：严格去重（Strict Dedup）

### 4.1 目标

识别几乎相同的样本，例如：

* 同一语义句子只是标点不同
* 同一模板句，只有轻微措辞差异
* 多次重复生成的近乎相同 case

### 4.2 原则

严格去重必须保守。
它解决的是：

> **这是不是几乎同一条样本？**

而不是：

> **这是不是同一需求模式？**

---

### 4.3 去重主键不应依赖 commit_log

这个点要明确：

> **`commit_log` 不适合作为严格去重的核心主键。**

因为即使属于同一模式：

* 对不同模块调整
* 对不同对象新增
* 对不同路径修复

`commit_log` 也天然会不同。

所以严格去重主看：

* `module`
* `development_type`
* `normalized_issue_text`

必要时再辅以：

* `constraint_signature`

---

### 4.4 推荐 dedup_key

第一版建议：

```text
dedup_key = hash(
  normalize(module) +
  "|" +
  normalize(development_type) +
  "|" +
  normalize(issue_text)
)
```

可选增强版：

```text
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

其中：

### `constraint_signature`

对 `rules + invariants` 做轻量抽象，例如提取关键词后排序：

* compatibility
* alignment
* concurrency
* mapping
* contract
* migration

如果这层还不稳定，第一版可以先不加。

---

### 4.5 归一化规则

对 `issue_text` 做 normalize：

* 去空白
* 全角半角统一
* 标点轻量统一
* 大小写统一
* 少量同义词归一
* 可选数值占位化

例如：

* `线程数不要超过32`
* `线程数不要超过64`

可归一到：

* `线程数不要超过<NUM>`

但注意：

> **数值占位化只适合在某些 tweak 密集场景开启，不建议全局滥用。**

---

### 4.6 严格去重输出

按 `dedup_key` 分组：

* 选一个 canonical case
* 其他记录为 duplicates

输出：

* `duplicates.jsonl`

示例：

```json
{
  "dedup_key": "abc123",
  "canonical_case_id": "case_001",
  "duplicate_case_ids": ["case_018", "case_042"]
}
```

---

## 5. 第二层：模式归并（Pattern Aggregation）

### 5.1 目标

把不完全相同、但本质属于同一**需求模式**的 case 归到同一个 pattern。

这里回答的问题是：

> **这两个 case 虽然不是同一句话，但是否属于同一种需求模式？**

---

### 5.2 核心原则：pattern 数必须被压缩到少量

你新增的这个约束非常重要，建议直接写死：

> **单业务域的 pattern 数量应高度内聚，通常不应超过 10~20。**

所以模式归并的目标不是“尽可能细”，而是：

> **尽可能把同类近似 case 向少量模式收敛**

如果最终得到几十上百个 pattern，默认应视为归并失败，而不是成功。

---

### 5.3 模式归并的核心对象不是 commit_log，而是“需求模式抽象”

模式归并应该主要依赖：

* `issue_text`
* `development_type`
* `rules / invariants` 抽象
* 对象类 / 动作类抽象

而不是依赖原始 `commit_log` 文本相同。

因为 pattern 是更高一层的东西。

---

## 6. pattern_fingerprint 设计

### 6.1 目的

先把 case 分桶，再做桶内近似归并。
避免全量两两比较。

### 6.2 推荐 fingerprint 组成

```text
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

### 6.3 各字段说明

#### `domain`

业务域。
这一层非常重要，因为你现在讨论的是“另一个业务域”。

如果 domain 不先切开，pattern 很容易虚高。

---

#### `development_type`

例如：

* feature
* bugfix
* refactor
* migration
* optimize

---

#### `action_class`

从 `issue_text` 抽象的动作类：

* add
* fix
* refactor
* optimize
* migrate
* control
* align

注意，这里可以比 development_type 更细一点，但不要过细。

---

#### `object_class`

从 `issue_text + rules + invariants` 抽象的对象类：

例如：

* config-control
* concurrency-control
* request-response-alignment
* registry-structure
* compatibility-path
* feature-extraction
* parser-logic

---

#### `constraint_class`

从 `rules / invariants` 抽象：

* compatibility
* alignment
* concurrency
* mapping
* contract
* migration
* boundedness

---

## 7. object/action/constraint 的抽象粒度要求

这里必须有一个原则：

> **抽象层级应尽量高，宁可略粗，不要太细。**

因为你的目标是把 pattern 压到 <10~20。

所以不要抽成：

* `qserver-score-item-alignment-after-filter`
* `qserver-request-item-alignment-after-conversion`

这种太细。

更合理的是统一成：

* `request-response-alignment`

---

## 8. 模式归并策略

### Step 1：按 `pattern_fingerprint` 分桶

先得到粗桶。

### Step 2：桶内相似比较

在桶内再比较：

* `normalized_issue_text`
* `normalized_rules_signature`
* `normalized_invariants_signature`

### Step 3：聚合为 pattern group

将高度相似的 case 聚成一个 pattern。

---

## 9. 桶内相似度策略

第一版不要太重，建议：

### 9.1 必选

* token Jaccard 相似
* SequenceMatcher 相似

### 9.2 可选

* embedding 相似

### 9.3 不建议第一版就全量做

* pairwise LLM 打分

---

## 10. canonical pattern 的选择

每个 pattern 只保留一个 canonical pattern case 作为代表。

### 选择原则

优先保留：

1. `issue_text` 最抽象但不空泛的
2. `rules / invariants` 最稳定、最有概括力的
3. 不依赖具体数值和具体对象名的
4. 能代表这一类修改“共同语义”的

也就是说：

> **canonical case 不是最具体的，而是最能代表模式的。**

---

## 11. pattern 输出格式

输出到：

* `patterns.jsonl`

示例：

```json
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

---

## 12. pattern 数量控制机制

这是你新增的最关键要求，建议变成**强检查**。

### 12.1 规则

单业务域的 pattern 数量应满足：

* `< 10`：优秀
* `10 ~ 20`：可接受
* `> 20`：需报警
* `> 30`：默认认为归并策略失效或抽象粒度过细

---

### 12.2 触发后的处理

如果 pattern 数过多，不要直接接受结果，而是执行：

#### 检查项 1

是否 object_class 抽得太细

#### 检查项 2

是否 action_class 切得太碎

#### 检查项 3

是否把参数 tweak 误当独立模式

#### 检查项 4

是否严格去重太弱，导致大量近重复漏掉

#### 检查项 5

是否 `issue_text` 过具体，导致模式无法收敛

---

### 12.3 summary.json 增加报警项

例如：

```json
{
  "domain": "domainA",
  "pattern_count": 28,
  "pattern_count_status": "too_high",
  "action": "review_pattern_abstraction"
}
```

---

## 13. 该放在哪实现

这里给 Claude Code 的最终结论必须明确：

### prompt

不做去重，不做模式归并。

### cache

只做“相同输入不要重复生成”，不做最终资产去重。

### collect_cases

不做最终语义级归并，只做 semantic_case 构造。

### export_cases

统一负责：

* 严格去重
* 高频模式归并
* canonical sample 选择
* pattern 数量检查
* summary 报警

---

## 14. 代码层实现建议

建议在 `src/` 下新增：

```text
src/
├─ normalize.py
├─ dedup.py
└─ patterning.py
```

---

### normalize.py

负责：

* 文本归一化
* 同义词轻量归一
* 数值占位化（可选）

核心函数：

* `normalize_text(text: str) -> str`

---

### dedup.py

负责：

* `dedup_key` 生成
* 严格重复分组
* canonical duplicate 选择

核心函数：

* `build_dedup_key(case: CaseRecord) -> str`
* `group_strict_duplicates(cases: list[CaseRecord]) -> list[DedupGroup]`

---

### patterning.py

负责：

* `pattern_fingerprint` 生成
* object/action/constraint 抽象
* 桶内相似比较
* pattern group 构造
* pattern_count 检查

核心函数：

* `build_pattern_fingerprint(case: CaseRecord) -> str`
* `group_patterns(cases: list[CaseRecord]) -> list[PatternGroup]`
* `check_pattern_count(patterns: list[PatternGroup], domain: str) -> PatternCheckResult`

---

## 15. Claude Code 可直接执行的实现版本

### v1

先实现：

* 严格去重：`module + development_type + normalized_issue_text`
* pattern_fingerprint 分桶
* 桶内 Jaccard / SequenceMatcher 比较
* `patterns.jsonl`
* `summary.json` 增加 pattern_count 检查

### v2

再补：

* embedding 相似
* 灰区样本 LLM 复核
* 更强的 canonical pattern 选择
* pattern_count 过高后的自动回溯建议

---

## 16. 最终一句话要求（可直接给 CC）

> 在 `export_cases` 阶段实现分层去重与模式归并：
> 先基于 `module + development_type + normalized_issue_text` 做严格去重；
> 再基于 `development_type + action_class + object_class + constraint_class` 做模式分桶，并在桶内做轻量相似比较形成 pattern groups；
> 同时对每个业务域统计最终 pattern 数量，并将 `<10~20` 作为合理范围，若 pattern 数明显过高，则在 `summary.json` 中给出报警，提示当前业务域存在大量同类近似 commit/case 未被有效归并，或 pattern 抽象粒度过细。

如果你要，我下一条可以直接把这部分改写成 **`skills/export_cases/SKILL.md` 的最终增强版**。
