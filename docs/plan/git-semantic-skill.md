下面继续，直接给你 **3 个 prompt 文件的最终正文**。
这版和前面的 README / SKILL.md 完全对齐，可以直接落到：

* `prompts/generate_commit_log.md`
* `prompts/generate_rules_invariants.md`
* `prompts/generate_issue_text.md`

---

# prompts/generate_commit_log.md

````md
# Generate Commit Log

You are given one `semantic_case` extracted from repository history.

Your task is to produce a compact `commit_log` that describes the main code-change action of this case.

You are not writing an issue sentence.
You are not writing rules or invariants.
You are not writing a long explanation.
You must output YAML only.

---

## Goal

Given one `semantic_case`, generate:

- `commit_log`

This field is the code-change-oriented business expression of the case.

---

## What `commit_log` means

`commit_log` answers:

- what was changed in code
- what main object/path/logic was affected
- what main implementation action happened

It should stay close to the actual code change, but be more semantic than raw diff text.

It is the main code-change summary for this `semantic_case`.

---

## What `commit_log` is NOT

It is NOT:

- an issue sentence
- a requirement title
- a rule list
- an invariant list
- a long explanation
- a why-analysis

Do NOT write things like:

- feat：新增...
- bugfix：修复...
- refactor：重构...
- migration：迁移...
- optimize：优化...

Those belong to `issue_text`, not `commit_log`.

Do NOT include constraint-style statements such as:

- ensure compatibility
- keep output unchanged
- preserve existing behavior

Those belong to `rules` or `invariants`, not `commit_log`.

---

## Core constraints

### 1. Describe the main code change only
Focus on the primary change action of the `semantic_case`.

### 2. Supporting changes are subordinate
Tests, config, flags, wiring, registration, cleanup, and similar auxiliary changes are usually supporting attributes, not the primary subject.

You may mention them only when they are clearly attached to the main change, for example:

- 并更新对应回归测试
- 并补充相关配置接入
- 并整理配套注册逻辑

### 3. Keep it auditable back to the diff
The wording should be traceable to the provided files and diff summaries.

### 4. Keep it compact
- Prefer 1 sentence
- At most 2 short sentences
- No prose

### 5. Use concrete change verbs
Good verbs include:

- 补充…
- 新增…
- 调整…
- 重构…
- 迁移…
- 修正…
- 整理…

---

## Good examples

- 在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。
- 在 discovery 抽象下新增 Redis backend 注册与接入逻辑。
- 调整 qserver 请求转换逻辑，减少重复处理开销。
- 重构 operator registry 的内部组织，整理注册路径。
- 将旧配置解析路径迁移到新配置结构，并保留兼容读取路径。

---

## Bad examples

- bugfix：修复旧DSL写法边界检查
- 修复兼容问题，确保历史输入仍可正确解析
- feat：新增Redis节点来源接入能力
- 优化性能并保持输出一致
- 修复问题并提升稳定性

Why bad:
- issue-style output
- mixes constraints into change summary
- too requirement-like
- too abstract

---

## Input

You will receive YAML like this:

```yaml
case_id: ...
commit_id: ...
module: ...
files: [...]
diff_chunks: [...]
related_tests: [...]
bugfix_evidence:
  weak: [...]
  medium: [...]
  strong: [...]
split_hints:
  ...
````

Only infer from the provided case.
Do not assume hidden context.

---

## Output format

You must output YAML only:

```yaml
commit_log: >
  ...
```

---

## Final reminder

Your job is only to answer:

> what code-change action happened in this semantic_case

Do not output anything else.

````

---

# prompts/generate_rules_invariants.md

```md
# Generate Rules and Invariants

You are given one `semantic_case` and its `commit_log`.

Your task is to extract:

- `rules`
- `invariants`

You are not rewriting the commit log.
You are not writing an issue sentence.
You are not writing general coding advice.
You must output YAML only.

---

## Goal

Given one `semantic_case`, identify the object-specific semantic constraints and preserved semantic properties of the modified object.

You must output:

- `rules`
- `invariants`

---

## What `rules` mean

`rules` are the object-specific semantic constraints that must be respected while modifying this logic.

They may include:

- business logic constraints
- subsystem contract constraints
- concurrency/resource bounds
- request-response alignment constraints
- data mapping constraints
- compatibility or migration boundaries

A valid `rule` must be strongly related to the modified object of this `semantic_case`.

---

## What `invariants` mean

`invariants` are the object-specific semantic properties that must remain true after the change.

They may include:

- preserved alignment relations
- preserved external behavior relations
- preserved historical compatibility semantics
- preserved subsystem-level semantic stability properties

A valid `invariant` must be strongly related to the modified object of this `semantic_case`.

---

## Core principle

`commit_log` says:

> what was changed

`rules / invariants` say:

> around this modified object, what semantic constraints must not be broken, and what semantic properties must still hold

They are not generic engineering hygiene.

---

## Important exclusion

Do NOT output generic coding advice or development hygiene, such as:

- null checks
- bounds checks
- exception handling
- input validation
- avoiding crashes
- generic thread-safety advice
- code style guidance
- defensive programming clichés

These are NOT valid `rules` or `invariants` for this task.

If you cannot infer stable object-specific semantic constraints, prefer empty arrays.

---

## Core constraints

### 1. Do NOT repeat the commit log
Do not restate what was changed.

### 2. Must be object-specific
The rule or invariant must be tightly tied to the modified object/path/subsystem of this case.

### 3. Must be semantically meaningful
It should reflect a real logic contract, semantic boundary, alignment property, compatibility requirement, concurrency bound, or system-level relation.

### 4. Avoid duplication
Do not write near-identical meanings in both `rules` and `invariants`.

### 5. Empty is allowed
If the case does not support a stable high-value result, output empty arrays.

---

## Good examples

### Example 1: parser compatibility

```yaml
rules:
  - legacy syntax compatibility must be preserved during repair

invariants:
  - historical inputs remain parseable
````

### Example 2: qserver request-response alignment

```yaml
rules:
  - request item filtering must preserve score response alignment

invariants:
  - returned scored items remain aligned with effective request items
```

### Example 3: feature extraction concurrency control

```yaml
rules:
  - feature extraction worker count must remain under configured concurrency bound

invariants:
  - extraction concurrency remains bounded by the current scheduling model
```

### Example 4: discovery backend integration

```yaml
rules:
  - new backend integration must preserve current discovery abstraction contract

invariants:
  - existing discovery behavior remains stable
```

### Example 5: config migration

```yaml
rules:
  - legacy config path must remain readable during transition

invariants:
  - existing config behavior remains available
```

---

## Bad examples

```yaml
rules:
  - check null pointer
  - avoid out of bounds

invariants:
  - system does not crash
```

```yaml
rules:
  - fix parser logic

invariants:
  - parser logic is fixed
```

Why bad:

* generic engineering hygiene
* repeats the code action
* not object-specific semantic constraints

---

## Input

You will receive YAML like this:

```yaml
case_id: ...
commit_id: ...
module: ...

commit_log: ...

files: [...]
diff_chunks: [...]
related_tests: [...]

bugfix_evidence:
  weak: [...]
  medium: [...]
  strong: [...]
```

Only infer from the provided case and `commit_log`.
Do not invent missing semantics.

---

## Output format

You must output YAML only:

```yaml
rules: []
invariants: []
```

---

## Final reminder

Only output object-specific semantic constraints and preserved properties.

Do not output generic coding guidance.
Do not repeat the change action.
Prefer empty arrays over vague filler.

````

---

# prompts/generate_issue_text.md

```md
# Generate Issue Text

You are given one `semantic_case`, represented by:

- `commit_log`
- `rules`
- `invariants`
- bugfix evidence
- split hints

Your task is to produce:

- `issue_text`
- `development_type`
- `split_suggestion`

You are not writing a long explanation.
You must output YAML only.

---

## Goal

Compress the main semantic intent of this `semantic_case` into a short requirement-style issue sentence.

At the same time:

- classify its `development_type`
- decide whether this compression overflows and therefore requires split

---

## What `issue_text` means

`issue_text` is the compressed requirement-style summary of the main semantic intent of the case.

It should be:

- short
- single-sentence
- single-subject
- requirement-oriented

It should summarize the semantic_case, mainly based on:

- `commit_log`
- `rules`
- `invariants`
- bugfix evidence

---

## What `issue_text` must NOT do

Do NOT:

- include rules or invariants directly
- include hidden constraints
- include a second clause such as:
  - 并保持…
  - 并确保…
  - 在…前提下…
- become vague or generic
- turn into a long explanation

Bad:

- bugfix：修复旧DSL写法边界检查，并确保历史输入仍可正确解析
- feat：新增Redis节点来源接入能力，并保持已有discovery行为不变
- optimize：优化请求转换逻辑，在保持输出语义一致的前提下降低CPU消耗

The second clause belongs to `rules` or `invariants`, not to `issue_text`.

---

## Prefix requirements

`issue_text` must start with exactly one of:

- feat：
- bugfix：
- refactor：
- migration：
- optimize：

---

## development_type

`development_type` must be exactly one of:

- feature
- bugfix
- refactor
- migration
- optimize

It must match the prefix of `issue_text`.

---

## split logic

`split_suggestion` is NOT a prior guess.
It is the result of compression overflow.

Use this rule:

- if the case can be naturally compressed into one short, single-subject `issue_text`, then `needs_split: false`
- if compression would require multiple independent main changes, or would collapse into an overly generic sentence, then `needs_split: true`

Typical overflow cases:

- multiple independent main actions must be expressed together
- one short sentence would become misleadingly generic
- conflicting main development types coexist in the same semantic case

Supporting attributes such as tests, config, flags, wiring, registration, and cleanup usually do NOT cause overflow by themselves.

---

## Bugfix guidance

Bugfix is a high-priority interpretation direction, but it is NOT determined by a single low-level code pattern.

For example:
- branch modification alone is NOT a strong bugfix signal

Use bugfix when the overall evidence supports correctness repair, such as:

- regression tests for broken behavior
- restoration of old behavior
- compatibility repair
- boundary correction
- semantic stability preservation

---

## Good examples

### Example 1

```yaml
issue_text: >
  bugfix：修复旧DSL写法边界检查

development_type: bugfix

split_suggestion:
  needs_split: false
  split_reasons: []
````

### Example 2

```yaml
issue_text: >
  feat：新增Redis节点来源接入能力

development_type: feature

split_suggestion:
  needs_split: false
  split_reasons: []
```

### Example 3

```yaml
issue_text: >
  refactor：重构算子注册结构

development_type: refactor

split_suggestion:
  needs_split: false
  split_reasons: []
```

### Example 4

```yaml
issue_text: >
  optimize：优化qserver请求转换逻辑

development_type: optimize

split_suggestion:
  needs_split: false
  split_reasons: []
```

---

## Bad examples

### Bad 1

```yaml
issue_text: >
  bugfix：修复旧DSL写法边界检查，并确保历史输入仍可正确解析
```

### Bad 2

```yaml
issue_text: >
  feat：新增Redis节点来源接入能力，并保持已有discovery行为不变
```

### Bad 3

```yaml
issue_text: >
  refactor：重构多个模块逻辑
```

Why bad:

* mixes constraints into issue_text
* too broad
* loses the main subject
* becomes generic compression

---

## Input

You will receive YAML like this:

```yaml
case_id: ...
commit_id: ...
module: ...

commit_log: ...

rules: []
invariants: []

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

Only infer from the provided case.
Do not invent hidden context.

---

## Output format

You must output YAML only:

```yaml
issue_text: >
  ...

development_type: ...

split_suggestion:
  needs_split: false
  split_reasons: []
```

---

## Final reminder

Your job is to produce one short issue sentence for one semantic_case.

If that compression cannot be done cleanly, mark `needs_split: true`.

```
```
