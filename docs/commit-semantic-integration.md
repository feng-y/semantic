# commit-semantic Integration Guide

## Overview

commit-semantic is a historical code change semantic extraction system that transforms git commit history into structured semantic cases for requirements understanding, case retrieval, few-shot learning, and offline training data construction.

### System Goals

- Extract semantic cases from repository commit history
- Generate structured semantic samples with rules, invariants, and issue descriptions
- Perform strict deduplication and high-frequency pattern aggregation
- Output high-cohesion, low-noise case and pattern libraries

### Core Principle

**semantic_case is the fundamental unit** - not commits, not individual change blocks. A semantic_case is an independently viable semantic package that can be compressed into a single, short, single-subject issue_text.

## Architecture

### Three-Skill Pipeline

The system exposes exactly three external skills:

1. **collect_cases** - Extract and group commits into semantic cases
2. **generate_case_semantics** - Generate structured semantic fields
3. **export_cases** - Deduplicate, aggregate patterns, and export

```
git history → collect_cases → semantic_case_inputs/
                                      ↓
                              generate_case_semantics
                                      ↓
                              semantic_cases/ + invalid_cases/ + low_value_cases/
                                      ↓
                              export_cases
                                      ↓
                              exports/ (cases.jsonl, duplicates.jsonl, patterns.jsonl, summary.json)
```

### P4 Architecture (Pattern Processing Pipeline)

The export stage implements a four-phase pattern processing architecture:

1. **normalize.py** - Text normalization for deduplication and pattern extraction
2. **dedup.py** - Strict deduplication based on normalized keys
3. **patterning.py** - Pattern extraction with domain-aware aggregation
4. **export** - Final output generation with canonical selection

## Skills Usage

### 1. collect_cases

**Purpose**: Extract raw commits and construct semantic cases with evidence and hints.

**Input**:
- repo_path
- commit_range or commit_list
- Optional path filters, author filters, time windows

**Output**: `data/semantic_case_inputs/*.yaml`

```yaml
case_id: ...
commit_id: ...
module: ...
domain: ...
files: []
diff_chunks: []
related_tests: []

bugfix_evidence:
  weak: []
  medium: []
  strong: []

split_hints:
  too_many_files: false
  too_many_diff_themes: false
  mixed_feature_and_bugfix: false
  unrelated_objects_detected: false

semantic_value: medium  # high/medium/low
```

**Key Rules**:
- Commits are NOT issue units - semantic_case is the unit
- Same object changes group together
- Main logic + tests group together
- Config/flag/wiring/registration attach to main group
- Cleanup attaches to main group
- Only independent main actions create new groups
- bugfix_evidence is evidence pool, not final conclusion
- Low-value cases go to `data/low_value_cases/`

**Low-Value Cases**:
- Format/lint/import/comment only
- Trivial test maintenance
- Trivial config/flag wiring only
- Low-information parameter tweaks
- Fragmented changes that cannot form stable semantic packages

### 2. generate_case_semantics

**Purpose**: Generate structured semantic fields for each semantic case.

**Input**: `data/semantic_case_inputs/*.yaml`

**Output**: `data/semantic_cases/*.yaml` (valid) + `data/invalid_cases/*.yaml` (failed validation)

```yaml
case_id: ...
commit_id: ...
module: ...
domain: ...

commit_log: ...
issue_text: ...
development_type: ...

rules: []
invariants: []

split_suggestion:
  needs_split: false
  split_reasons: []

semantic_value: medium
```

**Internal Structure**: Uses exactly 3 prompts sequentially:

1. **generate_commit_log** - Expresses "what changed" (code modification action)
2. **generate_rules_invariants** - Extracts object semantic constraints and preservation items
3. **generate_issue_text** - Generates compressed single-subject issue description

**Key Rules**:
- commit_log: Only expresses "what changed", not issue-style, no rules/invariants language
- rules/invariants: Must be object-specific semantic constraints, NOT generic development guidelines
- issue_text: Must be short, single sentence, single subject
- development_type: Must match issue_text prefix (feat:, bugfix:, refactor:, migration:, optimize:)
- split_suggestion: Result of compression overflow, not a priori judgment
- bugfix: Determined by combined evidence (commit_log + rules/invariants + regression/restore/compatibility evidence)

### 3. export_cases

**Purpose**: Deduplicate, aggregate patterns, and export final assets.

**Input**: `data/semantic_cases/*.yaml`

**Output**:
- `data/exports/cases.jsonl` - Unique canonical cases
- `data/exports/duplicates.jsonl` - Duplicate groups with canonical references
- `data/exports/patterns.jsonl` - High-frequency patterns with variants
- `data/exports/summary.json` - Statistics and alerts

**Key Rules**:
- Strict deduplication happens at export stage (not in prompts, not via cache)
- Pattern aggregation happens at export stage
- No semantic field rewriting at export stage
- Canonical selection based on semantic_value, abstraction level, and stability

## Claude Code Integration

### Skill Invocation

```bash
# Collect semantic cases from git history
/commit-semantic-collect --repo-path /path/to/repo --commit-range HEAD~100..HEAD

# Generate semantic fields for collected cases
/commit-semantic-generate --input-dir data/semantic_case_inputs

# Export with deduplication and pattern aggregation
/commit-semantic-export --input-dir data/semantic_cases
```

### Execution Flow

1. Run collect_cases to extract and group commits
2. Review `data/semantic_case_inputs/` and `data/low_value_cases/`
3. Run generate_case_semantics to generate structured fields
4. Review `data/semantic_cases/` and `data/invalid_cases/`
5. Run export_cases to produce final assets
6. Review `data/exports/summary.json` for statistics and alerts

## Data Flow

### Directory Structure

```
data/
├── raw_commits/              # Raw commit data (internal)
├── semantic_case_inputs/     # Collected cases ready for generation
├── semantic_cases/           # Valid generated cases
├── low_value_cases/          # Low semantic value cases
├── invalid_cases/            # Failed validation cases
└── exports/                  # Final export outputs
    ├── cases.jsonl
    ├── duplicates.jsonl
    ├── patterns.jsonl
    └── summary.json
```

### Data Structures

**SemanticCaseInput** (after collect):
- case_id, commit_id, module, domain
- files, diff_chunks, related_tests
- bugfix_evidence (weak/medium/strong)
- split_hints (flags for potential split scenarios)
- semantic_value (high/medium/low)

**SemanticCaseOutput** (after generate):
- case_id, commit_id, module, domain
- commit_log (what changed)
- issue_text (compressed requirement)
- development_type (feature/bugfix/refactor/migration/optimize)
- rules (semantic constraints)
- invariants (preservation items)
- split_suggestion (needs_split + reasons)
- semantic_value

**Export Structures**:
- CaseRecord - Final case with dedup_key and pattern_id
- DedupGroup - Duplicate group with canonical case
- PatternGroup - Pattern with canonical case and variants
- ExportSummary - Statistics and alerts

## Validation Rules

### 1. development_type Validation

**Valid values**: feature, bugfix, refactor, migration, optimize

**Enforcement**: Enum validation in validators.py

### 2. issue_text Prefix Validation

**Required prefixes**:
- feature → feat：
- bugfix → bugfix：
- refactor → refactor：
- migration → migration：
- optimize → optimize：

**Enforcement**: Prefix must match development_type exactly

### 3. Split Consistency Validation

**Rule**: If needs_split=false, split_reasons must be empty

**Enforcement**: Consistency check in validators.py

### 4. commit_log Validation

**Forbidden**: commit_log must NOT use requirement-style prefixes (feat:, bugfix:, etc.)

**Rationale**: commit_log expresses "what changed", not requirements

### 5. rules/invariants Quality Validation

**Forbidden patterns** (generic development guidelines):
- null checks
- bounds checks
- exception handling
- input validation
- avoid crash
- thread-safety advice
- code style guidance
- defensive programming

**Required**: Must be object-specific semantic constraints around the modified object

**Examples**:
- ✓ "legacy syntax compatibility must be preserved during repair"
- ✓ "historical inputs remain parseable"
- ✗ "add null checks for safety"
- ✗ "handle exceptions properly"

## Pattern Extraction

### Deduplication (P4 Phase 2)

**Dedup Key Components**:
```
module + development_type + normalized_issue_text
```

**Important**: commit_log is NOT part of the dedup key. Same pattern applied to different objects/paths naturally has different commit_log.

**Normalization** (normalize.py):
- NFKC Unicode normalization
- Whitespace normalization
- ASCII lowercasing
- Conservative synonym mapping (修正→修复, 调整→优化, etc.)
- Optional number placeholder (<NUM>)

**Output**: `duplicates.jsonl` with canonical case selection

**Canonical Selection Criteria**:
1. Higher semantic_value (high > medium > low)
2. Clearer issue_text (moderate length ~18 chars preferred)
3. Stable case_id (deterministic)

### Pattern Aggregation (P4 Phase 3)

**Pattern Fingerprint**:
```
domain | development_type | action_class | object_class | constraint_class
```

**Action Classes**: fix, add, refactor, migrate, optimize, control, align, general

**Object Classes** (keep broad, <15 categories):
- parser
- request-response-alignment
- feature-extraction
- config-control
- registry
- compatibility-path
- concurrency-control
- demand-analysis
- semantic-processing
- general

**Constraint Classes** (can combine with +):
- compatibility
- alignment
- concurrency
- mapping
- contract
- migration
- boundedness
- validation
- none
- general

**Similarity Calculation**:
```
similarity = 0.5 * sequence_ratio + 0.3 * jaccard + 0.2 * constraint_ratio
```

- issue_text dominates (0.8 weight)
- constraint signature assists (0.2 weight)
- Default threshold: 0.50

**Output**: `patterns.jsonl` with canonical patterns and variants

**Canonical Pattern Selection**:
1. Higher semantic_value
2. More abstract but not vague issue_text (~16 chars preferred)
3. More stable rules/invariants (more is better)
4. Stable case_id

### Pattern Count Control

**Thresholds per domain**:
- <10: excellent (good)
- 10-20: acceptable (observe)
- 21-30: too_high (review abstraction)
- >30: critical (review abstraction and dedup)

**Alert**: If pattern count >20, summary.json includes alert with recommended action

## Validation Workflow

### Structure Validation
- Required fields present
- split_suggestion structure complete

### Type Validation
- commit_log, issue_text, development_type are strings
- rules, invariants are lists
- needs_split is boolean
- split_reasons is list

### Enum Validation
- development_type in {feature, bugfix, refactor, migration, optimize}

### Consistency Validation
- issue_text prefix matches development_type
- needs_split=false → split_reasons empty
- commit_log has no requirement-style prefixes
- rules/invariants not generic development guidelines

### Failure Handling
- Structure/type/enum failures → `invalid_cases/`
- Consistency failures → `invalid_cases/`
- Low semantic value → `low_value_cases/`

## Best Practices

### 1. Start Small
- Test with 10-20 commits first
- Review semantic_case_inputs before generating
- Review semantic_cases before exporting

### 2. Iterative Refinement
- Check invalid_cases for common failure patterns
- Adjust collection filters if needed
- Review pattern count alerts in summary.json

### 3. Quality Over Coverage
- System does NOT aim to cover all commits
- Focus on high semantic value cases
- Low-value cases are expected and acceptable

### 4. Pattern Count Monitoring
- Monitor pattern count per domain
- If >20 patterns in a domain, review abstraction level
- Consider whether dedup key needs adjustment

### 5. Canonical Selection
- Trust the canonical selection algorithm
- Canonical cases represent the pattern best
- Variants are preserved for reference

## Troubleshooting

### High Invalid Rate
- Check validation errors in invalid_cases/
- Common issues: prefix mismatch, generic rules/invariants
- Review prompt outputs for quality

### High Duplicate Rate
- Expected for similar changes across codebase
- Review duplicates.jsonl to verify dedup correctness
- Adjust normalization if needed

### Pattern Explosion (>30 patterns)
- Review object_class inference logic
- Consider broader object categories
- Check if dedup is working correctly

### Low Semantic Value Cases
- Review low_value_cases/ to understand filtering
- Adjust semantic_value thresholds if needed
- Expected for maintenance-heavy repositories

## Summary

commit-semantic provides a complete pipeline for extracting structured semantic knowledge from git history. The three-skill architecture (collect → generate → export) ensures clear separation of concerns, while the P4 pattern processing pipeline (normalize → dedup → pattern → export) produces high-quality, deduplicated case and pattern libraries.

Key success factors:
- Understand that semantic_case is the fundamental unit
- Trust the validation rules to filter low-quality outputs
- Monitor pattern counts and adjust abstraction as needed
- Focus on high semantic value cases, not coverage
- Use the export stage for deduplication and pattern aggregation
