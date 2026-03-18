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
```

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
