# commit-semantic Quick Start

Extract structured semantic knowledge from git commit history.

## What It Does

Transforms git commits into structured semantic cases with:
- **commit_log**: What changed (code modification action)
- **issue_text**: Compressed requirement description
- **rules/invariants**: Object-specific semantic constraints
- **development_type**: feature/bugfix/refactor/migration/optimize

## Setup

```bash
# Install dependencies
pip install -e .

# Create data directories
mkdir -p data/{raw_commits,semantic_case_inputs,semantic_cases,low_value_cases,invalid_cases,exports}
```

## Three-Step Pipeline

### 1. Collect Cases

Extract and group commits into semantic cases:

```bash
/commit-semantic-collect --repo-path /path/to/repo --commit-range HEAD~50..HEAD
```

**Output**: `data/semantic_case_inputs/*.yaml`

**What it does**:
- Groups related changes (main logic + tests + config)
- Injects bugfix evidence (weak/medium/strong)
- Filters low-value cases (format-only, trivial changes)
- Outputs semantic_case units (not raw commits)

### 2. Generate Semantics

Generate structured fields for each case:

```bash
/commit-semantic-generate --input-dir data/semantic_case_inputs
```

**Output**: `data/semantic_cases/*.yaml` (valid) + `data/invalid_cases/*.yaml` (failed)

**What it does**:
- Generates commit_log (what changed)
- Extracts rules/invariants (object-specific constraints)
- Creates issue_text (single-subject requirement)
- Validates consistency (prefix matching, no generic rules)

### 3. Export & Deduplicate

Deduplicate and aggregate patterns:

```bash
/commit-semantic-export --input-dir data/semantic_cases
```

**Output**: `data/exports/`
- `cases.jsonl` - Unique canonical cases
- `duplicates.jsonl` - Duplicate groups
- `patterns.jsonl` - High-frequency patterns
- `summary.json` - Statistics and alerts

**What it does**:
- Strict deduplication (module + type + normalized issue_text)
- Pattern aggregation (domain + action + object + constraint)
- Canonical selection (highest semantic value + abstraction)
- Pattern count monitoring (alerts if >20 per domain)

## Key Concepts

### semantic_case is the Unit

Not commits, not individual changes. A semantic_case is an independently viable semantic package that can be compressed into a single, short issue_text.

### commit_log vs issue_text

- **commit_log**: "Added retry logic to HTTP client with exponential backoff"
- **issue_text**: "feat: add HTTP request retry with backoff"

commit_log expresses what changed. issue_text is the compressed requirement.

### rules/invariants Must Be Object-Specific

✓ Good: "legacy syntax compatibility must be preserved during repair"
✗ Bad: "add null checks for safety" (generic guideline)

### Validation Rules

- development_type must match issue_text prefix
- commit_log cannot use requirement prefixes (feat:, bugfix:, etc.)
- needs_split=false requires empty split_reasons
- rules/invariants cannot be generic development guidelines

## Testing

Run the end-to-end test:

```bash
pytest test_commit_semantic_e2e.py -v
```

This validates the full pipeline: collect → generate → export.

## Output Structure

```
data/
├── semantic_case_inputs/     # After collect
├── semantic_cases/           # After generate (valid)
├── low_value_cases/          # Low semantic value
├── invalid_cases/            # Failed validation
└── exports/                  # After export
    ├── cases.jsonl           # Unique cases
    ├── duplicates.jsonl      # Duplicate groups
    ├── patterns.jsonl        # Aggregated patterns
    └── summary.json          # Stats + alerts
```

## Common Workflows

### Quick Test (10 commits)

```bash
/commit-semantic-collect --repo-path . --commit-range HEAD~10..HEAD
/commit-semantic-generate --input-dir data/semantic_case_inputs
/commit-semantic-export --input-dir data/semantic_cases
cat data/exports/summary.json
```

### Full History Scan

```bash
/commit-semantic-collect --repo-path . --commit-range HEAD~500..HEAD
/commit-semantic-generate --input-dir data/semantic_case_inputs
/commit-semantic-export --input-dir data/semantic_cases
```

### Review Invalid Cases

```bash
ls data/invalid_cases/
# Check validation errors and adjust prompts if needed
```

### Monitor Pattern Quality

```bash
jq '.pattern_stats' data/exports/summary.json
# Check pattern_count per domain
# Alert if >20 patterns (review abstraction level)
```

## Troubleshooting

**High invalid rate**: Check `invalid_cases/` for common validation errors (prefix mismatch, generic rules).

**Pattern explosion (>30)**: Review object_class inference, consider broader categories.

**Low semantic value**: Review `low_value_cases/` to understand filtering. Expected for maintenance-heavy repos.

## More Information

- **Integration Guide**: `docs/commit-semantic-integration.md` (comprehensive)
- **P0 Specification**: `docs/plan/git-semantic-p0.md` (design principles)
- **E2E Test**: `test_commit_semantic_e2e.py` (example usage)
