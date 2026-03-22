下面给你 **`skills/repo-structure/schemas/baseline_facts.schema.yaml` 初稿**。

这份和 `fact_entry.schema.yaml` 的关系是：

* `fact_entry.schema.yaml` 定义 **原子 fact**
* `baseline_facts.schema.yaml` 定义 **冻结后的 baseline snapshot**

也就是它要解决的不是“单条 fact 长什么样”，而是：

* 一个 baseline 文件头长什么样
* 怎么记录版本 / snapshot / lineage
* facts 和 conflicts 怎么挂进去
* downstream 如何把它当 source-of-truth 来消费

---

```yaml id="bqarfm"
schema_name: baseline_facts
schema_version: v1

description: >
  Canonical schema for the frozen baseline snapshot produced by the
  repo-structure pipeline. This artifact is the only source-of-truth
  output of repo-structure and is consumed downstream by domain-model.

type: object
additional_properties: false

required:
  - baseline_version
  - repo_snapshot_commit
  - generated_at
  - source_versions
  - facts
  - conflicts
  - snapshot

properties:
  baseline_version:
    type: string
    min_length: 1
    description: Version identifier for this baseline artifact, e.g. facts.v3.

  repo_snapshot_commit:
    type: string
    min_length: 1
    description: Git commit hash representing the repo snapshot described by this baseline.

  generated_at:
    type: string
    min_length: 1
    description: ISO-8601 timestamp when this baseline snapshot was frozen.

  snapshot:
    type: object
    additional_properties: false
    required:
      - snapshot_version
      - snapshot_id
    properties:
      snapshot_version:
        type: string
        min_length: 1
        description: Version of the combined semantic-foundation snapshot.
      snapshot_id:
        type: string
        min_length: 1
        description: Unique identifier for this snapshot combination.

  source_versions:
    type: object
    additional_properties: false
    required:
      - hotspot_map
      - codebase_map
      - architect_augment
    properties:
      hotspot_map:
        type: object
        additional_properties: false
        required:
          - artifact
          - version
        properties:
          artifact:
            type: string
            min_length: 1
          version:
            type: string
            min_length: 1
          repo_snapshot_commit:
            type:
              - string
              - "null"

      codebase_map:
        type: object
        additional_properties: false
        required:
          - artifact
          - version
        properties:
          artifact:
            type: string
            min_length: 1
          version:
            type: string
            min_length: 1
          repo_snapshot_commit:
            type:
              - string
              - "null"

      architect_augment:
        type: object
        additional_properties: false
        required:
          - artifact
          - version
        properties:
          artifact:
            type: string
            min_length: 1
          version:
            type: string
            min_length: 1
          repo_snapshot_commit:
            type:
              - string
              - "null"

  facts:
    type: array
    min_items: 0
    description: Accepted baseline facts after validation and arbitration.
    items:
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

        fact_type:
          type: string
          min_length: 1

        subject:
          type: string
          min_length: 1

        predicate:
          type: string
          min_length: 1

        object:
          type:
            - string
            - "null"

        statement:
          type: string
          min_length: 1

        confidence:
          type: string
          enum:
            - confirmed
            - uncertain
            - contradicted

        repo_snapshot_commit:
          type: string
          min_length: 1

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

              rationale:
                type: string
                min_length: 1

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

        provenance:
          type: object
          additional_properties: false
          required:
            - selected_from
            - arbitration_reason
          properties:
            selected_from:
              type: array
              min_items: 1
              items:
                type: string
                min_length: 1
              description: Artifact ids or fact ids considered during arbitration.
            arbitration_reason:
              type: string
              min_length: 1
              description: Short explanation of why this fact was accepted into baseline.

  conflicts:
    type: array
    min_items: 0
    description: Unresolved or explicitly preserved conflicts after validation/arbitration.
    items:
      type: object
      additional_properties: false
      required:
        - conflict_id
        - repo_snapshot_commit
        - conflict_type
        - facts
        - resolution_status
      properties:
        conflict_id:
          type: string
          min_length: 1

        repo_snapshot_commit:
          type: string
          min_length: 1

        conflict_type:
          type: string
          enum:
            - contradictory_statement
            - snapshot_drift
            - source_priority_tie
            - evidence_strength_tie
            - unresolved_merge

        facts:
          type: array
          min_items: 2
          items:
            type: object
            additional_properties: false
            required:
              - fact_id
              - source_type
              - source_artifact
              - statement
            properties:
              fact_id:
                type: string
                min_length: 1
              source_type:
                type: string
                enum:
                  - hotspot
                  - codebase
                  - architect
              source_artifact:
                type: string
                min_length: 1
              statement:
                type: string
                min_length: 1
              stable_refs:
                type: array
                min_items: 0
                items:
                  type: string
                  min_length: 1

        resolution_status:
          type: string
          enum:
            - preserved
            - deferred
            - partially_resolved

        notes:
          type:
            - string
            - "null"

  lineage:
    type:
      - object
      - "null"
    additional_properties: false
    properties:
      previous_baseline_version:
        type:
          - string
          - "null"
      previous_snapshot_id:
        type:
          - string
          - "null"
      change_summary:
        type:
          - string
          - "null"

validation_rules:
  - name: baseline_is_source_of_truth
    description: This artifact is the only canonical output of repo-structure for downstream semantic consumers.

  - name: facts_must_be_evidence_bound
    description: Every accepted fact must carry at least one evidence item.

  - name: conflicts_must_remain_visible
    description: Unresolved conflicts must not be silently dropped.

  - name: source_versions_required
    description: The baseline must record which upstream artifacts were fused.

  - name: repo_snapshot_required
    description: The baseline must describe one explicit repo snapshot.

  - name: provenance_should_exist_for_accepted_facts
    description: Accepted facts should preserve arbitration provenance when available.

normalization_hints:
  - facts are frozen outputs after validation and arbitration, not raw worker outputs.
  - conflicts may coexist with accepted facts.
  - architect_augment may be empty in source_versions if optional architecture docs were absent, but the field must still exist.
  - lineage is optional but recommended for traceability across reruns.

examples:
  - baseline_version: facts.v3
    repo_snapshot_commit: abc123
    generated_at: 2026-03-22T14:30:00Z
    snapshot:
      snapshot_version: sf-2026-03-22.1
      snapshot_id: sf-2026-03-22.1-abc123
    source_versions:
      hotspot_map:
        artifact: hotspot_map.v5.yaml
        version: v5
        repo_snapshot_commit: abc123
      codebase_map:
        artifact: codebase_map.v3.yaml
        version: v3
        repo_snapshot_commit: abc123
      architect_augment:
        artifact: architect_augment.v2.yaml
        version: v2
        repo_snapshot_commit: abc123
    facts:
      - fact_id: baseline-001
        fact_type: dependency_rule
        subject: lower layers
        predicate: must_not_depend_on
        object: service orchestration code
        statement: Lower layers must not depend on service orchestration code.
        confidence: confirmed
        repo_snapshot_commit: abc123
        source:
          source_type: codebase
          source_artifact: codebase_map.v3.yaml
        evidence:
          - source_doc: CONVENTIONS
            section_title: Layering Rules
            section_path: CONVENTIONS/Layering Rules
            locator_type: section_ref
            locator: CONVENTIONS/Layering Rules
            stable_ref: section:CONVENTIONS::CONVENTIONS/Layering Rules
            rationale: The section explicitly defines this dependency rule.
        status: active
        notes: null
        provenance:
          selected_from:
            - codebase_map.v3.yaml#fact-017
          arbitration_reason: selected as highest-quality current-snapshot fact with direct rule evidence
    conflicts:
      - conflict_id: conflict-001
        repo_snapshot_commit: abc123
        conflict_type: source_priority_tie
        facts:
          - fact_id: hotspot-044
            source_type: hotspot
            source_artifact: hotspot_map.v5.yaml
            statement: Operator registration is a recurring hotspot around macro enforcement.
            stable_refs:
              - symbol:ops/registry.h::REGISTER_OPERATOR
          - fact_id: architect-009
            source_type: architect
            source_artifact: architect_augment.v2.yaml
            statement: Operator implementations are registered through REGISTER_OPERATOR.
            stable_refs:
              - symbol:ops/registry.h::REGISTER_OPERATOR
        resolution_status: preserved
        notes: overlap detected but semantic merge not lossless
    lineage:
      previous_baseline_version: facts.v2
      previous_snapshot_id: sf-2026-03-20.2-a91d2f
      change_summary: refreshed codebase and architect inputs for current repo snapshot
```

---

这版 `baseline_facts.schema.yaml` 有几个关键设计点：

### 1. `facts` 里允许带 `provenance`

因为 baseline 不是 raw extracted facts，而是 **经过 arbitration 选进来的事实**。
所以最好记录：

* 从哪些候选里选出来的
* 为什么选它

这对后面 debug 很有价值。

### 2. `conflicts` 独立挂出来

不是把冲突事实直接混在 `facts` 里。
这样 downstream 可以：

* 只消费 `facts`
* 或者同时读 `conflicts` 做人工审阅 / 高风险提示

### 3. `source_versions` 固化三路输入版本

这能让 `facts.vN.yaml` 真正成为 snapshot，而不只是一个大列表。

### 4. `architect_augment` 仍然必须占位

即使 architecture docs 缺失、它为空，也要在 `source_versions` 里出现。
这样 snapshot 结构才稳定。

---

到这里，你最小闭环的“文字 + prompt + schema”已经基本够了：

* `SKILL.md`
* `references/gotchas.md`
* `references/evidence-model.md`
* `prompts/extract_codebase.md`
* `prompts/augment_architect.md`
* `schemas/fact_entry.schema.yaml`
* `schemas/baseline_facts.schema.yaml`

再往下最值得补的，就是两个运行规则文件：

* `references/preflight-rules.md`
* `references/arbitration-rules.md`

我建议先补 `references/preflight-rules.md`。
