# commit-semantic Quick Start

Extract structured semantic knowledge from git commit history.

## What It Does

Transforms git commits into structured semantic cases with:
- **commit_log**: What changed (code modification action)
- **issue_text**: Compressed requirement description (e.g. `feat：HTTP 请求增加指数退避重试`)
- **rules/invariants**: Object-specific semantic constraints
- **development_type**: feature/bugfix/refactor/migration/optimize

## Setup

```bash
# Install dependencies
pip install -e .

# Create data directories
mkdir -p data/{raw_commits,grouped_changes,semantic_case_inputs,semantic_cases,low_value_cases,invalid_cases,exports}

# Verify installation
python skills/commit-semantic-collect/run.py --help
python skills/commit-semantic-generate/run.py --help
python skills/commit-semantic-export/run.py --help
```

## Usage

### Option A: Unified Pipeline Runner (one call)

```python
from src.commit_semantic.pipeline import run_pipeline

result = run_pipeline(
    repo_path=".",
    commit_range="HEAD~50..HEAD",
    executor=my_llm_executor,   # callable(prompt: str) -> str
    incremental=False,
    exclude_paths=["config/", "docs/"],
)
```

Supports `resume=True` (default) to skip already-completed stages via checkpoint file.
Supports `stages="collect,generate"` to run a subset of stages.

### Option B: Three-Step Pipeline (shell / Claude Code skills)

**Command Format**: Python scripts invocable as shell commands or as Claude Code skills (with `/` prefix).

#### 1. Collect Cases

```bash
# Shell
python skills/commit-semantic-collect/run.py /path/to/repo \
    --commit-range HEAD~50..HEAD \
    --exclude-paths config/ docs/ \
    --incremental --state-file data/.collect-state.json

# Claude Code skill
/commit-semantic-collect 最近 50 个 commit，排除 config 和 docs 目录
```

**Output**: `data/semantic_case_inputs/*.yaml`, low-value cases → `data/low_value_cases/`

#### 2. Generate Semantics

```bash
# Shell
python skills/commit-semantic-generate/run.py \
    --input-dir data/semantic_case_inputs

# Claude Code skill
/commit-semantic-generate
```

**Output**: `data/semantic_cases/*.yaml` (valid) + `data/invalid_cases/*.yaml` (failed)

#### 3. Export & Deduplicate

```bash
# Shell
python skills/commit-semantic-export/run.py \
    --input-dir data/semantic_cases \
    --incremental

# Claude Code skill
/commit-semantic-export
```

**Output**: `data/exports/`
- `cases.jsonl` — unique canonical cases
- `duplicates.jsonl` — duplicate groups
- `patterns.jsonl` — high-frequency patterns
- `summary.json` — statistics and alerts

## Key Concepts

### semantic_case is the Unit

Not commits, not individual changes. A semantic_case is an independently viable semantic package that can be compressed into a single, short issue_text.

### commit_log vs issue_text

- **commit_log**: "在 HTTP 客户端中增加指数退避重试逻辑"
- **issue_text**: `feat：HTTP 请求增加指数退避重试`

commit_log expresses what changed. issue_text is the compressed requirement.

### issue_text Prefix Format

Prefixes use **full-width colon `：`** (not ASCII `:`):

| development_type | prefix |
|-----------------|--------|
| feature | `feat：` |
| bugfix | `bugfix：` |
| refactor | `refactor：` |
| migration | `migration：` |
| optimize | `optimize：` |

### rules/invariants Must Be Object-Specific

✓ Good: `legacy syntax compatibility must be preserved during repair`
✗ Bad: `add null checks for safety` (generic guideline)

### Validation Rules

- `development_type` must match `issue_text` prefix
- `commit_log` cannot use requirement prefixes (`feat：`, `bugfix：`, etc.)
- `needs_split=false` requires empty `split_reasons`
- `rules`/`invariants` cannot be generic development guidelines

## Testing

```bash
# Run commit-semantic unit and logic tests
pytest tests/test_commit_semantic_logic.py tests/test_grouping_boundaries.py -v

# Run end-to-end pipeline test
pytest tests/test_e2e_commit_semantic.py -v
```

## Output Structure

```
data/
├── raw_commits/              # Raw git data
├── grouped_changes/          # Intermediate grouping
├── semantic_case_inputs/     # After collect
├── semantic_cases/           # After generate (valid)
├── low_value_cases/          # Low semantic value (filtered)
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

### Incremental Run (new commits only)

```bash
python skills/commit-semantic-collect/run.py . \
    --commit-range HEAD~10..HEAD \
    --incremental --state-file data/.collect-state.json
python skills/commit-semantic-generate/run.py --input-dir data/semantic_case_inputs
python skills/commit-semantic-export/run.py --input-dir data/semantic_cases --incremental
```

### Exclude Directories

```bash
python skills/commit-semantic-collect/run.py . \
    --commit-range HEAD~50..HEAD \
    --exclude-paths config/ deploy/ infra/
```

### Review Invalid Cases

```bash
ls data/invalid_cases/
cat data/invalid_cases/case_*.yaml | grep -A 5 "validation_error"
```

### Monitor Pattern Quality

```bash
jq '.pattern_stats' data/exports/summary.json
# Alert if >20 patterns per domain (review abstraction level)
```

## Troubleshooting

### High invalid rate

**Symptom**: Many cases in `invalid_cases/`.

**Common causes**:
- **Prefix mismatch**: `issue_text` prefix doesn't match `development_type`
  - Fix: ensure `issue_text` starts with the correct full-width prefix (`feat：`, `bugfix：`, etc.)
- **Generic rules/invariants**: rules contain guidelines like "add null checks"
  - Fix: rewrite rules to be object-specific semantic constraints
- **Missing required fields**: `commit_log`, `issue_text`, or `development_type` missing

### Pattern explosion (>30 patterns)

**Symptom**: `summary.json` shows >30 patterns in a domain.

**Fixes**:
- Review `object_class` inference in `src/commit_semantic/patterning.py`
- Consider broader object categories (merge similar classes)
- Check `duplicates.jsonl` for missed duplicates
- Adjust similarity threshold in export configuration

### Low semantic value cases

**Expected behavior**: low-value filtering is working correctly for format/lint/import-only changes, trivial test maintenance, trivial config wiring, and low-information parameter tweaks. No fix needed unless filtering is too aggressive.

### Empty output directories

**Diagnosis**:
```bash
git log HEAD~10..HEAD --oneline   # verify commit range
python skills/commit-semantic-collect/run.py . --commit-range HEAD~10..HEAD
```

## More Information

- **User Guide**: `docs/commit-semantic/user-guide.md`
- **Skills Reference**: `docs/commit-semantic/skills-reference.md`
- **Integration Guide**: `docs/commit-semantic-integration.md`
- **P0 Specification**: `docs/plan/git-semantic-p0.md`
- **E2E Test**: `tests/test_e2e_commit_semantic.py`
