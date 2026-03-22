---

````markdown
# Evidence Model

This document defines the evidence contract for the `repo-structure` pipeline.

It standardizes:

- what a fact entry is
- what an architecture adjudication record is
- how evidence is attached
- how locator types are used
- how `stable_ref` is constructed
- what later stages may assume during validation and baseline arbitration

The goal is not to describe all possible metadata.
The goal is to define the minimum trustworthy structure required for extraction, validation, and consolidation.

---

## 1. Core principle

All facts in `repo-structure` must be **evidence-bound**.

This means:

- every accepted fact must be traceable to at least one evidence item
- every evidence item must identify where support comes from
- evidence must be stable enough to survive normalization and downstream reuse
- unsupported summaries are not facts

Narrative text is not a substitute for evidence binding.

---

## 2. Evidence-bearing objects

`repo-structure` uses two evidence-bearing objects:

1. **Fact Entry**
   - produced mainly by `hotspot` and `extract`
   - normalized by `validate`
   - merged into baseline by `baseline`

2. **Architecture Adjudication Record**
   - produced by `augment`
   - used to qualify architecture-document claims
   - merged as architect-side evidence during baseline arbitration

These objects are different and must not be collapsed into one schema.

---

## 3. Fact Entry

A fact entry is the atomic unit of repo knowledge in the pipeline.

It must be:

- atomic
- evidence-bound
- mergeable
- deduplicable
- understandable by both machine and human reviewers

### Required structure

```yaml
fact_id:
fact_type:
subject:
predicate:
object:
statement:
confidence:
repo_snapshot_commit:
source:
  source_type:
  source_artifact:
evidence:
  - source_doc:
    section_title:
    section_path:
    locator_type:
    locator:
    stable_ref:
    rationale:
status:
notes:
````

### Field meaning

#### `fact_id`

Stable identifier for this fact entry inside the artifact that produced it.

This does not need to be globally permanent across reruns, but it must be unique within the source artifact.

#### `fact_type`

Concise semantic category for the fact.

Examples:

* `module_role`
* `abstraction`
* `entry_point`
* `layer_boundary`
* `dependency_rule`
* `registration_pattern`
* `technology_dependency`
* `config_binding`
* `risk_area`
* `boundary_fact`
* `convention_rule`
* `naming_rule`
* `implementation_rule`
* `integration_dependency`
* `external_contract`
* `data_source_binding`
* `test_surface`
* `verification_rule`
* `regression_risk`
* `test_entry_point`

#### `subject`

Primary semantic object of the fact.

Examples:

* `core/`
* `OperatorRegistry`
* `lower layers`
* `feature hydration`
* `parser compatibility changes`

#### `predicate`

Short relation phrase.

Examples:

* `contains`
* `depends_on`
* `must_not_depend_on`
* `exposes`
* `registers`
* `loads_from`
* `integrates_with`
* `requires`
* `is_fragile_due_to`
* `must_follow`

#### `object`

Target of the relation, if any.

#### `statement`

Human-readable sentence expressing the fact.

This is for readability and review.
It must remain faithful to `subject/predicate/object`.

#### `confidence`

Allowed values:

* `confirmed`
* `uncertain`
* `contradicted`

Guidance:

* `confirmed`: explicitly supported by evidence
* `uncertain`: partially supported, incomplete, or indirect
* `contradicted`: only when the source itself explicitly negates or forbids an alternative

`contradicted` is rare in ordinary extraction and more common in comparison/adjudication contexts.

#### `repo_snapshot_commit`

Git commit hash representing the repo snapshot this fact belongs to.

This is required for:

* stale detection
* snapshot drift handling
* baseline arbitration across versions

#### `source`

Metadata about where the fact entry came from as a pipeline artifact.

```yaml
source:
  source_type: hotspot|codebase|architect
  source_artifact:
```

* `hotspot`: produced from commit-history pipeline
* `codebase`: produced from 7-file dossier extraction
* `architect`: produced through architecture claim augmentation

`source_artifact` should identify the producing artifact, such as:

* `hotspot_map.v3.yaml`
* `codebase_map.v2.yaml`
* `architect_augment.v1.yaml`

#### `evidence`

List of one or more evidence items supporting this fact.

A fact with zero evidence items must not be accepted into validated output.

#### `status`

Recommended values:

* `active`
* `conflicted`
* `filtered`

Typical use:

* `active`: normal candidate fact
* `conflicted`: fact participates in unresolved conflict
* `filtered`: rejected or downgraded during validation

#### `notes`

Optional implementation/debug field.
Must not carry critical semantics that are missing from the structured fields.

---

## 4. Evidence Item

An evidence item explains why a fact is allowed to exist.

### Required structure

```yaml
- source_doc:
  section_title:
  section_path:
  locator_type:
  locator:
  stable_ref:
  rationale:
```

### Field meaning

#### `source_doc`

Origin document category.

Common values:

* `STRUCTURE`
* `ARCHITECTURE`
* `CONCERNS`
* `CONVENTIONS`
* `INTEGRATIONS`
* `STACK`
* `TESTING`
* `COMMIT`
* `ARCH_DOC`

Use stable uppercase categories rather than arbitrary filenames.

#### `section_title`

Human-readable section title from the source document.

#### `section_path`

Stable path-like section locator inside the source document.

Examples:

* `STRUCTURE/Directory Layout`
* `ARCHITECTURE/Key Abstractions`
* `TESTING/Required Regressions`

#### `locator_type`

How the evidence anchors into a repo-relevant object.

Allowed types:

* `file_path`
* `symbol`
* `config_key`
* `section_ref`
* `test_case`
* `ast_pattern`

Do not invent new locator types without updating this document and downstream validation.

#### `locator`

Concrete locator payload corresponding to `locator_type`.

Examples:

* for `file_path`: `runtime/parser/compat.py`
* for `symbol`: `OperatorRegistry`
* for `config_key`: `slot.id`
* for `section_ref`: `TESTING/Required Regressions`
* for `test_case`: `tests/parser/test_legacy.py::test_legacy_fixture`
* for `ast_pattern`: `REGISTER_OPERATOR(*)`

#### `stable_ref`

Canonical stable reference string used across normalization and comparison.

This is the most important evidence field.

#### `rationale`

One short explanation of why this evidence supports the fact.

It should explain the relevance of the locator.
It should not repeat the entire section text.

---

## 5. stable_ref contract

`stable_ref` is the canonical reference format for evidence comparison, deduplication, and downstream traceability.

### Allowed forms

#### File path only

```text
path:<file_path>
```

Example:

```text
path:runtime/parser/compat.py
```

#### Symbol in file

```text
symbol:<file_path>::<symbol_name>
```

Example:

```text
symbol:ops/registry.h::REGISTER_OPERATOR
```

#### Symbol without known file

```text
symbol:<unknown>::<symbol_name>
```

Use only when:

* the source explicitly names the symbol
* no stable file path is available in the current evidence context

This is allowed in worker output but should be enriched later if possible.

#### Config key

```text
config:<config_path>::<key>
```

Example:

```text
config:conf/ops.conf::slot_id
```

#### Section reference

```text
section:<source_doc>::<section_path>
```

Example:

```text
section:CONVENTIONS::CONVENTIONS/Layering Rules
```

#### Test case

```text
test:<file_path>::<test_name>
```

Example:

```text
test:tests/parser/test_legacy.py::test_legacy_fixture
```

### stable_ref rules

* prefer the most concrete stable reference available
* prefer symbol over file path when a named symbol exists
* prefer config key over generic section reference when the key is explicit
* use section reference when the source states a rule or boundary without concrete repo objects
* do not fabricate file paths or symbol names
* do not use line numbers as canonical stable refs

Line ranges are too fragile for baseline-quality evidence.

---

## 6. Locator usage rules

Locator choice must be consistent with source semantics.

### `file_path`

Use for:

* directory/module roles
* fragile files
* named implementation files
* explicit file-level ownership

### `symbol`

Use for:

* entry points
* registries
* macros
* interfaces
* concrete abstractions
* test helpers when explicitly named

### `config_key`

Use for:

* config-driven behavior
* explicit feature flags
* slot allocation/config rules
* infrastructure config bindings

### `section_ref`

Use for:

* document-level structural rules
* conventions
* test/verification requirements
* architecture claims that do not point to a concrete file/symbol

### `test_case`

Use only when an explicit test file and test name are present.

### `ast_pattern`

Use sparingly.
Prefer concrete symbols when available.

Suitable for:

* registration patterns
* structural macros
* syntax-level patterns explicitly named in docs

---

## 7. Architecture Adjudication Record

`augment` does not emit ordinary fact entries first.
It emits adjudication records that qualify architecture claims.

### Required structure

```yaml
claim_id:
claim_text:
claim_type:
status:
repo_snapshot_commit:
matched_evidence:
  - evidence_id:
    stable_ref:
    source_type:
    support_strength:
    rationale:
counter_evidence:
  - evidence_id:
    stable_ref:
    source_type:
    rationale:
miss_summary:
  missing_queries: []
  note:
rationale:
```

### Field meaning

#### `claim_id`

Stable identifier for the architecture-doc claim inside the augment artifact.

#### `claim_text`

Original architecture claim text.

#### `claim_type`

Semantic category of the claim.

Examples:

* `registration_pattern`
* `dependency_rule`
* `thread_safety_rule`
* `config_driven_behavior`
* `boundary_rule`
* `integration_contract`

#### `status`

Allowed values:

* `evidence_backed`
* `weakly_backed`
* `gap`
* `drift`

These are not the same as fact confidence.

#### `matched_evidence`

Evidence supporting the claim.

Each item should include:

* stable reference
* source type
* support strength
* concise rationale

#### `counter_evidence`

Evidence contradicting the claim.

Used mainly for `drift`.

#### `miss_summary`

Negative search signal.
Useful when explaining why support is absent or incomplete.

#### `rationale`

Short explanation of the adjudication decision.

---

## 8. Difference between fact confidence and claim status

Do not confuse these two systems.

### Fact confidence

Used on extracted facts:

* `confirmed`
* `uncertain`
* `contradicted`

### Claim adjudication status

Used on architecture-doc claims:

* `evidence_backed`
* `weakly_backed`
* `gap`
* `drift`

They solve different problems.

A claim can be `gap` even though some extracted facts are `confirmed`.
A claim can be `drift` even if the old documentation was once accurate.

---

## 9. Minimum acceptance rules for validation

`validate` may assume the following.

### A fact entry is minimally valid only if:

* `fact_type` exists
* `statement` exists
* `repo_snapshot_commit` exists
* `source.source_type` exists
* at least one evidence item exists
* each evidence item has:

  * `locator_type`
  * `locator`
  * `stable_ref`
  * `rationale`

### A fact entry should be rejected or downgraded when:

* it is only a summary with no atomic meaning
* evidence is missing
* stable refs are malformed
* locator type is unknown
* statement and structured fields disagree badly
* object is overloaded with multiple unrelated claims

### An adjudication record is minimally valid only if:

* `claim_id` exists
* `claim_text` exists
* `status` exists
* `repo_snapshot_commit` exists
* `rationale` exists

For `drift`, at least one `counter_evidence` item should usually be present.

For `evidence_backed`, at least one strong or clearly stable matched evidence item should usually be present.

---

## 10. Baseline expectations

`baseline` may assume:

* all input facts have already passed schema and evidence completeness checks
* conflicts have already been surfaced
* `stable_ref` is comparable across artifacts
* `repo_snapshot_commit` is available for snapshot-aware arbitration

`baseline` must not assume:

* all facts are conflict-free
* all symbol refs are file-resolved
* all architecture claims are accepted
* all evidence has equal strength

---

## 11. Non-goals

This evidence model does not define:

* the full versioning scheme
* the full CLI/state protocol
* how prompts are implemented
* how candidate evidence is collected in Python
* how downstream domain-model assets are distilled

Those belong elsewhere.

This document only defines the minimum evidence contract that all stages must respect.

---

## 12. Practical guidance

When uncertain, prefer:

* fewer facts
* stronger evidence
* stable refs over fragile anchors
* visible uncertainty over fake certainty
* explicit conflict over silent overwrite

A pipeline with fewer trustworthy facts is better than a larger baseline full of weak summaries.

```

这份补上之后，你现在最小闭环就更完整了：

- `SKILL.md`
- `references/gotchas.md`
- `references/evidence-model.md`
- `prompts/extract_codebase.md`
- `prompts/augment_architect.md`
