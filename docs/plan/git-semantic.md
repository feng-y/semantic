下面给你一版 **Claude Code 可直接实施的完整方案文档**。
它已经吸收了前面收敛后的关键结论：

* 不做过度复杂拆分
* 系统只有 3 个 skill
* `semantic_case` 才是最终语义单位
* `commit_log` 表达“改了什么”
* `rules / invariants` 表达“围绕修改对象的语义约束与保持项”
* `issue_text` 是压缩结果
* `split` 是 `issue_text` 压缩溢出的结果
* 测试 / 配置 / 开关默认是附带属性
* bugfix 是组合证据判断，不是单模式判断
* prompt 只提供定义、样本、约束、结构，不替 Claude Code 写死思考过程

---

# 历史代码变更语义抽取系统实施方案

## 1. 目标

从仓库历史 commit 中提炼出可独立成立的**主语义包**，并为每个主语义包生成结构化语义样本，用于：

* 需求理解
* case 检索
* few-shot 样本沉淀
* 经验规则沉淀
* 离线训练数据构造

系统对每个有效语义单元最终输出：

* `commit_log`
* `rules`
* `invariants`
* `issue_text`
* `development_type`
* `split_suggestion`

---

## 2. 核心原则

### 2.1 一个 commit 不等于一个 issue

commit 只是原始代码变更容器，不是需求单位。
一个 commit 可能包含多个独立主语义，也可能混有大量附带修改，因此不能直接压成一个 `issue_text`。

### 2.2 一个小改动块也不等于一个 issue

不能把每个细粒度改动块都变成一个 `issue_text`。
否则会导致样本碎裂，测试、配置、开关等配套动作被误识别为独立需求。

### 2.3 真正单位是 semantic_case

真正的语义抽取单位是：

> **semantic_case = 可独立成立的主语义包**

一个 `semantic_case` 对应：

* 一个 `commit_log`
* 一个 `issue_text`

### 2.4 测试、配置、开关默认是附带属性

以下内容默认不构成主语义主体：

* tests
* config
* flags
* wiring
* registration
* import/include 调整
* 小型 cleanup
* 文案同步
* 兼容接线

它们默认挂靠主改动动作，不单独形成 `issue_text`。

### 2.5 split 是 issue_text 压缩溢出的结果

`split_suggestion` 不是先验判断，而是：

> 尝试把当前 `semantic_case` 压成一个短的、单主体的 `issue_text` 时，如果发生语义溢出，则触发 split

### 2.6 bugfix 是高优先级解释方向，但不是单模式判断

“修改分支”“拆细条件”本身都不是强 bugfix 信号。
bugfix 必须结合：

* `commit_log`
* `rules / invariants`
* regression / restore / compatibility repair 等证据

共同判断。

### 2.7 prompt 只定义问题，不替模型写死思考过程

prompt 只提供：

* 字段定义
* 输入边界
* 输出结构
* 正例
* 反例
* 约束

prompt 不负责替 Claude Code 编写内部推理脚本。

---

## 3. 核心概念

### 3.1 commit

原始提交容器，仅用于扫描输入。

### 3.2 change_group

细粒度改动组，是中间分析单元，不直接生成 `issue_text`。

例如：

* 主逻辑块
* 测试块
* 配置块
* wiring/registration 块
* cleanup 块

### 3.3 semantic_case

真正的语义抽取单位，定义为：

> 一组能够共同表达一个主语义，并且可以稳定压缩为一个短 `issue_text` 的改动包

### 3.4 commit_log

`commit_log` 表示：

> 当前 `semantic_case` 的代码修改主动作

回答：

> 这次改了什么

它是对修改内容的业务/功能表达，不是需求句，不是约束句。

### 3.5 rules

`rules` 表示：

> 围绕当前修改对象，在该子系统/场景下必须遵守的对象语义约束

它们可以是：

* 业务语义约束
* 子系统契约约束
* 并发/资源边界约束
* 请求-响应对齐约束
* 数据映射约束
* 兼容/迁移边界约束

它们必须与当前修改对象强相关。

### 3.6 invariants

`invariants` 表示：

> 围绕当前修改对象，改动完成后仍必须保持成立的对象语义性质

例如：

* 外部行为关系仍成立
* 请求与返回的对齐关系仍成立
* 历史兼容语义仍有效
* 子系统关键性质仍保持

### 3.7 issue_text

`issue_text` 表示：

> 当前 `semantic_case` 主语义的压缩需求句

它主要基于：

* `commit_log`
* `rules`
* `invariants`
* bugfix 证据

共同压缩而来。

要求：

* 单句
* 短
* 单主体
* 不混隐藏约束
* 不写第二分句

### 3.8 development_type

对 `issue_text` 的类型归类，固定为：

* `feature`
* `bugfix`
* `refactor`
* `migration`
* `optimize`

### 3.9 split_suggestion

表示当前 `semantic_case` 在 `issue_text` 压缩时是否溢出。

---

## 4. 系统架构

系统只保留 3 个 skill。

### Skill 1：collect_cases

负责：

* 扫描 git 历史
* 提取原始提交变更
* 构造 `change_group`
* 归并成 `semantic_case`
* 注入 bugfix 证据
* 注入 split hints
* 输出 `semantic_case` 输入数据

### Skill 2：generate_case_semantics

负责：

* 对单个 `semantic_case` 生成：

  * `commit_log`
  * `rules`
  * `invariants`
  * `issue_text`
  * `development_type`
  * `split_suggestion`
* 做基础校验
* 组装最终 YAML

这个 skill 内部使用 3 个 prompt，不用一个大 prompt。

### Skill 3：export_cases

负责：

* 落盘最终 case
* 汇总 JSONL
* 输出基础统计
* 输出 invalid bucket / error bucket

---

## 5. 总体流程

```text
Git commits
  ↓
collect_cases
  ↓
semantic_case inputs
  ↓
generate_case_semantics
  ↓
validated semantic cases
  ↓
export_cases
  ↓
case library + stats
```

---

## 6. 目录结构

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
│  └─ io_utils.py
├─ data/
│  ├─ raw_commits/
│  ├─ grouped_changes/
│  ├─ semantic_case_inputs/
│  ├─ semantic_cases/
│  ├─ invalid_cases/
│  └─ exports/
└─ README.md
```

---

## 7. 数据结构

### 7.1 RawCommit

```yaml
commit_id: ...
author: ...
timestamp: ...
files: []
diff_chunks: []
related_tests: []
```

### 7.2 ChangeGroup

```yaml
group_id: ...
theme: ...
files: []
role: primary|secondary|supporting
```

### 7.3 SemanticCaseInput

```yaml
case_id: ...
commit_id: ...
module: ...
files: []
diff_chunks: []
related_tests: []

bugfix_evidence:
  weak: []
  medium: []
  strong: []

split_hints:
  too_many_files: false
  too_many_diff_themes: false
  mixed_feature_and_bugfix: false
  unrelated_objects_detected: false
```

### 7.4 SemanticCaseOutput

```yaml
case_id: ...
commit_id: ...
module: ...

commit_log: ...
issue_text: ...
development_type: ...

rules: []
invariants: []

split_suggestion:
  needs_split: false
  split_reasons: []
```

---

## 8. collect_cases 设计

### 8.1 输入

* repo_path
* commit_range 或 commit_list
* 可选 path include/exclude
* 可选 author / time window

### 8.2 输出

输出 `semantic_case` 输入 YAML。

示例：

```yaml
case_id: 0545e881-parser-01
commit_id: 0545e881
module: parser

files:
  - parser/legacy_parser.cpp
  - parser/legacy_parser_test.cpp

diff_chunks:
  - file: parser/legacy_parser.cpp
    summary: modified legacy parsing boundary handling
  - file: parser/legacy_parser_test.cpp
    summary: added regression tests for historical syntax cases

related_tests:
  - parser/legacy_parser_test.cpp

bugfix_evidence:
  weak:
    - legacy path touched
  medium:
    - boundary check added
  strong:
    - regression test added for historical broken case

split_hints:
  too_many_files: false
  too_many_diff_themes: false
  mixed_feature_and_bugfix: false
  unrelated_objects_detected: false
```

### 8.3 内部步骤

#### Step 1：扫描 git 历史

抽取：

* commit_id
* changed files
* diff chunks
* related tests

#### Step 2：构造 change_group

把细粒度改动按轻规则分组。

#### Step 3：归并 semantic_case

把能够共同表达一个主语义的 `change_group` 合成 `semantic_case`。

#### Step 4：注入 bugfix_evidence

这里是证据池，不是“强信号列表”。

#### Step 5：注入 split_hints

只是提示，不是最终结论。

---

## 9. change_group 和 semantic_case 规则

### 9.1 change_group 规则

只做轻量主语义分组，不做复杂聚类。

#### 规则 A：同对象优先归一组

例如：

* `legacy_parser.cpp`
* `legacy_parser.h`
* `legacy_parser_test.cpp`

#### 规则 B：主逻辑 + 测试归一组

测试默认挂靠主逻辑。

#### 规则 C：config / flag / wiring / registration 默认挂主组

默认作为附带属性。

#### 规则 D：cleanup 默认挂主组

小型整理默认不独立升格。

#### 规则 E：只有独立主动作才新开组

例如：

* 修 parser legacy 边界检查
* 重构 operator registry

这是两个组。

### 9.2 semantic_case 规则

#### 应合并为一个 semantic_case 的情况

以下改动共同服务一个主意图，应合并：

* 主逻辑
* 回归测试
* config 接入
* feature flag
* wiring / registration
* 小型 cleanup
* 相关文案同步

#### 不应合并的情况

出现多个独立主动作时不合并。

例如：

* 一个 bugfix
* 一个独立 refactor

#### 最终判断标准

> 如果这些改动能够共同压缩成一个短的、单主体的 `issue_text`，就可以构成一个 `semantic_case`。

---

## 10. bugfix 证据设计

### 10.1 定位

bugfix 是高优先级解释方向，但不应由单一低层代码动作直接判定。

### 10.2 证据分层

#### weak

只能作为提示，不能单独判 bugfix：

* existing branch structure changed
* condition refinement / split
* fallback path touched
* compatibility path touched
* error-handling branch adjusted

#### medium

偏向 correctness repair，但仍需结合语义：

* boundary check added
* invalid input handling corrected
* legacy path repaired
* parser/config/runtime mismatch corrected
* historical compatibility case adjusted

#### strong

明显提高 bugfix 置信度：

* regression tests added for broken behavior
* old behavior restored
* historical inputs explicitly kept parseable
* external behavior repaired rather than capability added

### 10.3 判断原则

> bugfix 是组合语义判断，不是单个代码模式判断。

最终判断应结合：

* `commit_log`
* `rules / invariants`
* `bugfix_evidence`

共同完成。

---

## 11. generate_case_semantics 设计

内部使用 3 个 prompt。

### Prompt 1：generate_commit_log

产出：

* `commit_log`

### Prompt 2：generate_rules_invariants

产出：

* `rules`
* `invariants`

### Prompt 3：generate_issue_text

产出：

* `issue_text`
* `development_type`
* `split_suggestion`

---

## 12. prompt 设计总原则

每个 prompt 只负责定义：

* 字段是什么
* 输入边界是什么
* 输出结构是什么
* 什么是正例
* 什么是反例
* 什么约束必须遵守

每个 prompt 不负责：

* 替 Claude Code 写死内部推理链
* 规定严格的“先想什么后想什么”
* 脚本化模型思考过程

---

## 13. Prompt 1：generate_commit_log

### 描述

用于从一个 `semantic_case` 中提取：

> 代码修改的主业务动作表达

### 功能

只回答：

> 这次改了什么

### 关键约束

* 只表达“改了什么”
* 测试 / 配置 / 开关默认是附带属性
* 不写需求句
* 不写 rules/invariants
* 不写 ensure / preserve 等约束语
* 1~2 句，尽量 1 句

### 结构化输出

```yaml
commit_log: >
  ...
```

### 正例

* 在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。
* 在 discovery 抽象下新增 Redis backend 注册与接入逻辑。
* 调整 qserver 请求转换逻辑，减少重复处理开销。

### 反例

* bugfix：修复旧DSL写法边界检查
* 修复兼容问题，确保历史输入仍可正确解析

---

## 14. Prompt 2：generate_rules_invariants

### 描述

用于提取围绕当前修改对象的：

* 对象语义约束
* 对象语义保持项

### 功能

只回答：

> 围绕当前修改对象，在该场景下有哪些对象语义约束必须遵守，以及哪些对象语义性质必须保持成立

### 关键约束

* 不重复 `commit_log`
* 必须是对象语义约束 / 对象语义保持项
* 允许为空
* 禁止通用开发规范
* 禁止同义重复

### 明确排除项

以下都不允许进入 `rules / invariants`：

* null checks
* bounds checks
* exception handling
* input validation
* avoid crash
* generic thread-safety advice
* code style guidance

### 结构化输出

```yaml
rules: []
invariants: []
```

### 正例 1：parser 兼容场景

```yaml
rules:
  - legacy syntax compatibility must be preserved during repair

invariants:
  - historical inputs remain parseable
```

### 正例 2：qserver 请求-返回对齐场景

```yaml
rules:
  - request item filtering must preserve score response alignment

invariants:
  - returned scored items remain aligned with effective request items
```

### 正例 3：特征抽取并发控制场景

```yaml
rules:
  - feature extraction worker count must remain under configured concurrency bound

invariants:
  - extraction concurrency remains bounded by the current scheduling model
```

### 反例

```yaml
rules:
  - check null pointer
  - avoid out of bounds

invariants:
  - system does not crash
```

---

## 15. Prompt 3：generate_issue_text

### 描述

用于对当前 `semantic_case` 做最终压缩，生成：

* `issue_text`
* `development_type`
* `split_suggestion`

### 功能

只回答：

> 将当前 semantic_case 压缩为一个短的单主体需求句，并做类型归类；若无法压缩，则触发 split

### 关键约束

* `issue_text` 必须短、单句、单主体
* 必须以前缀之一开头：

  * `feat：`
  * `bugfix：`
  * `refactor：`
  * `migration：`
  * `optimize：`
* 不混 rules/invariants
* 不写第二分句
* `development_type` 必须与前缀一致
* split 是压缩溢出的结果
* bugfix 是高优先级解释方向，但不是单模式判断
* 测试 / 配置 / 开关默认不是主体

### 结构化输出

```yaml
issue_text: >
  ...

development_type: ...

split_suggestion:
  needs_split: false
  split_reasons: []
```

### 正例

```yaml
issue_text: >
  bugfix：修复旧DSL写法边界检查

development_type: bugfix

split_suggestion:
  needs_split: false
  split_reasons: []
```

### 反例

```yaml
issue_text: >
  bugfix：修复旧DSL写法边界检查，并确保历史输入仍可正确解析
```

---

## 16. 校验规则

### 16.1 结构校验

必须包含：

* case_id
* commit_id
* module
* commit_log
* issue_text
* development_type
* rules
* invariants
* split_suggestion

### 16.2 类型校验

* `commit_log`: string
* `issue_text`: string
* `development_type`: string
* `rules`: list[str]
* `invariants`: list[str]
* `split_suggestion.needs_split`: bool
* `split_suggestion.split_reasons`: list[str]

### 16.3 枚举校验

`development_type` 只能是：

* feature
* bugfix
* refactor
* migration
* optimize

### 16.4 issue_text 前缀校验

必须以之一开头：

* `feat：`
* `bugfix：`
* `refactor：`
* `migration：`
* `optimize：`

### 16.5 一致性校验

* `issue_text` 前缀与 `development_type` 一致
* `needs_split=false` 时 `split_reasons` 为空
* `commit_log` 不得 requirement 化
* `rules/invariants` 不得与 `commit_log` 大量重复
* `rules/invariants` 不得退化为通用开发规范

---

## 17. skill 职责边界

### collect_cases

负责：

* 扫 git 历史
* 抽 raw commits
* 生成 change_group
* 归并 semantic_case
* 补 bugfix_evidence
* 补 split_hints
* 输出 semantic_case 输入

不负责：

* 生成 commit_log
* 生成 issue_text
* 类型判断

### generate_case_semantics

负责：

* 调 3 个 prompt
* 生成 commit_log
* 生成 rules / invariants
* 生成 issue_text / development_type / split_suggestion
* 基础校验
* 组装最终 YAML

不负责：

* git 扫描
* 最终导出

### export_cases

负责：

* YAML 落盘
* JSONL 汇总
* 基础统计
* invalid bucket 导出

不负责：

* 语义判断
* case 重修复

---

## 18. Claude Code 实施顺序

### 第一批先做

* `src/types.py`
* `skills/collect_cases/run.py`
* `skills/generate_case_semantics/run.py`
* `skills/export_cases/run.py`

### 第二批补齐

* `src/grouping.py`
* `src/semantic_case_builder.py`
* `src/prompt_runner.py`
* `src/validators.py`

### 第三批再补

* 统计报表
* invalid case 分析
* 抽样评估脚本

---

## 19. 最终摘要

> 这套系统不把 commit 直接映射为 issue，也不把细粒度改动直接映射为 issue。
> 它先将历史代码改动组织为可独立成立的主语义包 `semantic_case`，再分别生成：
>
> * `commit_log`：改了什么
> * `rules / invariants`：围绕当前修改对象的语义约束与保持项
> * `issue_text`：压缩后的需求主体句
>   若压缩发生语义溢出，则触发 `split_suggestion`。
>   其中测试、配置、开关默认是附带属性，bugfix 采用组合证据判断，而不是单模式判断。
>   prompt 只定义问题、边界、样本和输出结构，不替 Claude Code 写死思考过程。

如果你愿意，我下一条直接给你整理成 **README.md 最终版**，或者 **3 个 SKILL.md 最终版**。
