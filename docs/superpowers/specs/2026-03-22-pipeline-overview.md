下面给你 **`skills/repo-structure/references/pipeline-overview.md` 初稿**。

这份的作用不是补规则细节，而是把整条 `repo-structure` skill 的执行图景收成一页，方便 CC 在实现时不跑偏。

---

````markdown id="pyy8g8"
# Repo-Structure Pipeline Overview

This document gives the operational overview of the `repo-structure` pipeline.

It explains:

- what the pipeline consumes
- what each stage produces
- how artifacts flow
- where evidence is created, checked, and frozen
- what downstream consumers are allowed to read

This is a map, not a full policy document.

For detailed rules, see:

- `references/evidence-model.md`
- `references/preflight-rules.md`
- `references/arbitration-rules.md`
- `references/gotchas.md`

---

## 1. Purpose

`repo-structure` converts repo-level upstream signals into a versioned factual baseline.

It is the first semantic layer.

Its output is not a final semantic map.
Its output is a **baseline fact snapshot** that downstream stages can trust and reuse.

Primary output:

- `data/repo-structure/baseline/facts.vN.yaml`

This file is the only source-of-truth produced by this skill.

---

## 2. Upstream inputs

The pipeline consumes three upstream evidence sources.

### 2.1 Commit history artifacts
Input:
- `data/commit-extract/`

Used by:
- `hotspot`

Purpose:
- historical recurring change patterns
- hotspot modules
- evolution pressure
- recurring rule-touching areas

### 2.2 7-file precomputed codebase dossier
Inputs:
- `.planning/codebase/STRUCTURE.md`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/codebase/CONVENTIONS.md`
- `.planning/codebase/INTEGRATIONS.md`
- `.planning/codebase/STACK.md`
- `.planning/codebase/TESTING.md`

Used by:
- `sample`
- `extract`

Purpose:
- structural facts
- boundary facts
- conventions
- integration dependencies
- runtime/stack facts
- test and verification facts

### 2.3 Optional architecture doc
Input:
- `docs/ARCHITECTURE.md`

Used by:
- `augment`

Purpose:
- explicit architecture claims
- intended rules
- documented boundaries
- compare-with-repo governance signals

---

## 3. Execution model

`repo-structure` is a stage-driven pipeline.

Normal order:

1. `sample`
2. `hotspot`
3. `extract`
4. `augment`
5. `validate`
6. `baseline`

Every execution command must pass preflight first.

The pipeline does **not**:
- invoke `gsd`
- generate `commit-extract`
- invoke upstream skills implicitly
- hide missing dependencies inside stage logic

---

## 4. Stage-by-stage view

## 4.1 sample

Inputs:
- 7-file codebase dossier

Purpose:
- build a sampling manifest for downstream extraction
- decide what files/sections/symbols deserve stronger attention
- enrich extraction planning from structure, concerns, conventions, integrations, and testing references

Output:
- `data/repo-structure/sample/manifest.yaml`

Important:
- this stage prepares extraction
- it does not emit baseline facts directly

---

## 4.2 hotspot

Inputs:
- `data/commit-extract/`

Purpose:
- turn commit history artifacts into semantic hotspot facts
- capture recurring change patterns
- capture historically sensitive modules and rule-touching areas

Output:
- `data/repo-structure/maps/hotspot_map.vN.yaml`

Important:
- hotspot is not raw git statistics
- recurring semantic signals matter more than churn counts alone

---

## 4.3 extract

Inputs:
- 7-file codebase dossier
- optional sample manifest

Purpose:
- extract codebase facts from dossier sections
- produce atomic evidence-bound fact entries

Method:
- split documents deterministically into sections
- create `DocSectionTask`
- send each section task to the extract worker
- collect fact entries into `codebase_map`

Output:
- `data/repo-structure/maps/codebase_map.vN.yaml`

Important:
- extraction unit is section task, not whole file
- output unit is fact entry, not prose summary

---

## 4.4 augment

Inputs:
- `docs/ARCHITECTURE.md` if present
- repo evidence candidates collected by deterministic tooling

Purpose:
- qualify architecture claims against current repo evidence
- distinguish:
  - `evidence_backed`
  - `weakly_backed`
  - `gap`
  - `drift`

Method:
- read architecture claim
- collect candidate evidence in Python
- let augment worker adjudicate claim/evidence match

Output:
- `data/repo-structure/maps/architect_augment.vN.yaml`

Important:
- augment is not repo exploration by LLM
- augment is evidence adjudication

---

## 4.5 validate

Inputs:
- `hotspot_map.vN.yaml`
- `codebase_map.vN.yaml`
- `architect_augment.vN.yaml`

Purpose:
- clean and normalize facts before baseline freeze

Responsibilities:
- schema checks
- evidence completeness checks
- normalization
- deduplication
- conflict detection
- invalid fact filtering

Outputs:
- `data/repo-structure/facts/validated.vN.yaml`
- `data/repo-structure/facts/conflicts.vN.yaml`

Important:
- validate detects and preserves disagreement
- validate does not perform final arbitration

---

## 4.6 baseline

Inputs:
- `validated.vN.yaml`
- `conflicts.vN.yaml`

Purpose:
- select or preserve candidate facts into the frozen baseline snapshot

Responsibilities:
- candidate grouping
- source-aware arbitration
- snapshot-aware arbitration
- provenance preservation
- conflict preservation
- final baseline freeze

Outputs:
- `data/repo-structure/baseline/facts.vN.yaml`
- `data/repo-structure/baseline/facts.latest.yaml`
- `data/repo-structure/baseline/snapshot.yaml`

Important:
- baseline is the only source-of-truth output
- conflicts may remain visible after baseline

---

## 5. Artifact flow

High-level flow:

```text id="tkczx8"
commit-extract
  ──→ hotspot
  ──→ hotspot_map.vN.yaml

7-file dossier
  ──→ sample
  ──→ manifest.yaml
  ──→ extract
  ──→ codebase_map.vN.yaml

docs/ARCHITECTURE.md + repo evidence candidates
  ──→ augment
  ──→ architect_augment.vN.yaml

hotspot_map + codebase_map + architect_augment
  ──→ validate
  ├──→ validated.vN.yaml
  └──→ conflicts.vN.yaml

validated + conflicts
  ──→ baseline
  ├──→ facts.vN.yaml
  ├──→ facts.latest.yaml
  └──→ snapshot.yaml
````

---

## 6. Evidence flow

Evidence is introduced and strengthened in stages.

### In `hotspot`

Evidence comes from:

* commit history structures
* semantic clustering over commit-extract results

### In `extract`

Evidence comes from:

* dossier sections
* locators
* stable refs
* rationale bound to each fact entry

### In `augment`

Evidence comes from:

* deterministic candidate evidence collection
* adjudicated claim/evidence match records

### In `validate`

Evidence is checked for:

* completeness
* legal locator types
* stable ref presence
* schema compliance

### In `baseline`

Evidence is not newly created.
It is:

* compared
* prioritized
* preserved
* frozen with provenance

---

## 7. What downstream stages may consume

Downstream semantic stages should primarily consume:

* `data/repo-structure/baseline/facts.vN.yaml`
* or `data/repo-structure/baseline/facts.latest.yaml`

Downstream stages may inspect:

* `conflicts`
* `snapshot`
* `source_versions`

But they should not treat:

* `hotspot_map`
* `codebase_map`
* `architect_augment`

as final semantic assets.

Those are intermediate source maps, not baseline truth.

---

## 8. State and reruns

The pipeline keeps stage progress and artifact lineage in state.

Expected state responsibilities:

* record repo snapshot
* record stage success/failure
* record artifact versions
* support `status`
* support `resume`
* support stale detection

Important:

* source maps have independent versions
* baseline snapshot records their combination
* do not force all source maps to rerun together unless explicitly requested

---

## 9. Failure model

Failures should be visible and attributable.

Fail early when:

* required upstream artifact is missing
* repo root is invalid
* HEAD cannot be resolved
* structured artifact is malformed
* snapshot-sensitive input does not match current HEAD
* output path is not writable

Warn when:

* optional architecture doc is missing
* allowed stale input is older than current HEAD
* current output would overwrite prior output
* optional enrichment is incomplete

Do not:

* silently substitute inputs
* silently regenerate upstream artifacts
* continue through invalid required state

---

## 10. Ownership boundaries

`repo-structure` owns:

* section-based extraction
* evidence-bound fact generation
* normalization
* arbitration
* baseline freeze

`repo-structure` does not own:

* generation of `commit-extract`
* generation of the 7-file dossier
* downstream domain-model distillation
* demand matching
* demand card generation

These boundaries must remain explicit.

---

## 11. Mental model

Use this mental model:

* `hotspot` tells you where history keeps hurting
* `extract` tells you what the repo dossier explicitly says
* `augment` tells you whether architecture claims survive contact with the repo
* `validate` tells you what is structurally acceptable
* `baseline` tells you what the current repo snapshot is allowed to claim as trusted baseline fact

That is the whole job of `repo-structure`.

No more.
No less.

```

到这里，`repo-structure` 这条 skill 的设计文档已经比较完整了。现在真正还差的，更多是**实现约束对象**，不是说明文档。

最值得继续补的有两个方向：

- `schemas/state.schema.json`
- `references/pipeline-overview.md` 已经补完后，接下来就是 `state.schema.json`

我建议下一步直接补 **`schemas/state.schema.json`**。
```
