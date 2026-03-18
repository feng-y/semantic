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
```

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
