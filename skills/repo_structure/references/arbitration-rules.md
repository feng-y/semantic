下面给你 **`skills/repo-structure/references/arbitration-rules.md` 初稿**。

这份要解决的是：

**`baseline` 阶段面对多个候选 fact 时，到底怎么选、怎么保留、什么时候不该硬合并。**

你前面已经定了几条关键原则：

* source priority：`architect > hotspot > codebase`
* 同优先级下：`recurring > evidence_backed > isolated`
* 不同 snapshot 时优先当前 snapshot
* 仲裁不出来就保留 conflict，不要偷偷抹平

这份文档就是把这些口径正式写死。

---

```markdown id="4v92yx"
# Arbitration Rules

This document defines how the `baseline` stage chooses, preserves, or defers candidate facts after validation.

Arbitration exists to answer one question:

**Given multiple validated candidate facts, which facts should enter the frozen baseline, and which disagreements must remain visible as conflicts?**

Arbitration is not deduplication.
Arbitration happens after validation has already:

- normalized candidate facts
- checked evidence completeness
- surfaced conflicts
- filtered structurally invalid facts

---

## 1. Core principle

Baseline should prefer:

- current-snapshot facts
- stronger evidence
- semantically stable facts
- traceable source lineage

Baseline must not prefer:

- convenience
- over-merged summaries
- silent overwrite
- fake certainty

If a disagreement cannot be resolved cleanly, preserve the conflict.

A visible unresolved conflict is better than a silently wrong baseline fact.

---

## 2. Inputs to arbitration

Arbitration consumes validated candidate facts from three sources:

- `hotspot_map`
- `codebase_map`
- `architect_augment`

These sources are not treated as equal.

They capture different kinds of knowledge:

- `hotspot`: historical recurring evolution signals
- `codebase`: extracted structural/codebase facts from the 7-file dossier
- `architect`: architecture-claim adjudication qualified by repo evidence

---

## 3. Output of arbitration

Arbitration may produce two kinds of results:

1. **Accepted baseline fact**
   - selected into `facts.vN.yaml`

2. **Preserved conflict**
   - recorded under `conflicts`
   - not silently collapsed into one accepted fact

Arbitration may also drop a candidate if it is clearly dominated and non-essential to preserve.

However, dropping should only happen when:
- the winner is clear
- the loser adds no important semantic disagreement
- lineage remains understandable

---

## 4. Arbitration unit

Arbitration should operate on **candidate fact groups**, not on the whole artifact at once.

A candidate fact group is a set of facts that appear to express the same or closely competing semantic statement.

Typical grouping signals:

- same `fact_type`
- same or strongly overlapping `subject`
- same or strongly overlapping `predicate`
- same or strongly overlapping `object`
- same or overlapping `stable_ref`
- very similar normalized `statement`

Grouping should happen before winner selection.

Do not compare unrelated facts just because they come from the same module or file.

---

## 5. Primary source priority

When two candidate facts compete on the same semantic statement, use this source priority order:

1. `architect`
2. `hotspot`
3. `codebase`

### Why this order exists

#### `architect`
Architecture claims that survive adjudication often encode explicit intended system rules or boundaries, and have already been qualified by repo evidence.
They are high-value when evidence-backed.

#### `hotspot`
Recurring change patterns often reveal strong operational truth and long-lived maintenance pressure.
They are stronger than isolated structural mentions when the same behavior keeps resurfacing.

#### `codebase`
Codebase dossier extraction is broad and foundational, but many facts are descriptive rather than strongly enforced.
It is the default structural layer, not always the strongest governing layer.

### Important limitation

Source priority is not absolute.
It is only the first decision axis.

A higher-priority source does **not** automatically win if:
- its support is weak
- it belongs to an older snapshot
- it conflicts with stronger current evidence

---

## 6. Secondary strength priority

Within the same source tier, use this priority order:

1. `recurring`
2. `evidence_backed`
3. `isolated`

### Meaning

#### `recurring`
The same semantic fact or issue appears repeatedly across history or evidence clusters.

Most common in:
- `hotspot`
- repeated conflict surfaces
- repeated rule-touching changes

#### `evidence_backed`
The fact is directly supported by stable evidence.

Most common in:
- `architect_augment` with status `evidence_backed`
- strong `codebase` fact entries with concrete symbol/config anchors

#### `isolated`
The fact appears only once or in a weakly anchored way.

This is not invalid, but it is less trustworthy when competing with recurring or strongly backed facts.

---

## 7. Snapshot priority

If the same semantic statement appears across different repo snapshots:

- prefer the fact aligned with the current `repo_snapshot_commit`
- preserve older facts only as lineage/history when useful
- do not let older snapshot facts dominate the current baseline

### Rule

Current snapshot truth outranks historical truth for baseline coverage.

### Implication

A fact may once have been valid but should still lose baseline selection if:
- it no longer matches current snapshot
- current evidence shows drift
- the repo has moved on

This rule is especially important when architecture docs lag behind the codebase.

---

## 8. Evidence quality modifiers

After applying source priority and snapshot priority, adjust decisions using evidence quality.

Evidence quality is stronger when facts have:

- concrete symbol refs
- concrete config refs
- stable file anchors plus clear rationale
- multiple aligned evidence items
- enforcement-oriented evidence
- validation/test evidence tied to the claimed behavior

Evidence quality is weaker when facts rely mainly on:

- comments only
- naming coincidence
- broad section-level statements without concrete anchors
- generic structural hints
- single weak evidence item

### Important rule

A lower-priority source with clearly stronger current evidence may beat a higher-priority source with weak or stale support.

For example:
- a current codebase fact with concrete symbol/config evidence
- may outrank an older architecture-derived claim that is only weakly backed

---

## 9. Architect-specific status handling

Architecture-derived candidates must respect adjudication status.

### `evidence_backed`
Eligible to compete strongly in arbitration.

### `weakly_backed`
May enter baseline if no stronger current fact exists, but should lose against strong evidence-backed current alternatives.

### `gap`
Should not usually produce an accepted baseline fact.
It is primarily a governance signal.

### `drift`
Should not be accepted as a normal positive baseline fact.
It should usually contribute to:
- conflict preservation
- drift notes
- governance output

Do not convert `gap` or `drift` into ordinary accepted truths.

---

## 10. Conflict preservation rules

Preserve a conflict instead of forcing a winner when any of the following is true:

### 10.1 Semantic contradiction remains
The candidates express materially different meanings and a clean winner is not trustworthy.

### 10.2 Source priority is not enough
The higher-priority source exists, but support is too weak to justify overwriting the lower-priority fact.

### 10.3 Snapshot ambiguity exists
The system cannot confidently determine whether the disagreement is historical, current, or partially migrated.

### 10.4 Merge would lose meaning
Collapsing both sides into one vague summary would hide a meaningful difference.

### 10.5 Governance value is high
The disagreement itself is useful for review, risk tracking, or further refinement.

When in doubt, preserve the conflict.

---

## 11. When a candidate may be dropped

A candidate may be dropped instead of preserved only when all of the following are true:

- another candidate clearly dominates it
- both express effectively the same semantic fact
- dropping it does not hide a meaningful disagreement
- provenance remains reconstructable through the winning fact

Examples:
- same rule restated in multiple equivalent forms
- one fact is a clearly weaker paraphrase of a stronger fact with same stable anchors
- same module-role fact appears twice with no semantic difference

Do not drop a candidate merely to make output look cleaner.

---

## 12. Merge rules for accepted facts

Arbitration may merge candidates into one accepted fact only when:

- they are semantically aligned
- they reinforce the same meaning
- evidence can be combined without contradiction
- the resulting statement remains atomic and reviewable

### Safe merge examples
- two facts express the same dependency rule with different but aligned evidence anchors
- one fact provides file-level structure and another provides symbol-level strengthening

### Unsafe merge examples
- one fact says “must”
- another says “usually”
- one fact encodes a hard rule
- another encodes only a fragile convention
- one fact is current
- another is historical or drifting

If merge quality is doubtful, do not merge.

---

## 13. Arbitration order of operations

Recommended decision sequence:

1. Group competing candidate facts
2. Remove structurally invalid or already filtered candidates
3. Compare snapshot alignment
4. Compare source priority
5. Compare evidence quality
6. Compare recurrence / isolation
7. Check whether candidates are semantically mergeable
8. Either:
   - accept one
   - accept merged fact
   - preserve conflict

Do not start with source priority alone.

---

## 14. Provenance requirements

Every accepted baseline fact should preserve arbitration provenance.

Recommended provenance fields:

- selected candidate ids
- rejected or dominated candidate ids when relevant
- winning reason
- whether merge occurred
- whether snapshot priority was decisive

This is important because baseline is frozen output.
Without provenance, later debugging becomes guesswork.

---

## 15. Conflict record requirements

Every preserved conflict should record:

- participating candidate ids
- participating source artifacts
- repo snapshot
- conflict type
- resolution status
- short explanation of why conflict was preserved

Useful conflict types include:

- `contradictory_statement`
- `snapshot_drift`
- `source_priority_tie`
- `evidence_strength_tie`
- `unresolved_merge`

Do not store only the final vague sentence.
Store enough detail for later review.

---

## 16. Practical decision examples

### Example 1: architect beats codebase
Candidates:
- architect claim: evidence-backed rule, current snapshot
- codebase fact: same rule, weaker section-level evidence

Decision:
- accept architect-derived fact
- optionally merge supporting evidence from codebase if semantically aligned

Reason:
- same snapshot
- higher source priority
- stronger evidence qualification

### Example 2: hotspot beats codebase
Candidates:
- hotspot recurring signal around registration enforcement
- isolated codebase extraction mentioning registration pattern once

Decision:
- hotspot-derived fact wins or strongly informs winner

Reason:
- historical recurrence is stronger than isolated structural mention

### Example 3: current codebase beats stale architect
Candidates:
- architect claim from older snapshot, weakly backed
- codebase fact from current snapshot, concrete symbol evidence

Decision:
- accept current codebase fact
- preserve drift note or conflict if disagreement matters

Reason:
- snapshot priority plus stronger current evidence

### Example 4: preserve conflict
Candidates:
- architect says lower layers must not depend on service orchestration
- current codebase evidence shows such dependency exists
- hotspot history shows repeated fixes around this boundary

Decision:
- preserve conflict
- optionally accept a narrower descriptive fact about the current dependency while separately preserving the violated rule conflict

Reason:
- intended rule and current implementation both matter
- forcing one winner would lose governance value

---

## 17. What arbitration must not do

Arbitration must not:

- silently overwrite meaningful disagreement
- turn `gap` into accepted truth
- turn `drift` into accepted positive baseline fact
- ignore repo snapshot differences
- merge hard rules and soft conventions into one vague fact
- collapse rule conflicts into generic summaries
- hide provenance
- optimize for smaller output at the expense of truthfulness

---

## 18. Default bias

When the decision is unclear, bias toward:

- current snapshot
- stronger evidence
- explicit provenance
- preserved conflict
- narrower accepted fact

Do not bias toward:
- maximal compression
- vague merged statements
- artificial certainty

A narrower trustworthy baseline is better than a broader but unreliable one.
```

---

到这里，`repo-structure` 这条 skill 的**核心设计文档闭环**已经差不多完整了：

* `SKILL.md`
* `references/gotchas.md`
* `references/evidence-model.md`
* `references/preflight-rules.md`
* `references/arbitration-rules.md`
* `prompts/extract_codebase.md`
* `prompts/augment_architect.md`
* `schemas/fact_entry.schema.yaml`
* `schemas/baseline_facts.schema.yaml`

现在往下最值得做的，不再是继续补说明文档，而是开始补**实现接口层**。
最顺的下一个就是：

* `schemas/state.schema.json`
* 或者 `references/pipeline-overview.md`

我建议先补 `references/pipeline-overview.md`，因为它能把上面这些文件怎么协同跑起来收成一页图景。
