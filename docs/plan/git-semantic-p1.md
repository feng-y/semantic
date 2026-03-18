下面给你一版 **新增需求整理 + 可直接交给 Claude Code 实现的补充方案**。
它是在前面最终方案基础上新增的，不推翻原设计，只补齐你刚才确认的约束。

---

# 新增需求整理

## 新增需求 1：不是所有 commit / case 都值得进入语义库

系统目标不是“覆盖所有 commit”，而是：

> **沉淀高语义价值的 semantic_case**

因此需要显式支持：

* 高价值 case：进入主语义库
* 中价值 case：进入主语义库或保留观察
* 低价值 case：进入 `low_value_cases/` 或直接丢弃

这一步必须发生在 `collect_cases` 阶段，不能等到最终导出才处理。

---

## 新增需求 2：teams agent 的并发粒度是 commit 级

并发时：

> **一个 commit 使用一个 agent**

而不是：

> 一个 commit 内多个 agent 分头处理

原因：

* commit 是天然原始容器
* commit 内分组/归并依赖全局一致理解
* 一个 commit 多 agent 会导致 semantic_case 归并风格漂移
* 会增加 orchestration 复杂度

所以 teams agent 应该用于：

* commit shard 并发
* 失败 commit 重跑
* 模块维度的大规模批量回填

但始终坚持：

> **一个 agent 负责一个 commit 的完整闭环处理**

---

## 新增需求 3：skill 仍保持“一个 skill 完成一个完整任务”

外部 pipeline 不变，仍然只有 3 个 skill：

* `collect_cases`
* `generate_case_semantics`
* `export_cases`

但需要强调：

> **外部一个 skill 完成一个完整任务；skill 内部允许必要子步骤，但不外扩成更多 skill。**

---

## 新增需求 4：输出目录和最终产物必须明确

新增要求后，输出目录要增加：

* `low_value_cases/`

最终主输出仍然是：

* `data/semantic_cases/*.yaml`
* `data/exports/cases.jsonl`
* `data/exports/summary.json`

补充输出：

* `data/low_value_cases/*.yaml`
* `data/invalid_cases/*.yaml`

---

## 新增需求 5：高频配置类 / 微调类样本需要去重或模式归并

系统中会有大量：

* 配置项增删改
* 开关接线
* 阈值调整
* 并发参数微调
* 小型 optimize tweak
* 高频类似 patch

这些不一定应全部平权进入主 case 库。
需要在 `export_cases` 阶段增加：

* 严格近重复去重
* 高频模式归并

输出：

* 全量 `cases.jsonl`
* 模式级 `patterns.jsonl`
* `summary.json`

---

# 补充后的最终方案

---

## 1. 系统目标（补充版）

系统不追求“语义化所有 commit”，而追求：

> **从历史代码中沉淀高价值 semantic_case，并形成稳定、可复用、可检索的语义资产库**

因此系统必须同时支持：

* 高价值 case 入主库
* 低价值 case 过滤或旁路存储
* 高频相似 case 模式归并
* commit 级并发处理

---

## 2. 新增实施约束

### 2.1 语义价值优先，不追求全量覆盖

硬规则：

> **系统不追求覆盖所有 commit，而追求沉淀高语义价值 case。**

---

### 2.2 teams agent 固定为 commit 粒度

硬规则：

> **一个 commit 一个 agent。**

每个 agent 负责这个 commit 的完整闭环：

* raw commit 提取
* change_group 构造
* semantic_case 归并
* 语义生成
* 校验与输出

禁止：

* 同一个 commit 内多个 agent 并行处理不同子部分

---

### 2.3 外部 skill 不增加

硬规则：

> **外部仍然只有 3 个 skill。**

* `collect_cases`
* `generate_case_semantics`
* `export_cases`

---

### 2.4 低价值 case 必须显式处理

不能让低价值样本混进主语义库。

处理结果只允许三种：

* 主库保留
* 低价值桶保留
* 直接丢弃

---

### 2.5 高频微调类样本必须做模式压缩

高频配置、开关、阈值、资源参数微调类样本，不应全部平权进入主检索资产。

必须支持：

* 严格近重复去重
* 高频模式归并
* canonical sample 保留
* frequency count 保留

---

## 3. 输出目录（补充版）

推荐目录更新为：

```text id="dir-update-01"
data/
├─ raw_commits/
├─ semantic_case_inputs/
├─ semantic_cases/
├─ low_value_cases/
├─ invalid_cases/
└─ exports/
```

---

## 4. 各目录含义

### `data/raw_commits/`

原始 commit 提取结果，仅供追溯和调试。

### `data/semantic_case_inputs/`

`collect_cases` 的标准输出。
每个文件对应一个 `semantic_case` 输入。

### `data/semantic_cases/`

最终有效语义样本。
这是主资产目录。

### `data/low_value_cases/`

低语义价值样本。
不进入主 case 库，但可供统计和模式分析。

### `data/invalid_cases/`

生成失败、校验失败、结构异常样本。

### `data/exports/`

导出层，至少包含：

* `cases.jsonl`
* `patterns.jsonl`
* `summary.json`

---

## 5. 最终主输出是什么

### 主输出 A：逐 case YAML

位置：

* `data/semantic_cases/*.yaml`

用途：

* 人审阅
* case 调试
* case 复用

---

### 主输出 B：全量 JSONL

位置：

* `data/exports/cases.jsonl`

用途：

* embedding
* retrieval
* downstream training
* 批量分析

---

### 主输出 C：模式级 JSONL

位置：

* `data/exports/patterns.jsonl`

用途：

* 高频类似 case 压缩
* 模式发现
* canonical case 管理

---

### 主输出 D：summary

位置：

* `data/exports/summary.json`

建议字段：

```json id="summary-example-01"
{
  "total_commits": 0,
  "processed_commits": 0,
  "total_semantic_cases": 0,
  "valid_cases": 0,
  "low_value_cases": 0,
  "invalid_cases": 0,
  "development_type_distribution": {
    "feature": 0,
    "bugfix": 0,
    "refactor": 0,
    "migration": 0,
    "optimize": 0
  },
  "needs_split_ratio": 0.0,
  "pattern_count": 0
}
```

---

## 6. collect_cases 新增职责

`collect_cases` 在原有职责上，新增两件事：

### 6.1 语义价值判断

对 commit / semantic_case 候选做 `semantic_value` 评估：

* `high`
* `medium`
* `low`

### 6.2 低价值分流

根据 `semantic_value` 做分流：

* `high` / `medium` → 正常进入 `semantic_case_inputs`
* `low` → 进入 `low_value_cases/` 或直接丢弃

---

## 7. semantic_value 判断规则

建议使用轻规则，不做复杂模型。

### 高价值 case

通常具备：

* 明确主对象
* 明确主动作
* 能形成稳定 `commit_log`
* 能形成潜在 `issue_text`
* 有对象语义约束价值

例如：

* parser compatibility fix
* qserver request-response alignment repair
* feature extraction concurrency control adjustment
* registry structure refactor

---

### 中价值 case

通常具备：

* 有可识别主动作
* 但约束较弱或语义密度一般
* 可进入主库，也可保留观察

例如：

* 一般性接入类 feature
* 普通优化类 patch
* 中等强度 refactor

---

### 低价值 case

通常是：

#### A. 纯机械性修改

* format only
* lint only
* import reorder
* comment/doc only
* rename without semantic change

#### B. 纯测试维护

* snapshot update only
* flaky test tweak
* test rename only
* assertion text cleanup only

#### C. 纯样板接线

* trivial config key wiring only
* trivial flag wiring only
* trivial registration append only

#### D. 低信息密度微调

* timeout tweak only
* retry count tweak only
* pure threshold value tweak only
* small worker count tweak with no stable object semantics

#### E. 无法形成稳定主语义包

* 改动太散
* 只有碎片
* 无法稳定形成 `commit_log`

---

## 8. low_value_cases 的处理策略

低价值 case 不一定全删，建议两类处理：

### 8.1 直接丢弃

适合明显无价值：

* format/lint/doc/import only

### 8.2 存入低价值桶

适合仍有统计意义：

* 高频参数 tweak
* 轻配置接线
* 高频微调 patch

位置：

* `data/low_value_cases/`

这部分后续可做：

* 频率分析
* pattern 归并原料
* 降噪统计

---

## 9. teams agent 设计（补充版）

### 9.1 正确粒度

固定规则：

> **每一个 commit 使用一个 agent**

---

### 9.2 一个 agent 的职责闭环

一个 agent 对一个 commit 必须完整完成：

1. raw commit 提取
2. change_group 构造
3. semantic_case 归并
4. 语义生成
5. 校验
6. 输出

---

### 9.3 不允许的方式

禁止：

* 同一个 commit 内多个 agent 分别处理不同模块
* 同一个 commit 内多个 agent 分别处理 parser / config / tests
* 同一个 commit 内多个 agent 分裂判断 semantic_case

原因：

* 会破坏 commit 内一致理解
* semantic_case 归并会漂
* 附带属性判断会漂
* split 判断会漂

---

### 9.4 teams agent 的推荐使用方式

#### 模式 A：commit shard 并发

把 commit 列表切片：

* shard_001
* shard_002
* shard_003

每个 agent 拉一批 commit，逐个处理。

#### 模式 B：失败 commit 重跑

主流程跑完后，把失败 commit 交给新的 agent 批量重试。

#### 模式 C：模块专题回填

按模块筛 commit，再按 commit 级并行处理。

但无论哪种模式，都保持：

> 一个 commit 一个 agent

---

## 10. export_cases 新增职责

`export_cases` 在原职责上增加：

### 10.1 严格近重复去重

可生成 `dedup_key`，建议基于：

* module
* normalized issue_text
* development_type
* normalized commit_log

用于消除明显重复样本。

---

### 10.2 高频模式归并

新增 `pattern_fingerprint`，例如基于：

* module
* development_type
* normalized issue template
* modified object class
* rules/invariants signature

例如：

* `feature-extraction + optimize + concurrency-control`
* `config-control + feature`
* `qserver + bugfix + alignment`

---

### 10.3 输出 canonical pattern

每个 pattern 至少输出：

```yaml id="pattern-example-01"
pattern_id: ...
count: ...
canonical_case_id: ...
variant_case_ids: []
```

---

## 11. 高频相似样本处理策略

### 11.1 不建议简单全删

因为高频本身有价值。

### 11.2 正确做法

对高频相似样本：

* 保留全量原始 case
* 主导出层只保留 canonical sample
* 记录出现频率
* 保留少量变体

### 11.3 特别值得模式压缩的类型

* 配置 / 开关类
* 阈值 / 并发 / 资源控制微调类
* 映射表 / 注册表追加类
* 小型 optimize tweak
* 高频类似 patch

---

## 12. skill 约束（最终版）

### 12.1 外部 skill 约束

外部只有 3 个 skill，每个 skill 完成一个完整任务：

* `collect_cases`
* `generate_case_semantics`
* `export_cases`

### 12.2 内部 pipeline 约束

skill 内部允许必要子步骤，例如：

* prompt 1 / 2 / 3
* validate
* assemble

但不扩展成更多 skill。

---

## 13. 最终新增规则可直接写进 README 的“实施约束”

### 约束 1：skill 约束

> 外部一个 skill 完成一个完整任务；skill 内部允许必要子步骤，但不外扩成额外 skill。

### 约束 2：输出约束

> 最终主输出是：
>
> * `data/semantic_cases/*.yaml`
> * `data/exports/cases.jsonl`
> * `data/exports/patterns.jsonl`
> * `data/exports/summary.json`

### 约束 3：低价值过滤约束

> 系统不追求覆盖所有 commit，而追求沉淀高语义价值 case。
> 低价值样本必须进入 `low_value_cases/` 或直接丢弃。

### 约束 4：teams agent 约束

> teams agent 的并发粒度固定为：一个 commit 一个 agent。
> 不允许一个 commit 内多个 agent 分头处理。

### 约束 5：去重约束

> 同时做：
>
> * 严格近重复去重
> * 高频相似模式归并
>   并保留 canonical sample + frequency，而不是简单删除。

---

# 可以直接交给 Claude Code 的最终实现任务

你可以直接让它做下面这些：

## 第一批

* 更新 `README.md`
* 更新 `skills/collect_cases/SKILL.md`
* 更新 `skills/export_cases/SKILL.md`
* 在 `src/types.py` 中加入：

  * `semantic_value`
  * `pattern_id`
  * `dedup_key`

## 第二批

* 在 `collect_cases` 增加 low-value filtering
* 在 `export_cases` 增加 dedup + pattern export
* 在 summary 中加入 low_value_cases / pattern_count

## 第三批

* 增加 commit-shard 级别的批处理入口
* 为 teams agent 预留 commit 级任务输入接口

---

如果你愿意，我下一条可以直接把这些**合并进 README 最终版文本**，变成一个完整收口版。
