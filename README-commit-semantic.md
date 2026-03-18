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

# Verify installation
python skills/commit-semantic-collect/run.py --help
python skills/commit-semantic-generate/run.py --help
python skills/commit-semantic-export/run.py --help
```

## Three-Step Pipeline

**Command Format**: These are Python scripts that can be invoked as shell commands or as Claude Code skills (with `/` prefix).

### 1. Collect Cases

Extract and group commits into semantic cases:

```bash
# Shell command
python skills/commit-semantic-collect/run.py /path/to/repo --commit-range HEAD~50..HEAD

# Or as Claude Code skill
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
# Shell command
python skills/commit-semantic-generate/run.py --input-dir data/semantic_case_inputs

# Or as Claude Code skill
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
# Shell command
python skills/commit-semantic-export/run.py --input-dir data/semantic_cases

# Or as Claude Code skill
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
python skills/commit-semantic-collect/run.py . --commit-range HEAD~10..HEAD
python skills/commit-semantic-generate/run.py --input-dir data/semantic_case_inputs
python skills/commit-semantic-export/run.py --input-dir data/semantic_cases
cat data/exports/summary.json
```

### Full History Scan

```bash
python skills/commit-semantic-collect/run.py . --commit-range HEAD~500..HEAD
python skills/commit-semantic-generate/run.py --input-dir data/semantic_case_inputs
python skills/commit-semantic-export/run.py --input-dir data/semantic_cases
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

### High invalid rate

**Symptom**: Many cases in `invalid_cases/` directory.

**Diagnosis**:
```bash
# Check validation errors
ls data/invalid_cases/
cat data/invalid_cases/case_*.yaml | grep -A 5 "validation_error"
```

**Common causes and fixes**:
- **Prefix mismatch**: issue_text prefix doesn't match development_type
  - Fix: Ensure issue_text starts with correct prefix (feat:, bugfix:, refactor:, migration:, optimize:)
- **Generic rules/invariants**: Rules contain generic guidelines like "add null checks"
  - Fix: Rewrite rules to be object-specific semantic constraints
- **Missing required fields**: commit_log, issue_text, or development_type missing
  - Fix: Check prompt outputs and ensure all fields are generated

### Pattern explosion (>30 patterns)

**Symptom**: `summary.json` shows >30 patterns in a domain.

**Diagnosis**:
```bash
# Check pattern count per domain
jq '.pattern_stats' data/exports/summary.json
jq '.alerts' data/exports/summary.json
```

**Fixes**:
- Review object_class inference logic in `src/commit_semantic/p4/patterning.py`
- Consider broader object categories (merge similar classes)
- Verify deduplication is working: check `duplicates.jsonl` for missed duplicates
- Adjust similarity threshold in export configuration

### Low semantic value cases

**Symptom**: Many cases in `low_value_cases/` directory.

**Diagnosis**:
```bash
# Review low value cases
ls data/low_value_cases/ | wc -l
cat data/low_value_cases/case_*.yaml | grep "semantic_value"
```

**Expected behavior**: Low-value filtering is working correctly for:
- Format/lint/import/comment-only changes
- Trivial test maintenance
- Trivial config/flag wiring
- Low-information parameter tweaks

**Action**: This is expected for maintenance-heavy repositories. No fix needed unless filtering is too aggressive.

### Empty output directories

**Symptom**: No files generated in expected output directories.

**Diagnosis**:
```bash
# Check if commits were found
python skills/commit-semantic-collect/run.py . --commit-range HEAD~10..HEAD
# Look for "Found N commits" message
```

**Fixes**:
- Verify commit range is valid: `git log HEAD~10..HEAD`
- Check path filters aren't excluding all files
- Verify repository path is correct
- Check for errors in console output

## More Information

- **Integration Guide**: `docs/commit-semantic-integration.md` (comprehensive)
- **P0 Specification**: `docs/plan/git-semantic-p0.md` (design principles)
- **E2E Test**: `test_commit_semantic_e2e.py` (example usage)
