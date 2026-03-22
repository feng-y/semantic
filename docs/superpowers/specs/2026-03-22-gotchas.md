可以，下面把 **`skills/repo-structure/references/gotchas.md`** 完整再输出一遍。

```markdown
# Repo-Structure Gotchas

This file records the highest-value failure modes for the `repo-structure` skill.

Read this file before changing stage boundaries, artifact contracts, extraction prompts, or baseline arbitration logic.

---

## 1. Do not treat Domain / Concept / Rule Map as outputs of this skill

`repo-structure` does **not** directly produce Domain Map, Concept Map, or Rule Map.

Its only source-of-truth output is:

- `data/repo-structure/baseline/facts.vN.yaml`

Those semantic maps are **derived views** and must be produced downstream from baseline facts.

If a problem appears in a derived semantic view, do **not** patch the view directly. Fix the issue in:

- source extraction
- validation
- baseline arbitration

---

## 2. Do not invoke `gsd` inside this pipeline

`gsd` is an upstream analyzer.

This skill consumes precomputed artifacts under:

- `.planning/codebase/STRUCTURE.md`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/codebase/CONVENTIONS.md`
- `.planning/codebase/INTEGRATIONS.md`
- `.planning/codebase/STACK.md`
- `.planning/codebase/TESTING.md`

If they are missing, fail explicitly and report the expected files.

Do **not**:

- shell out to `gsd`
- silently regenerate `.planning/codebase/`
- blur the boundary between upstream analysis and fact extraction

Reason:

- keeps control flow transparent
- keeps failures attributable
- keeps `repo-structure` tool-agnostic at the pipeline boundary

---

## 3. Do not generate `commit-extract` internally

`data/commit-extract/` is an upstream artifact.

The `hotspot` stage consumes it. It does not generate it.

If commit artifacts are missing:

- fail in preflight
- report producer
- suggest the upstream action

Do **not** make `hotspot` secretly bootstrap `commit-extract`.

Reason:

- otherwise `hotspot` becomes both consumer and producer
- stage ownership becomes unclear
- rerun/cache/version semantics get muddy

---

## 4. Do not skip preflight or backfill dependencies inside a stage

All required dependencies must be checked before execution.

Preflight is not optional bookkeeping. It is part of the pipeline contract.

Do **not**:

- enter a stage and then discover missing upstream inputs halfway through
- silently create substitute inputs
- bypass required-input failures with `--continue`

`--continue` only applies to optional inputs and warnings.

Reason:

- control flow must remain explicit
- failures must remain attributable
- stage execution must be reproducible

---

## 5. Do not treat `hotspot_map` as raw git statistics

`hotspot_map` is not “top changed files”.

It must come from:

- `commit-extract`
- `commit-semantic`

This stage exists to capture recurring change patterns, hotspot domains, and historical evolution signals.

Do **not** reduce it to:

- file churn counts
- line-change rankings
- naive author/date aggregation

Reason:

- raw git stats lose semantic recurrence
- downstream baseline would overfit noise and underfit real change patterns

---

## 6. Do not batch `extract` by whole file

`extract` must not process `STRUCTURE.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `STACK.md`, or `TESTING.md` as monolithic files.

The required extraction unit is:

- deterministic section split
- then `DocSectionTask`
- then route by section type

Do **not**:

- pass an entire file to one worker and ask for “facts”
- merge unrelated section semantics into one batch
- use file-level prompt policies where section-level locator rules are required

Reason:

- section semantics are heterogeneous
- locator policy depends on section type
- whole-file extraction causes drifting summaries and weak evidence binding

---

## 7. Do not output summaries from `extract`

The output unit of `extract` is a **fact entry with evidence binding**.

It is **not**:

- a prose summary
- a module overview paragraph
- a “best effort architecture explanation”

Every extracted fact must be:

- atomic enough to validate
- grounded in the provided section
- attached to evidence

Minimum expectation:

- statement
- subject / predicate / object or equivalent structured form
- source metadata
- locator_type
- locator
- stable_ref
- rationale or quote

Reason:

- summaries are hard to merge, validate, deduplicate, and arbitrate
- baseline requires structured fact units, not narrative text

---

## 8. Do not let locator rules drift

Locator strategy is part of the extraction contract.

Typical mapping:

- file listings / module lists → `file_path`
- key methods / interfaces / extension points → `symbol`
- config mentions → `config_key`
- runtime/library stack references → `section_ref`
- test file / explicit test case → `test_case`

Do **not** let workers invent locator styles ad hoc.

Reason:

- evidence becomes incomparable
- validation becomes inconsistent
- stable refs become unreliable

---

## 9. Do not let `augment` trust architecture docs by default

Architecture docs are claims, not automatically accepted facts.

The `augment` stage must:

1. read architecture claims
2. collect candidate repo evidence deterministically
3. adjudicate the claim/evidence match
4. assign a status

Accepted statuses:

- `evidence_backed`
- `weakly_backed`
- `gap`
- `drift`

Do **not**:

- accept claims directly from docs
- let the LLM search the repo on its own without provided evidence candidates
- treat comments as stronger than direct implementation evidence

Reason:

- architecture docs drift
- code may partially implement a claim
- some claims are historical, aspirational, or outdated

---

## 10. Do not collapse `weakly_backed`, `gap`, and `drift`

These statuses exist for a reason.

They are not interchangeable.

- `evidence_backed`: direct stable support exists
- `weakly_backed`: partial or indirect support only
- `gap`: no stable supporting evidence found
- `drift`: repo contradicts the claim

Do **not** compress all non-confirmed states into “not found”.

Reason:

- downstream repair actions differ
- governance needs to distinguish absence from contradiction
- drift is a stronger signal than missing support

---

## 11. Do not let `validate` perform baseline arbitration

`validate` is for:

- schema checks
- evidence completeness checks
- normalization
- deduplication
- conflict detection

`validate` is **not** the place to decide final winners across sources.

Final source arbitration belongs in:

- `baseline`

Reason:

- keeping validation and arbitration separate preserves stage clarity
- otherwise conflicts disappear too early and become impossible to inspect

---

## 12. Do not hide conflicts

If two facts cannot be cleanly reconciled, preserve the conflict explicitly.

Write conflicts to:

- `data/repo-structure/facts/conflicts.vN.yaml`

Do **not**:

- silently drop the lower-priority fact
- flatten disagreement into one vague merged sentence
- overwrite historical disagreement without lineage

Reason:

- unresolved conflicts are valuable review signals
- hidden conflict is worse than visible ambiguity

---

## 13. Do not ignore snapshot drift during baseline arbitration

When the same statement appears across different repo snapshots:

- prefer the current snapshot for current baseline coverage
- keep older evidence in lineage/history
- do not let an older fact override the current snapshot

Reason:

- otherwise stale architect/codebase facts can wrongly dominate current baseline
- versioned baseline must describe the current repo snapshot first

---

## 14. Do not force all three maps to rerun together

The three source maps have independent versions:

- `hotspot_map`
- `codebase_map`
- `architect_augment`

A snapshot records their combination.

Do **not** make every update require a full rerun of all three sources unless explicitly requested.

Reason:

- wastes work
- increases iteration cost
- breaks the independent-pipeline design

---

## 15. Do not patch baseline issues by editing derived outputs

If downstream users find a semantic issue in a derived asset, do **not** patch:

- Domain Map
- Concept Map
- Rule Map

as the primary fix.

Instead, trace the issue back to:

- extraction error
- evidence weakness
- validation miss
- arbitration error

Then regenerate from baseline.

Reason:

- otherwise source-of-truth and derived views diverge
- future reruns will reintroduce the same issue

---

## 16. Do not make the skill explanation heavier than the execution contract

`SKILL.md` should remain a map, not an encyclopedia.

Put detailed policies in:

- `references/evidence-model.md`
- `references/arbitration-rules.md`
- `references/preflight-rules.md`
- this file

Do **not** overload `SKILL.md` with all examples, edge cases, and rationales.

Reason:

- keeps routing clear
- supports progressive disclosure
- prevents prompt bloat

---

## 17. Do not optimize for green runs over trustworthy facts

A pipeline that “completes” but produces weak or ungrounded facts is worse than a pipeline that fails loudly.

Prefer:

- explicit failure
- preserved uncertainty
- visible conflict
- grounded evidence

over:

- silent coercion
- fake certainty
- over-merged summaries
- hidden missing inputs

Reason:

- local success does not equal trustworthy semantic baseline
- this skill is part of governance, not just automation

---

## Review checklist for changes to this skill

Before accepting a change, verify:

- Are upstream boundaries still explicit?
- Are stage responsibilities still separated?
- Are facts still atomic and evidence-bound?
- Are conflicts still preserved?
- Is baseline still the only source-of-truth?
- Is any stage silently doing someone else’s job?
- Has any convenience change weakened traceability?

If the answer to any of these is “yes, maybe”, stop and inspect before merging.
```

如果你要，我下一条可以把这份再收成一个**更短、更像 CC 真正在运行时会读的版本**。
