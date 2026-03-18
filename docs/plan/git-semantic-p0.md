下面直接给你 “Claude Code 实施任务总说明 Prompt”。
这版是可以整段直接发给 Claude Code 的，目标就是：

按我们已经定好的边界，先把最小闭环实现出来
不扩散，不过度设计，不自作主张加新层

⸻

Claude Code 实施任务总说明 Prompt

你要实现一个“历史代码变更语义抽取系统”的最小可运行版本。

目标不是做通用平台，也不是做复杂 agent orchestration，而是完成一个稳定闭环：

- 从历史 commit 提取 semantic_case
- 为 semantic_case 生成结构化语义结果
- 对结果做导出、严格去重、高频模式归并

请严格按下面的约束实施，不要擅自扩大设计范围。

---

## 一、系统目标

系统从仓库历史 commit 中提炼出可独立成立的主语义包（semantic_case），并生成结构化语义样本，用于：

- 需求理解
- case 检索
- few-shot 样本沉淀
- 经验规则沉淀
- 离线训练数据构造

每个有效样本最终输出：

- `commit_log`
- `rules`
- `invariants`
- `issue_text`
- `development_type`
- `split_suggestion`

---

## 二、必须遵守的核心原则

### 1. commit 不是 issue 单位
不要假设一个 commit 对应一个 issue_text。

### 2. 小改动块也不是 issue 单位
不要把每个细粒度改动块都直接映射成 issue。

### 3. 真正单位是 semantic_case
`semantic_case` 是可独立成立的主语义包。  
一个 `semantic_case` 对应：
- 一个 `commit_log`
- 一个 `issue_text`

### 4. 测试、配置、开关默认是附带属性
这些默认挂靠主改动动作，不单独形成主体。

### 5. split 是 issue_text 压缩溢出的结果
不是先验判断。

### 6. bugfix 是组合证据判断
不能因为“修改分支”就直接判 bugfix。  
必须结合：
- `commit_log`
- `rules / invariants`
- regression / restore / compatibility repair 等证据

### 7. prompt 只定义问题，不替模型写死思考过程
prompt 只提供：
- 字段定义
- 输入边界
- 输出结构
- 正例
- 反例
- 约束

不要在 prompt 里写死思维链。

### 8. rules / invariants 不是通用开发规范
它们必须是围绕当前修改对象的对象语义约束与保持项。  
禁止退化为：
- null checks
- bounds checks
- exception handling
- input validation
- avoid crash
- generic thread-safety advice
- code style guidance

### 9. 系统不追求覆盖所有 commit
只追求沉淀高语义价值 case。  
低价值 case 进入 `low_value_cases/` 或直接丢弃。

### 10. teams agent 的粒度固定为一个 commit 一个 agent
不要在一个 commit 内再拆多个 agent。

---

## 三、系统外部只允许 3 个 skill

外部 skill 固定为：

- `collect_cases`
- `generate_case_semantics`
- `export_cases`

不要再新增额外 skill。

### 说明
- 外部一个 skill 完成一个完整任务
- skill 内部允许必要子步骤
- 但不要把内部子步骤再外扩成额外 skill

---

## 四、目录结构

请按下面结构实现：

```text
project/
├─ prompts/
│  ├─ generate_commit_log.md
│  ├─ generate_rules_invariants.md
│  └─ generate_issue_text.md
├─ skills/
│  ├─ collect_cases/
│  │  ├─ SKILL.md
│  │  └─ run.py
│  ├─ generate_case_semantics/
│  │  ├─ SKILL.md
│  │  └─ run.py
│  └─ export_cases/
│     ├─ SKILL.md
│     └─ run.py
├─ src/
│  ├─ types.py
│  ├─ git_utils.py
│  ├─ grouping.py
│  ├─ semantic_case_builder.py
│  ├─ prompt_runner.py
│  ├─ validators.py
│  ├─ normalize.py
│  ├─ dedup.py
│  ├─ patterning.py
│  └─ io_utils.py
├─ data/
│  ├─ raw_commits/
│  ├─ semantic_case_inputs/
│  ├─ semantic_cases/
│  ├─ low_value_cases/
│  ├─ invalid_cases/
│  └─ exports/
└─ README.md


⸻

五、各 skill 的职责

1. collect_cases

负责：
    •   扫 git 历史
    •   抽取 raw commits
    •   构造 change_group
    •   归并 semantic_case
    •   注入 bugfix_evidence
    •   注入 split_hints
    •   做 semantic_value 判断
    •   输出 semantic_case 输入

不负责：
    •   生成 commit_log
    •   生成 rules / invariants
    •   生成 issue_text
    •   最终去重 / 模式归并

⸻

2. generate_case_semantics

负责：
    •   调 3 个 prompt
    •   生成 commit_log
    •   生成 rules / invariants
    •   生成 issue_text / development_type / split_suggestion
    •   校验输出
    •   产出 semantic_cases
    •   失败样本进入 invalid_cases

不负责：
    •   git 扫描
    •   semantic_case 归并
    •   最终资产去重 / pattern merge

⸻

3. export_cases

负责：
    •   导出 valid cases
    •   严格去重
    •   高频模式归并
    •   选择 canonical cases / canonical patterns
    •   输出：
    •   cases.jsonl
    •   duplicates.jsonl
    •   patterns.jsonl
    •   summary.json

不负责：
    •   重写语义字段
    •   重新生成 case
    •   修改 prompt 输出

⸻

六、数据结构要求

至少实现这些结构：

RawCommit
    •   commit_id
    •   author
    •   timestamp
    •   files
    •   diff_chunks
    •   related_tests

SemanticCaseInput
    •   case_id
    •   commit_id
    •   module
    •   domain
    •   files
    •   diff_chunks
    •   related_tests
    •   bugfix_evidence
    •   split_hints
    •   semantic_value

SemanticCaseOutput
    •   case_id
    •   commit_id
    •   module
    •   domain
    •   commit_log
    •   issue_text
    •   development_type
    •   rules
    •   invariants
    •   split_suggestion
    •   semantic_value

Export-time structures
    •   CaseRecord
    •   DedupInput
    •   DedupGroup
    •   PatternInput
    •   PatternGroup
    •   PatternCheckResult
    •   ExportSummary

⸻

七、collect_cases 的实现要求

1. 输入

从 git_utils.load_commits_from_repo() 获取 raw commits。

2. change_group 规则
    •   同对象优先归一组
    •   主逻辑 + 测试归一组
    •   config / flag / wiring / registration 默认挂主组
    •   cleanup 默认挂主组
    •   只有独立主动作才新开组

3. semantic_case 规则
    •   能共同压缩成一个短的单主体 issue_text 的 group，合并为一个 semantic_case
    •   多个独立主动作时不合并

4. bugfix_evidence

只做证据注入，不做最终类型结论。
支持：
    •   weak
    •   medium
    •   strong

5. semantic_value

分为：
    •   high
    •   medium
    •   low

6. low_value_cases

低价值样本进入：
    •   data/low_value_cases/

典型低价值包括：
    •   format/lint/import/comment only
    •   trivial test maintenance
    •   trivial config/flag wiring only
    •   low-information parameter tweaks
    •   无法形成稳定主语义包的碎片修改

⸻

八、generate_case_semantics 的实现要求

内部固定使用 3 个 prompt：

Prompt 1：generate_commit_log

输出：
    •   commit_log

规则：
    •   只表达“改了什么”
    •   不写 issue 风格
    •   不写 rules/invariants
    •   不写 ensure / preserve 类约束语

Prompt 2：generate_rules_invariants

输出：
    •   rules
    •   invariants

规则：
    •   只提取围绕当前修改对象的对象语义约束与保持项
    •   允许为空
    •   禁止通用开发规范
    •   禁止同义重复

Prompt 3：generate_issue_text

输出：
    •   issue_text
    •   development_type
    •   split_suggestion

规则：
    •   issue_text 必须短、单句、单主体
    •   必须以前缀之一开头：
    •   feat：
    •   bugfix：
    •   refactor：
    •   migration：
    •   optimize：
    •   development_type 必须与前缀一致
    •   split 是压缩溢出的结果

⸻

九、validators 的实现要求

至少校验：

1. development_type 合法

只允许：
    •   feature
    •   bugfix
    •   refactor
    •   migration
    •   optimize

2. issue_text 前缀合法

必须与 development_type 一致。

3. split 一致性

needs_split=false 时，split_reasons 必须为空。

4. commit_log 不得 requirement 化

不能以：
    •   feat：
    •   bugfix：
    •   refactor：
    •   migration：
    •   optimize：

开头。

5. rules / invariants 不得退化为通用开发规范

如：
    •   null checks
    •   bounds checks
    •   exception handling
    •   input validation
    •   avoid crash
    •   thread-safe advice
    •   code style guidance

⸻

十、export_cases 的实现要求

1. export 阶段才做最终去重与归并

不要放到 prompt。
不要靠 cache 代替。

⸻

2. 严格去重（strict dedup）

目标：
    •   完全重复
    •   模板化重复
    •   轻微文案差异重复

第一版严格去重主键：

module + development_type + normalized_issue_text

注意：
    •   不要默认把 commit_log 放进 strict dedup 主键
    •   commit_log 更适合做人审阅和 canonical 展示

输出：
    •   duplicates.jsonl

⸻

3. 高频模式归并（pattern aggregation）

目标：
    •   把不完全相同但属于同一需求模式的 case 归并成少量高内聚 patterns

pattern_fingerprint 第一版：

domain + development_type + action_class + object_class + constraint_class

不要直接用 commit_log 原文做 fingerprint。

⸻

4. pattern 数量约束

单业务域 pattern 数量应高度内聚：
    •   < 10：优秀
    •   10 ~ 20：可接受
    •   > 20：需报警
    •   > 30：默认认为归并策略失效或抽象粒度过细

如果 pattern 数过高，在 summary.json 中输出报警。

⸻

5. 桶内相似度策略

第一版只实现：
    •   token Jaccard
    •   difflib.SequenceMatcher

不要先实现全量模型复核。

灰区模型复核作为 v2 预留。

⸻

6. canonical pattern 选择

优先保留：
    •   issue_text 最抽象但不空泛
    •   rules/invariants 最稳定
    •   不依赖具体数值和具体对象名
    •   最能代表共同模式的 case

⸻

7. 最终导出

必须输出：
    •   data/exports/cases.jsonl
    •   data/exports/duplicates.jsonl
    •   data/exports/patterns.jsonl
    •   data/exports/summary.json

⸻

十一、缓存要求

prompt runner 可以做缓存，但缓存只负责：
    •   相同输入不要重复生成
    •   加快重跑
    •   降低生成成本

缓存不负责最终去重。

⸻

十二、实现顺序要求

按下面顺序实现，不要跳：

第一批
    •   src/types.py
    •   src/io_utils.py
    •   src/normalize.py
    •   src/dedup.py
    •   src/patterning.py

第二批
    •   skills/export_cases/run.py

第三批
    •   src/grouping.py
    •   src/semantic_case_builder.py
    •   skills/collect_cases/run.py

第四批
    •   src/prompt_runner.py
    •   src/validators.py
    •   skills/generate_case_semantics/run.py

⸻

十三、第一版明确不做的事情

第一版不要实现：
    •   全量模型复核
    •   embedding 检索
    •   复杂多 agent orchestration
    •   一个 commit 内多 agent
    •   复杂聚类算法
    •   自动修复 invalid cases
    •   可视化前端

先把最小闭环跑通。

⸻

十四、最小闭环验收标准

跑完后至少应该能稳定产出：
    •   data/semantic_case_inputs/*.yaml
    •   data/semantic_cases/*.yaml
    •   data/low_value_cases/*.yaml
    •   data/invalid_cases/*.yaml
    •   data/exports/cases.jsonl
    •   data/exports/duplicates.jsonl
    •   data/exports/patterns.jsonl
    •   data/exports/summary.json

并且：
    1.  issue_text / development_type 一致
    2.  rules / invariants 不退化为通用开发规范
    3.  strict dedup 可工作
    4.  pattern aggregation 可工作
    5.  单业务域 pattern_count 能统计并报警

⸻

十五、最终一句话目标

构建一个最小可运行的历史代码变更语义抽取系统，
先把 semantic_case 抽出来，再生成稳定语义结果，最后在 export 阶段做严格去重与高频模式归并，输出高内聚、低噪声的 case 库和 pattern 库。

---

这个版本已经可以直接发给 Claude Code 了。  
如果你想更稳一点，我建议你把它和前面那 3 个 prompt 文件一起给它。