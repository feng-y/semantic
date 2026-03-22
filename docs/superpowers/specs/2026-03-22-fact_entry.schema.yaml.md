下面给你 **`skills/repo-structure/schemas/fact_entry.schema.yaml` 初稿**。

目标很明确：

**把 `extract` / `hotspot` / `validate` 能共同接受的最小 fact contract 固化下来。**

这版我故意不做成超重 JSON Schema 风格，而是偏 **实现友好**、方便你在 CC 里先落类型检查和基本校验。

---

```yaml id="pzhmfy"
schema_name: fact_entry
schema_version: v1

description: >
  Canonical schema for atomic evidence-bound fact entries used by the
  repo-structure pipeline. This schema is shared by hotspot, extract,
  validate, and baseline stages.

type: object
additional_properties: false

required:
  - fact_id
  - fact_type
  - subject
  - predicate
  - statement
  - confidence
  - repo_snapshot_commit
  - source
  - evidence
  - status

properties:
  fact_id:
    type: string
    min_length: 1
    description: Unique identifier within the producing artifact.

  fact_type:
    type: string
    min_length: 1
    enum:
      - module_role
      - abstraction
      - entry_point
      - extension_point
      - layer_boundary
      - dependency_rule
      - registration_pattern
      - technology_dependency
      - config_binding
      - risk_area
      - boundary_fact
      - convention_rule
      - naming_rule
      - implementation_rule
      - integration_dependency
      - external_contract
      - data_source_binding
      - test_surface
      - verification_rule
      - regression_risk
      - test_entry_point

  subject:
    type: string
    min_length: 1
    description: Primary semantic object of the fact.

  predicate:
    type: string
    min_length: 1
    description: Relation phrase connecting subject and object.

  object:
    type:
      - string
      - "null"
    description: Optional target of the relation.

  statement:
    type: string
    min_length: 1
    description: Human-readable sentence faithful to the structured fields.

  confidence:
    type: string
    enum:
      - confirmed
      - uncertain
      - contradicted

  repo_snapshot_commit:
    type: string
    min_length: 1
    description: Git commit hash for the repo snapshot this fact belongs to.

  source:
    type: object
    additional_properties: false
    required:
      - source_type
      - source_artifact
    properties:
      source_type:
        type: string
        enum:
          - hotspot
          - codebase
          - architect
      source_artifact:
        type: string
        min_length: 1
        description: Producing artifact file name or logical artifact id.

  evidence:
    type: array
    min_items: 1
    items:
      type: object
      additional_properties: false
      required:
        - source_doc
        - section_title
        - section_path
        - locator_type
        - locator
        - stable_ref
        - rationale
      properties:
        source_doc:
          type: string
          enum:
            - STRUCTURE
            - ARCHITECTURE
            - CONCERNS
            - CONVENTIONS
            - INTEGRATIONS
            - STACK
            - TESTING
            - COMMIT
            - ARCH_DOC

        section_title:
          type: string
          min_length: 1

        section_path:
          type: string
          min_length: 1

        locator_type:
          type: string
          enum:
            - file_path
            - symbol
            - config_key
            - section_ref
            - test_case
            - ast_pattern

        locator:
          type: string
          min_length: 1

        stable_ref:
          type: string
          min_length: 1
          description: Canonical stable reference used for comparison and traceability.

        rationale:
          type: string
          min_length: 1
          description: Short explanation of why this evidence supports the fact.

  status:
    type: string
    enum:
      - active
      - conflicted
      - filtered

  notes:
    type:
      - string
      - "null"
    description: Optional debug or implementation note. Must not carry critical semantics.

validation_rules:
  - name: statement_should_not_be_blank
    description: Statement must be non-empty and represent one atomic fact.

  - name: evidence_must_exist
    description: Every fact must have at least one evidence item.

  - name: stable_ref_required
    description: Every evidence item must include a stable_ref.

  - name: locator_type_must_be_known
    description: locator_type must be one of the allowed evidence locator types.

  - name: subject_predicate_required
    description: subject and predicate are mandatory even when object is null.

  - name: contradicted_should_be_rare
    description: contradicted confidence is allowed but should normally appear only in explicitly negative source statements.

normalization_hints:
  - object may be null when the fact expresses a one-sided property.
  - symbol:<unknown>::<symbol_name> is allowed in worker output and may be enriched later.
  - statement is review-facing; subject/predicate/object are merge-facing.
  - notes should never be required for semantic interpretation.

examples:
  - fact_id: codebase-structure-001
    fact_type: module_role
    subject: core/
    predicate: contains
    object: shared abstractions
    statement: The core/ module contains shared abstractions.
    confidence: confirmed
    repo_snapshot_commit: abc123
    source:
      source_type: codebase
      source_artifact: codebase_map.v1.yaml
    evidence:
      - source_doc: STRUCTURE
        section_title: Directory Layout
        section_path: STRUCTURE/Directory Layout
        locator_type: file_path
        locator: core/
        stable_ref: path:core/
        rationale: The section explicitly assigns shared abstractions to core/.
    status: active
    notes: null

  - fact_id: conventions-002
    fact_type: dependency_rule
    subject: lower layers
    predicate: must_not_depend_on
    object: service orchestration code
    statement: Lower layers must not depend on service orchestration code.
    confidence: confirmed
    repo_snapshot_commit: abc123
    source:
      source_type: codebase
      source_artifact: codebase_map.v1.yaml
    evidence:
      - source_doc: CONVENTIONS
        section_title: Layering Rules
        section_path: CONVENTIONS/Layering Rules
        locator_type: section_ref
        locator: CONVENTIONS/Layering Rules
        stable_ref: section:CONVENTIONS::CONVENTIONS/Layering Rules
        rationale: The section explicitly states this layering restriction.
    status: active
    notes: null
```

---

这版 schema 有几个设计点你可以注意下：

### 1. `object` 允许为 `null`

因为有些 fact 天然是一侧属性，比如：

* `parser/compat.py is fragile`
* `OperatorRegistry exists as registry abstraction`

如果强行要求 object，很多句子会变形。

### 2. `source.source_type` 只保留 3 个

因为这是 **baseline source lineage**，不是原始 doc lineage：

* `hotspot`
* `codebase`
* `architect`

而 `source_doc` 才记录更细的 dossier 文档来源。

### 3. `status` 不是 confidence

这两个要分开：

* `confidence` 说事实支持强度
* `status` 说这个 fact 在 pipeline 里的处理状态

这个 separation 很重要，后面 `validate` 和 `baseline` 才不会混。

### 4. 允许 `symbol:<unknown>::X`

这是为了适配 worker 阶段还没做 enrichment 的情况。
前面在 `extract_codebase.md` 里我们已经留了这个口子，现在 schema 也对齐了。

---

我建议你在 CC 里实现时，第一版不要直接拿这个 schema 做全量 JSON Schema validator，而是先映射成 Python dataclass / pydantic model，再补 schema export。这样调试快很多。

