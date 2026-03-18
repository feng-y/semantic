下面直接给你 README.md 最终版 + 3 个 SKILL.md 最终版。
这版可以直接交给 Claude Code 开始实现。

⸻

README.md（最终版）

# 历史代码变更语义抽取系统

## 目标

从仓库历史 commit 中提炼出可独立成立的主语义包，并为每个主语义包生成结构化语义样本，用于：

- 需求理解
- case 检索
- few-shot 样本沉淀
- 经验规则沉淀
- 离线训练数据构造

最终每个有效样本输出：

- `commit_log`
- `rules`
- `invariants`
- `issue_text`
- `development_type`
- `split_suggestion`

---

## 核心原则

### 1. commit 不是 issue 单位

不要假设：

- 一个 commit 对应一个 issue_text
- 一个 commit 对应一个 commit_log

commit 只是原始代码变更容器，不是需求单位。

---

### 2. 小改动块也不是 issue 单位

不要把每个细粒度改动块都直接产出：

- 一个 `commit_log`
- 一个 `issue_text`

否则会导致样本碎裂，测试、配置、开关等配套动作被误识别为独立需求。

---

### 3. 真正单位是 semantic_case

真正的处理单位是：

**semantic_case = 可独立成立的主语义包**

一个 `semantic_case` 对应：

- 一个 `commit_log`
- 一个 `issue_text`

---

### 4. 测试、配置、开关默认是附带属性

以下内容默认不是主语义主体：

- tests
- config
- flags
- wiring
- registration
- import/include 调整
- 小型 cleanup
- 文案同步
- 兼容接线

它们默认挂靠主改动动作，不单独形成 `issue_text`。

---

### 5. split 是 issue_text 压缩溢出的结果

`split_suggestion` 不是先验判断，而是：

> 在尝试把当前 `semantic_case` 压缩成一个短的、单主体的 `issue_text` 时，如果发生语义溢出，则触发 split

---

### 6. bugfix 是组合证据判断

bugfix 是高优先级解释方向，但不是单个代码模式判断。

例如：

- 修改分支
- 拆细条件
- 调整 fallback 路径

这些本身都不是强 bugfix 信号。

正确做法是综合判断：

- `commit_log`
- `rules / invariants`
- regression / restore / compatibility repair 等证据

---

### 7. prompt 只定义问题，不替模型写死思考过程

prompt 只提供：

- 字段定义
- 输入边界
- 输出结构
- 正例
- 反例
- 约束

prompt 不负责替 Claude Code 写死内部推理脚本。

---

## 核心概念

### commit
原始提交容器，仅用于扫描输入。

### change_group
细粒度改动组，是中间分析单元，不直接生成 `issue_text`。

### semantic_case
真正的语义抽取单位，定义为：

> 一组能够共同表达一个主语义，并且可以稳定压缩为一个短 `issue_text` 的改动包

### commit_log
当前 `semantic_case` 的代码修改主动作。回答：

> 这次改了什么

### rules
围绕当前修改对象，在该子系统/场景下必须遵守的对象语义约束。

这些约束可以是：

- 业务语义约束
- 子系统契约约束
- 并发/资源边界约束
- 请求-响应对齐约束
- 数据映射约束
- 兼容/迁移边界约束

### invariants
围绕当前修改对象，改动完成后仍必须保持成立的对象语义性质。

### issue_text
当前 `semantic_case` 主语义的压缩需求句。

### development_type
对 `issue_text` 的类型归类，固定为：

- `feature`
- `bugfix`
- `refactor`
- `migration`
- `optimize`

### split_suggestion
表示当前 `semantic_case` 在 `issue_text` 压缩时是否溢出。

---

## 系统架构

系统只保留 3 个 skill：

- `collect_cases`
- `generate_case_semantics`
- `export_cases`

---

## 总体流程

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


⸻

目录结构

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


⸻

数据结构

RawCommit

commit_id: ...
author: ...
timestamp: ...
files: []
diff_chunks: []
related_tests: []

ChangeGroup

group_id: ...
theme: ...
files: []
role: primary|secondary|supporting

SemanticCaseInput

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

SemanticCaseOutput

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


⸻

collect_cases 规则

change_group 规则
    •   同对象优先归一组
    •   主逻辑 + 测试归一组
    •   config / flag / wiring / registration 默认挂主组
    •   cleanup 默认挂主组
    •   只有独立主动作才新开组

semantic_case 规则

以下改动共同服务一个主意图时，应合并：
    •   主逻辑
    •   回归测试
    •   config 接入
    •   feature flag
    •   wiring / registration
    •   小型 cleanup
    •   相关文案同步

出现多个独立主动作时不合并。

最终判断标准：

如果这些改动能够共同压缩成一个短的、单主体的 issue_text，就可以构成一个 semantic_case。

⸻

bugfix_evidence 规则

weak
    •   existing branch structure changed
    •   condition refinement / split
    •   fallback path touched
    •   compatibility path touched
    •   error-handling branch adjusted

medium
    •   boundary check added
    •   invalid input handling corrected
    •   legacy path repaired
    •   parser/config/runtime mismatch corrected
    •   historical compatibility case adjusted

strong
    •   regression tests added for broken behavior
    •   old behavior restored
    •   historical inputs explicitly kept parseable
    •   external behavior repaired rather than capability added

注意：

bugfix 是组合语义判断，不是单个代码模式判断。

⸻

generate_case_semantics 内部流程

内部使用 3 个 prompt：
    1.  generate_commit_log
    2.  generate_rules_invariants
    3.  generate_issue_text

Prompt 1：generate_commit_log

输出：
    •   commit_log

Prompt 2：generate_rules_invariants

输出：
    •   rules
    •   invariants

Prompt 3：generate_issue_text

输出：
    •   issue_text
    •   development_type
    •   split_suggestion

⸻

rules / invariants 的关键约束

rules / invariants 必须是围绕当前修改对象的语义约束与保持项。

允许：
    •   业务语义约束
    •   子系统契约约束
    •   并发/资源边界约束
    •   请求-响应对齐约束
    •   数据映射约束
    •   兼容/迁移边界约束

禁止：
    •   null checks
    •   bounds checks
    •   exception handling
    •   input validation
    •   avoid crash
    •   generic thread-safety advice
    •   code style guidance

这些属于通用开发规范，不是有效的 rules / invariants。

⸻

issue_text 规则

issue_text 必须：
    •   单句
    •   短
    •   单主体
    •   不混规则和保持项
    •   不写第二分句

必须以前缀之一开头：
    •   feat：
    •   bugfix：
    •   refactor：
    •   migration：
    •   optimize：

development_type 必须与前缀一致。

⸻

split 规则

split_suggestion 是 issue_text 压缩溢出的结果。

不触发 split 的情况
    •   主逻辑 + 测试
    •   主逻辑 + config / flag / wiring
    •   主逻辑 + registration
    •   主逻辑 + cleanup

触发 split 的情况
    •   必须同时表达两个独立主动作
    •   只能退化成泛化空话
    •   同时混有多个主开发类型且都不是配套关系

最终标准：

如果当前 semantic_case 能自然压缩成一个短的、单主体的 issue_text，就不 split；压不住，就 split。

⸻

校验规则

结构校验

必须包含：
    •   case_id
    •   commit_id
    •   module
    •   commit_log
    •   issue_text
    •   development_type
    •   rules
    •   invariants
    •   split_suggestion

类型校验
    •   commit_log: string
    •   issue_text: string
    •   development_type: string
    •   rules: list[str]
    •   invariants: list[str]
    •   split_suggestion.needs_split: bool
    •   split_suggestion.split_reasons: list[str]

枚举校验

development_type 只能是：
    •   feature
    •   bugfix
    •   refactor
    •   migration
    •   optimize

一致性校验
    •   issue_text 前缀与 development_type 一致
    •   needs_split=false 时 split_reasons 为空
    •   commit_log 不得 requirement 化
    •   rules/invariants 不得与 commit_log 大量重复
    •   rules/invariants 不得退化为通用开发规范

⸻

三个 skill 的职责边界

collect_cases

负责：
    •   扫 git 历史
    •   抽 raw commits
    •   生成 change_group
    •   归并 semantic_case
    •   补 bugfix_evidence
    •   补 split_hints
    •   输出 semantic_case 输入

不负责：
    •   生成 commit_log
    •   生成 issue_text
    •   类型判断

generate_case_semantics

负责：
    •   调 3 个 prompt
    •   生成 commit_log
    •   生成 rules / invariants
    •   生成 issue_text / development_type / split_suggestion
    •   基础校验
    •   组装最终 YAML

不负责：
    •   git 扫描
    •   最终导出

export_cases

负责：
    •   YAML 落盘
    •   JSONL 汇总
    •   基础统计
    •   invalid bucket 导出

不负责：
    •   语义判断
    •   case 重修复

⸻

Claude Code 实施顺序

第一批先做
    •   src/types.py
    •   skills/collect_cases/run.py
    •   skills/generate_case_semantics/run.py
    •   skills/export_cases/run.py

第二批补齐
    •   src/grouping.py
    •   src/semantic_case_builder.py
    •   src/prompt_runner.py
    •   src/validators.py

第三批再补
    •   统计报表
    •   invalid case 分析
    •   抽样评估脚本

---

# skills/collect_cases/SKILL.md（最终版）

```md id="skill-collect-cases"
# collect_cases

## Purpose

从仓库历史 commit 中提取原始变更，构造细粒度 `change_group`，再归并为可独立成立的 `semantic_case`，并补充 bugfix 证据与 split hints。

## Input

- repo_path
- commit_range 或 commit_list
- 可选 path include/exclude
- 可选 author / time window

## Output

输出 `semantic_case` 输入数据：

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

Core Rules

1. commit 不是 issue 单位

不要把一个 commit 直接映射为一个 issue_text。

2. 小改动块不是 issue 单位

不要把每个细粒度改动块直接映射为一个 issue_text。

3. semantic_case 才是最终单位

只有能够共同压缩为一个短的、单主体 issue_text 的改动包，才能成为一个 semantic_case。

4. 测试 / 配置 / 开关默认是附带属性

它们默认挂靠主改动动作，不单独形成主体。

5. change_group 规则
    •   同对象优先归一组
    •   主逻辑 + 测试归一组
    •   config / flag / wiring / registration 默认挂主组
    •   cleanup 默认挂主组
    •   只有独立主动作才新开组

6. semantic_case 归并规则

若多个 change_group 能共同压缩成一个短的、单主体 issue_text，则合并；否则分开。

7. bugfix_evidence 是证据池，不是最终结论

这里只注入证据，不直接判定最终 development_type。

Non-goals

本 skill 不负责：
    •   生成 commit_log
    •   生成 rules
    •   生成 invariants
    •   生成 issue_text
    •   生成 development_type

Failure Handling
    •   无法抽取 diff 时，记录 invalid raw commit
    •   无法稳定归并 semantic_case 时，保守拆开而不是强行合并
    •   split_hints 只做提示，不做最终 split 结论

Example

Input

一个 commit，同时修改：
    •   parser 主逻辑
    •   对应回归测试

Output

一个 semantic_case，而不是两个独立 issue 单元。

---

# skills/generate_case_semantics/SKILL.md（最终版）

```md id="skill-generate-semantics"
# generate_case_semantics

## Purpose

对单个 `semantic_case` 生成最终语义样本：

- `commit_log`
- `rules`
- `invariants`
- `issue_text`
- `development_type`
- `split_suggestion`

## Input

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

Output

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

Internal Structure

内部固定使用 3 个 prompt：
    1.  generate_commit_log
    2.  generate_rules_invariants
    3.  generate_issue_text

Core Rules

1. commit_log

只表达“改了什么”，是代码修改主动作表达。

2. rules / invariants

必须是围绕当前修改对象的语义约束与保持项，不是通用开发规范。

3. issue_text

是主语义压缩句，必须短、单句、单主体。

4. development_type

只能是：
    •   feature
    •   bugfix
    •   refactor
    •   migration
    •   optimize

5. split_suggestion

是 issue_text 压缩溢出的结果，不是先验猜测。

6. bugfix 是组合证据判断

不得由单个代码模式直接下结论。

Validation

Required fields
    •   case_id
    •   commit_id
    •   module
    •   commit_log
    •   issue_text
    •   development_type
    •   rules
    •   invariants
    •   split_suggestion

Consistency checks
    •   issue_text 前缀与 development_type 一致
    •   needs_split=false 时 split_reasons 为空
    •   commit_log 不得 requirement 化
    •   rules/invariants 不得退化为通用开发规范

Non-goals

本 skill 不负责：
    •   git 扫描
    •   semantic_case 归并
    •   最终导出

Failure Handling
    •   YAML parse 失败：进入 invalid bucket
    •   development_type 非法：进入 invalid bucket
    •   issue_text 不合法：进入 invalid bucket
    •   rules/invariants 退化为通用开发规范：进入 invalid bucket

Example

commit_log

在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。

rules
    •   legacy syntax compatibility must be preserved during repair

invariants
    •   historical inputs remain parseable

issue_text

bugfix：修复旧DSL写法边界检查

---

# skills/export_cases/SKILL.md（最终版）

```md id="skill-export-cases"
# export_cases

## Purpose

将通过校验的 semantic case 落盘、汇总，并输出基础统计与 invalid bucket。

## Input

validated semantic cases:

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

Output
    •   单 case YAML 文件
    •   汇总 JSONL
    •   基础统计结果
    •   invalid bucket / error bucket

Core Rules

1. 只导出已校验 case

export 只接收 validated semantic cases。

2. 不在 export 阶段改语义

不得在 export 阶段重新改写：
    •   commit_log
    •   issue_text
    •   rules
    •   invariants
    •   development_type

3. 提供基础统计

至少输出：
    •   总 case 数
    •   validation pass rate
    •   development_type 分布
    •   bugfix 占比
    •   needs_split 占比
    •   invalid reason top-N

Non-goals

本 skill 不负责：
    •   语义生成
    •   case 修复
    •   prompt 调用

Failure Handling
    •   落盘失败：记录 error bucket
    •   JSONL 汇总失败：保留单文件 YAML，不阻断全部流程
    •   统计失败：不影响已有 case 文件输出

Example

Outputs
    •   data/semantic_cases/*.yaml
    •   data/exports/cases.jsonl
    •   data/exports/summary.json
    •   data/invalid_cases/*.yaml

---

这套已经可以直接交给 Claude Code 了。  
下一步最顺的是把 **3 个 prompt 文件正文** 也一起定稿。