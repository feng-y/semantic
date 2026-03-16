# FACT Canonical Contract

**Purpose**: Define the strict schema contract for canonical FACT outputs

**Version**: 1.0
**Date**: 2026-03-16
**Status**: FROZEN (breaking changes require major version bump)

---

## Overview

This document defines the **canonical FACT schema contract** that semantic layer will consume. This contract is **frozen** - any breaking changes require a major version bump and migration path.

---

## Top-Level Schema

```yaml
fact_layer_version: string  # Required, format: "major.minor"
fact_type: "canonical"      # Required, literal value
repo_identity: object       # Required
modules: array              # Required
entrypoints: array          # Required
core_entities: array        # Required
configuration: array        # Required
dependencies: object        # Required
execution_flows: array      # Required
baseline_reference: object  # Optional (only if baseline exists)
metadata: object            # Required
```

### Schema Stability Guarantees

1. **Top-level keys are frozen**: Cannot add/remove/rename top-level keys without major version bump
2. **Required fields are frozen**: Cannot make required fields optional or vice versa
3. **Field types are frozen**: Cannot change field types (string → array, etc.)
4. **Evidence format is frozen**: `file:line` or `command:output` format is stable
5. **Version format is frozen**: `major.minor` semantic versioning

---

## Field-Level Contracts

### 1. repo_identity

**Purpose**: Observable repository metadata

**Schema**:
```yaml
repo_identity:
  name: string              # Required, repository name
  type: string              # Required, e.g., "claude-code-plugin"
  primary_language: string  # Required, e.g., "python"
  build_system: string      # Required, e.g., "pip"
  evidence: array[string]   # Required, file:line refs
```

**Stability**: FROZEN

**Evidence requirement**: All fields must have evidence refs

**Example**:
```yaml
repo_identity:
  name: "semantic-harness"
  type: "claude-code-plugin"
  primary_language: "python"
  build_system: "pip"
  evidence:
    - "manifest.yaml:target=claude-code"
    - "pyproject.toml:[project] section"
```

---

### 2. modules

**Purpose**: Observable code module structure

**Schema**:
```yaml
modules:
  - name: string            # Required, module name
    path: string            # Required, file path
    functions: array[string] # Required, function names
    evidence: string        # Required, file:line range
```

**Stability**: FROZEN

**Evidence requirement**: Each module must have file:line evidence

**Prohibited fields**:
- ❌ `responsibility` (interpretation)
- ❌ `role` (semantic abstraction)
- ❌ `used_by` (relationship analysis)
- ❌ `purpose` (interpretation)

**Example**:
```yaml
modules:
  - name: "artifact_writer"
    path: "src/artifact_writer.py"
    functions:
      - "write_versioned_artifact"
      - "get_latest_working_version_path"
      - "safe_write_artifact"
    evidence: "src/artifact_writer.py:1-520"
```

---

### 3. entrypoints

**Purpose**: Observable execution entry points

**Schema**:
```yaml
entrypoints:
  - name: string            # Required, entrypoint name
    type: string            # Required, e.g., "skill", "cli"
    location: string        # Required, file path
    command: string         # Required, command name
    evidence: string        # Required, file:line ref
```

**Stability**: FROZEN

**Evidence requirement**: Each entrypoint must have file:line evidence

**Prohibited fields**:
- ❌ `execution_flow` (interpretation)
- ❌ `purpose` (interpretation)

**Example**:
```yaml
entrypoints:
  - name: "semantic-discover"
    type: "skill"
    location: "skills/semantic-discover.skill"
    command: "discover"
    evidence: "skills/semantic-discover.skill:command=discover"
```

---

### 4. core_entities

**Purpose**: Observable data structures

**Schema**:
```yaml
core_entities:
  - name: string            # Required, entity name
    type: string            # Required, e.g., "dataclass", "protocol"
    defined_in: string      # Required, file path
    fields: array[string]   # Required, field names
    evidence: string        # Required, file:line ref
```

**Stability**: FROZEN

**Evidence requirement**: Each entity must have file:line evidence

**Prohibited fields**:
- ❌ `role` (semantic abstraction)
- ❌ `purpose` (interpretation)
- ❌ `used_by` (relationship analysis)

**Example**:
```yaml
core_entities:
  - name: "DiscoveryResult"
    type: "dataclass"
    defined_in: "src/discovery_executor.py"
    fields:
      - "status"
      - "steps"
      - "artifacts_written"
    evidence: "src/discovery_executor.py:@dataclass DiscoveryResult"
```

---

### 5. configuration

**Purpose**: Observable configuration values

**Schema**:
```yaml
configuration:
  - name: string            # Required, config name
    type: string            # Required, e.g., "yaml", "toml"
    location: string        # Required, file path
    loaded_by: string       # Required, loader description
    evidence: string        # Required, file:line ref
```

**Stability**: FROZEN

**Evidence requirement**: Each config must have file:line evidence

**Example**:
```yaml
configuration:
  - name: "manifest"
    type: "yaml"
    location: "manifest.yaml"
    loaded_by: "Claude Code plugin system"
    evidence: "manifest.yaml:1-20"
```

---

### 6. dependencies

**Purpose**: Observable import and package dependencies

**Schema**:
```yaml
dependencies:
  internal_imports: array[object]  # Required
  external_packages: array[object] # Required
```

**Internal import schema**:
```yaml
- from_module: string     # Required, source module
  imports: array[string]  # Required, imported names
  evidence: string        # Required, file:line ref
```

**External package schema**:
```yaml
- package: string         # Required, package name
  version: string         # Optional, version constraint
  evidence: string        # Required, file:line ref
```

**Stability**: FROZEN

**Example**:
```yaml
dependencies:
  internal_imports:
    - from_module: "artifact_writer"
      imports: ["write_versioned_artifact", "get_latest_working_version_path"]
      evidence: "src/discovery_executor.py:5"
  external_packages:
    - package: "pytest"
      version: ">=8.0.0"
      evidence: "pyproject.toml:dependencies"
```

---

### 7. execution_flows

**Purpose**: Observable execution sequences

**Schema**:
```yaml
execution_flows:
  - name: string            # Required, flow name
    entrypoint: string      # Required, starting entrypoint
    steps: array[object]    # Required, execution steps
    evidence: string        # Required, file:line refs
```

**Step schema**:
```yaml
- module: string          # Required, module name
  function: string        # Required, function name
  evidence: string        # Required, file:line ref
```

**Stability**: FROZEN

**Prohibited fields**:
- ❌ `purpose` (interpretation)
- ❌ `inputs_interpretation` (semantic abstraction)
- ❌ `outputs_interpretation` (semantic abstraction)

**Example**:
```yaml
execution_flows:
  - name: "discover_flow"
    entrypoint: "semantic-discover"
    steps:
      - module: "dispatcher"
        function: "dispatch_command"
        evidence: "src/dispatcher.py:45"
      - module: "discovery_executor"
        function: "run_discovery"
        evidence: "src/discovery_executor.py:120"
    evidence: "skills/semantic-discover.skill + src/dispatcher.py + src/discovery_executor.py"
```

---

### 8. baseline_reference

**Purpose**: Observable baseline metadata (only if baseline exists)

**Schema**:
```yaml
baseline_reference:
  checkpoint_metadata: object  # Required
  baseline_files: array[string] # Required
  source_versions: object      # Required
```

**Checkpoint metadata schema**:
```yaml
checkpoint_metadata:
  timestamp: string         # Required, ISO 8601 format
  feedback_hash: string     # Required, hash of architect feedback
  evidence: string          # Required, file path
```

**Stability**: FROZEN

**Example**:
```yaml
baseline_reference:
  checkpoint_metadata:
    timestamp: "2026-03-16T10:00:00Z"
    feedback_hash: "a1b2c3d4e5f6"
    evidence: "docs/fact/baseline/checkpoint.json"
  baseline_files:
    - "purpose.md"
    - "pipelines.md"
    - "domains.md"
    - "concepts.md"
  source_versions:
    repo-understanding: 2
    knowledge-confidence: 1
    domain-candidates: 1
    review-summary: 1
```

---

### 9. metadata

**Purpose**: Canonical metadata for agent consumption

**Schema**:
```yaml
metadata:
  fact_layer_complete: boolean    # Required
  semantic_layer_ready: boolean   # Required
  demand_layer_ready: boolean     # Required
  generation_timestamp: string    # Required, ISO 8601
  evidence_count: integer         # Required
```

**Stability**: FROZEN

**Example**:
```yaml
metadata:
  fact_layer_complete: true
  semantic_layer_ready: false
  demand_layer_ready: false
  generation_timestamp: "2026-03-16T10:00:00Z"
  evidence_count: 127
```

---

## Evidence Format Contract

### File Evidence

**Format**: `file_path:line_number` or `file_path:line_start-line_end`

**Examples**:
- `src/artifact_writer.py:45`
- `src/artifact_writer.py:45-67`
- `manifest.yaml:target=claude-code`

**Stability**: FROZEN

### Command Evidence

**Format**: `command:output_description`

**Examples**:
- `git ls-files:237 files`
- `pytest:237 tests passed`

**Stability**: FROZEN

---

## Version Contract

### Semantic Versioning

**Format**: `major.minor`

**Rules**:
1. **Major version bump**: Breaking changes to schema (add/remove/rename top-level keys, change field types)
2. **Minor version bump**: Non-breaking additions (new optional fields, new evidence formats)

**Current version**: `1.0`

**Stability**: FROZEN

---

## Prohibited Content

The following content is **strictly prohibited** in canonical facts:

### 1. Interpretation Language

❌ "purpose", "role", "responsibility", "intent", "meaning"

**Why**: These are semantic abstractions, not observable facts

**Where it goes**: Working summary

### 2. Relationship Analysis

❌ "used_by", "depends_on", "related_to", "part_of"

**Why**: These are semantic relationships, not observable structure

**Where it goes**: Working summary

### 3. Domain Proposals

❌ "domain", "boundary", "grouping", "cluster"

**Why**: Domain identification is semantic work

**Where it goes**: Working summary

### 4. Confidence Ratings

❌ "confidence", "certainty", "trust_level"

**Why**: Confidence is metadata, not fact content

**Where it goes**: Working summary (as metadata)

### 5. Open Questions

❌ "unclear", "uncertain", "question", "assumption"

**Why**: Questions are working context, not facts

**Where it goes**: Working summary

### 6. Future-Oriented Content

❌ "should", "could", "might", "will", "plan"

**Why**: Future plans are not observable facts

**Where it goes**: Demand layer (future)

---

## Validation Rules

### 1. Evidence Requirement

**Rule**: Every claim must have evidence

**Validation**:
```python
def validate_evidence(claim: dict) -> bool:
    return "evidence" in claim and claim["evidence"]
```

### 2. Observable-Only Requirement

**Rule**: No interpretation language allowed

**Validation**:
```python
PROHIBITED_WORDS = ["purpose", "role", "responsibility", "used_by", "confidence"]

def validate_observable_only(claim: dict) -> bool:
    text = json.dumps(claim).lower()
    return not any(word in text for word in PROHIBITED_WORDS)
```

### 3. Structure Stability Requirement

**Rule**: Top-level keys must match schema

**Validation**:
```python
REQUIRED_KEYS = ["fact_layer_version", "fact_type", "repo_identity", "modules",
                 "entrypoints", "core_entities", "configuration", "dependencies",
                 "execution_flows", "metadata"]

def validate_structure(canonical: dict) -> bool:
    return all(key in canonical for key in REQUIRED_KEYS)
```

---

## Migration Path

### Breaking Changes

If breaking changes are required:

1. **Bump major version**: `1.0` → `2.0`
2. **Document changes**: List all breaking changes
3. **Provide migration script**: Convert `1.0` → `2.0`
4. **Deprecation period**: Support `1.0` for N releases

### Non-Breaking Changes

If non-breaking additions are needed:

1. **Bump minor version**: `1.0` → `1.1`
2. **Add optional fields**: New fields must be optional
3. **Backward compatible**: `1.0` consumers can still parse `1.1`

---

## Semantic Layer Consumption Contract

### What Semantic Layer Can Assume

1. **Structure stability**: Top-level keys will not change
2. **Evidence presence**: All claims have evidence refs
3. **Observable-only**: No interpretation mixed in (semantic can filter if needed)
4. **Version tracking**: All artifacts have version numbers
5. **Immutable baseline**: Accepted baseline will not auto-change

### What Semantic Layer Must Handle

1. **Evidence filtering**: Semantic must extract facts and ignore evidence refs (for human audit)
2. **Version resolution**: Semantic must handle version numbers and checkpoints
3. **Baseline detection**: Semantic must check if baseline exists before consuming

---

## Summary

**Canonical contract is FROZEN**. This schema is the stable foundation for semantic layer consumption. Any breaking changes require major version bump and migration path.

**Key principles**:
1. Observable facts only
2. Evidence required for all claims
3. No interpretation, abstraction, or semantic judgment
4. Stable structure for long-term consumption
5. Version tracked for evolution

---

**Contract version**: 1.0
**Status**: FROZEN
**Last updated**: 2026-03-16
