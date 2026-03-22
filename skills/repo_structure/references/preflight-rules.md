下面给你 **`skills/repo-structure/references/preflight-rules.md` 初稿**。

这份要解决的是：

**`repo-structure` 在真正执行任何 stage 之前，什么必须检查，怎么分级，什么直接失败，什么只是 warning。**

你前面已经定了一个很关键的原则：

* 不做 skill 嵌 skill
* 不在 stage 内偷偷补跑上游
* 依赖通过 preflight 显式暴露
* 缺失 required input 就 fail-fast

这份文档就是把这个原则写成运行契约。

---

````markdown id="2x5t1m"
# Preflight Rules

This document defines the preflight contract for the `repo-structure` pipeline.

Preflight exists to answer one question before execution:

**Are the required dependencies, artifacts, tools, and repo state valid enough to run the requested command safely and reproducibly?**

Preflight is not optional bookkeeping.
It is part of the execution contract.

---

## 1. Core principle

A stage must consume validated upstream inputs.

It must not:

- silently create missing upstream artifacts
- implicitly invoke upstream skills or pipelines
- continue after required-input failure
- hide stale or mismatched snapshot conditions

If preflight fails on required conditions, execution must stop.

---

## 2. What preflight checks

Preflight checks four classes of requirements:

1. **Repo state**
2. **Tool availability**
3. **Artifact availability**
4. **Artifact freshness and validity**

These checks apply before:

- `/repo-structure run`
- `/repo-structure run --stage <stage>`
- `/repo-structure resume`

They should also be available through:

- `/repo-structure check`

---

## 3. Check result levels

Every preflight finding must be classified as one of:

- `missing`
- `invalid`
- `warning`

### `missing`
A required dependency does not exist.

Typical cases:
- required file missing
- required directory missing
- repo root not found
- `.git/` missing
- required tool not available

Default behavior:
- execution must stop

### `invalid`
A dependency exists but is unusable or inconsistent.

Typical cases:
- empty artifact
- malformed schema
- snapshot mismatch
- unreadable file
- output path not writable
- artifact version metadata malformed

Default behavior:
- execution must stop

### `warning`
The dependency is usable but potentially suboptimal or stale.

Typical cases:
- optional input missing
- artifact older than repo HEAD but policy allows warning
- unresolved enrichment debt
- architect docs absent but augment is allowed to emit empty output

Default behavior:
- execution may continue unless stricter mode is requested

---

## 4. Required repo-state checks

The following repo-state checks are mandatory for all execution commands.

### 4.1 Repo root
The current working directory must be the intended repo root.

Expected signal:
- repository layout matches expected project root
- pipeline output paths resolve relative to this root

Failure classification:
- `missing` if repo root cannot be established

### 4.2 Git repo presence
`.git/` must exist.

Failure classification:
- `missing`

### 4.3 Current snapshot identity
The current repo HEAD commit must be available.

This is required for:
- `repo_snapshot_commit`
- stale detection
- snapshot-aware arbitration
- state tracking

Failure classification:
- `invalid` if HEAD cannot be resolved

### 4.4 Writable output paths
The pipeline must be able to write under required output directories.

Typical paths:
- `data/repo-structure/`
- `data/repo-structure/maps/`
- `data/repo-structure/facts/`
- `data/repo-structure/baseline/`

Failure classification:
- `invalid`

---

## 5. Required tool checks

`repo-structure` is an artifact-consuming pipeline, but some deterministic tooling is still required.

Minimum required tools should include:

- `git`
- `python3`
- `rg` or equivalent repo-search tool, if Python evidence collection depends on it

Optional tooling may exist, but required tooling must be explicitly declared in command requirements.

### Important rule
Preflight checks required tools for the current command.
It does **not** upgrade, install, or substitute them automatically.

Failure classification:
- `missing`

---

## 6. Required artifact checks

### 6.1 Upstream commit artifact
Required:

- `data/commit-extract/`

Purpose:
- input for `hotspot`

Failure classification:
- `missing`

Important:
- `repo-structure` does not generate `commit-extract`
- do not backfill it from inside preflight or stage logic

### 6.2 7-file codebase dossier
Required:

- `.planning/codebase/STRUCTURE.md`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/codebase/CONVENTIONS.md`
- `.planning/codebase/INTEGRATIONS.md`
- `.planning/codebase/STACK.md`
- `.planning/codebase/TESTING.md`

Purpose:
- primary input for `sample` and `extract`

Failure classification:
- `missing`

Important:
- these are upstream `gsd::map-codebase` artifacts
- `repo-structure` does not invoke `gsd` internally

### 6.3 Optional architecture doc
Optional:

- `docs/ARCHITECTURE.md`

Purpose:
- source input for `augment`

If absent:
- preflight should emit a `warning`, not a failure
- `augment` may emit an empty artifact and continue

---

## 7. Artifact validity checks

Existence is not enough.

Required artifacts should also be checked for basic validity.

### 7.1 Non-empty artifact
A required file or required artifact directory must not be empty.

Failure classification:
- `invalid`

Examples:
- zero-byte dossier file
- empty `commit-extract` directory
- empty structured artifact file when data is expected

### 7.2 Readability
Artifact must be readable by the pipeline.

Failure classification:
- `invalid`

### 7.3 Schema compatibility
If the artifact is structured and a schema exists, schema compatibility should be checked before stage execution.

Typical cases:
- `hotspot_map.vN.yaml`
- `codebase_map.vN.yaml`
- `architect_augment.vN.yaml`
- `validated.vN.yaml`
- `facts.vN.yaml`
- `state.json`

Failure classification:
- `invalid`

### 7.4 Required metadata
Artifacts that claim versioning or snapshot identity must include required metadata.

Typical required metadata:
- version
- repo_snapshot_commit
- artifact type / artifact name where relevant

Failure classification:
- `invalid`

---

## 8. Freshness and snapshot checks

Preflight must not only ask “does it exist?”
It must also ask “does it describe the right snapshot?”

### 8.1 Freshness policies

Use one of these policies per input:

- `must_exist`
- `optional`
- `must_match_repo_snapshot`
- `allow_older_with_warning`

#### `must_exist`
Artifact must exist.
Freshness may be ignored.

#### `optional`
Artifact may be absent.
Absence may produce a warning or no issue.

#### `must_match_repo_snapshot`
Artifact must exist and its `repo_snapshot_commit` must equal current HEAD.

Mismatch classification:
- `invalid`

Use this when downstream correctness depends on current-snapshot alignment.

#### `allow_older_with_warning`
Artifact may be older than current HEAD.
Mismatch classification:
- `warning`

Use this only when stale input is tolerable for exploratory or partial runs.

---

## 9. Recommended freshness policy by command

### `/repo-structure check`
- report everything
- do not execute
- show both hard failures and warnings

### `/repo-structure run`
Recommended default:
- required upstream raw inputs: `must_exist`
- current-stage structured inputs: `must_match_repo_snapshot` where applicable
- optional architecture doc: `optional`

### `/repo-structure run --stage hotspot`
- `data/commit-extract/`: `must_exist`
- repo HEAD: required
- output paths: writable

### `/repo-structure run --stage extract`
- 7-file dossier: `must_exist`
- repo HEAD: required
- output paths: writable

### `/repo-structure run --stage augment`
- if running with `docs/ARCHITECTURE.md`: `optional`
- candidate evidence collection tooling: required
- repo HEAD: required

### `/repo-structure run --stage validate`
Inputs such as:
- `hotspot_map`
- `codebase_map`
- `architect_augment`

should normally follow:
- `must_match_repo_snapshot`

### `/repo-structure run --stage baseline`
Inputs such as:
- `validated.vN.yaml`
- `conflicts.vN.yaml`

should normally follow:
- `must_match_repo_snapshot`

### `/repo-structure resume`
- same checks as `run`
- plus state continuity checks
- stale outputs from prior partial runs should be reported explicitly

---

## 10. State continuity checks

If `state.json` exists, preflight should inspect it.

Typical checks:

### 10.1 Stage continuity
If resuming:
- last known failed/incomplete stage should be identifiable
- required prior outputs should still exist

Failure classification:
- `invalid` if resume target is ambiguous or broken

### 10.2 Snapshot continuity
If existing state references a different `repo_snapshot_commit` from current HEAD:

- emit `warning` for exploratory resume modes if allowed
- emit `invalid` for strict snapshot-bound resume

Default recommended behavior:
- treat as `invalid` for normal resume

### 10.3 Output overwrite awareness
If output artifacts already exist for current stage and current snapshot:
- emit a `warning`
- continue only if overwrite policy allows it

---

## 11. Continue mode

`--continue` is not a bypass for required failures.

It may only:

- downgrade optional-input absence to warning
- allow selected stale-artifact situations when freshness policy explicitly allows it
- continue through non-blocking advisories

It must **not** bypass:
- missing required upstream inputs
- unreadable artifacts
- malformed schema
- repo snapshot required mismatch
- non-writable output directories

---

## 12. Stage ownership rule

Preflight should report the producer of missing upstream artifacts whenever possible.

Examples:

- missing `data/commit-extract/`
  - producer: `commit-extract`

- missing `.planning/codebase/STRUCTURE.md`
  - producer: `gsd::map-codebase`

This is important because `repo-structure` consumes upstream artifacts.
It does not silently assume ownership of producing them.

---

## 13. Recommended issue format

Preflight findings should be structured enough for both agent and human use.

Recommended fields:

```yaml id="pdv54w"
ok:
command:
repo_head:
missing:
  - code:
    subject:
    message:
    producer:
    suggestion:
invalid:
  - code:
    subject:
    message:
    producer:
    suggestion:
warnings:
  - code:
    subject:
    message:
    producer:
    suggestion:
````

Examples of useful codes:

### Missing

* `MISSING_REPO_ROOT`
* `MISSING_GIT_REPO`
* `MISSING_TOOL`
* `MISSING_INPUT`

### Invalid

* `INVALID_SCHEMA`
* `EMPTY_ARTIFACT`
* `CORRUPTED_ARTIFACT`
* `SNAPSHOT_MISMATCH`
* `OUTPUT_NOT_WRITABLE`

### Warning

* `OPTIONAL_INPUT_MISSING`
* `STALE_ARTIFACT`
* `OUTPUT_ALREADY_EXISTS`
* `STATE_SNAPSHOT_DRIFT`

---

## 14. Failure semantics

The pipeline must fail loudly when trustworthiness would otherwise degrade.

Prefer:

* explicit missing input
* explicit invalid schema
* explicit snapshot mismatch
* explicit stale warning

over:

* implicit substitution
* hidden fallback behavior
* silent coercion
* proceeding with ambiguous state

A green run with broken assumptions is worse than an early visible failure.

---

## 15. Non-goals

Preflight does not:

* perform stage execution
* generate missing upstream artifacts
* resolve semantic conflicts
* repair malformed structured outputs
* perform baseline arbitration

Preflight only decides whether execution can start safely.

---

## 16. Practical checklist

Before allowing execution, ask:

* Is this the correct repo root?
* Is `.git/` present?
* Can HEAD be resolved?
* Are required tools available?
* Are required upstream artifacts present?
* Are they readable and non-empty?
* Do structured inputs match expected schema?
* Do snapshot-sensitive inputs match current HEAD?
* Are output paths writable?
* If resuming, is the saved state still coherent?

If any required answer is “no”, stop.

```

---

这份补上之后，运行约束这一层就更清楚了：

- upstream artifact 缺失时报谁来生产
- 什么叫 missing / invalid / warning
- 哪些必须 `must_match_repo_snapshot`
- `--continue` 绝不能绕过哪些硬错误

这和你前面定下来的“依赖整体检查，而不是 skill 互调”是完全对齐的。

现在还差的核心文件，最值得补的是：

- `references/arbitration-rules.md`

因为 `baseline` 现在已经有 schema 了，但“到底怎么裁决冲突、怎么选 winning fact”还没写成正式规则。
```
