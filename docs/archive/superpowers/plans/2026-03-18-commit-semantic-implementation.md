# Commit-Semantic System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the commit-semantic system for extracting structured semantic cases from git commit history

**Architecture:** Three-skill pipeline (collect → generate → export) with P4 modular architecture. Each skill is independent and produces validated outputs. The system extracts semantic_case units (not commits) and generates structured fields via Claude prompts.

**Tech Stack:** Python 3.10+, PyYAML, git CLI, Claude API (via host executor)

---

## Current State Analysis

**What's Complete:**
- ✅ All three skill run.py files with full implementation
- ✅ P4 architecture modules (normalize.py, dedup.py, patterning.py)
- ✅ Core utilities (types.py, io_utils.py, validators.py)
- ✅ Git utilities (git_utils.py)
- ✅ Grouping and semantic case builder (grouping.py, semantic_case_builder.py)
- ✅ Prompt runner with executor pattern (prompt_runner.py)
- ✅ Value classifier (value_classifier.py)
- ✅ Pattern extraction v2 wrapper (pattern_extraction_v2.py)
- ✅ Deduplication module (deduplication.py)
- ✅ All three prompt templates (generate_commit_log.md, generate_rules_invariants.md, generate_issue_text.md)
- ✅ All three SKILL.md files

**What Needs Work:**
- Missing: domain field in SemanticCaseInput (required by P4 patterning)
- Missing: Executor integration for Claude API calls
- Missing: End-to-end testing
- Missing: Data directory structure creation
- Missing: Integration testing between skills

---

## Task 1: Fix Type Definitions to Match P0 Specification

**Files:**
- Modify: `src/types.py:61-93`

According to git-semantic-p0.md (lines 234-257), both `SemanticCaseInput` and `SemanticCaseOutput` **must** include a `domain` field. Currently both are missing this required field.

- [ ] **Step 1: Add domain field to SemanticCaseInput**

```python
@dataclass
class SemanticCaseInput:
    case_id: str
    commit_id: str
    module: str
    domain: str  # REQUIRED by P0 spec (line 238)
    files: List[str]
    diff_chunks: List[str]
    related_tests: List[str] = field(default_factory=list)
    bugfix_evidence: BugfixEvidence = field(default_factory=BugfixEvidence)
    split_hints: SplitHints = field(default_factory=SplitHints)
    semantic_value: str = "medium"  # high/medium/low
```

- [ ] **Step 1b: Add domain field to SemanticCaseOutput**

```python
@dataclass
class SemanticCaseOutput:
    case_id: str
    commit_id: str
    module: str
    domain: str  # REQUIRED by P0 spec (line 250)
    commit_log: str
    issue_text: str
    development_type: DevelopmentType
    rules: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    split_suggestion: SplitSuggestion = field(default_factory=SplitSuggestion)
    semantic_value: str = "medium"
    dedup_key: str = ""
    pattern_id: str = ""
```

- [ ] **Step 2: Update semantic_case_builder.py to set domain**

Modify `src/commit_semantic/semantic_case_builder.py:115-124` and `src/commit_semantic/semantic_case_builder.py:143-154`:

```python
# In _merge_groups_into_case
return SemanticCaseInput(
    case_id=case_id,
    commit_id=commit_id,
    module=main_group.theme,
    domain=main_group.theme,  # Add this - use module as domain for now
    files=all_files,
    diff_chunks=all_diff_chunks,
    related_tests=related_tests,
    bugfix_evidence=bugfix_evidence,
    split_hints=split_hints
)

# In _create_case_from_group
return SemanticCaseInput(
    case_id=case_id,
    commit_id=commit_id,
    module=group.theme,
    domain=group.theme,  # Add this - use module as domain for now
    files=group.files,
    diff_chunks=group.diff_chunks,
    related_tests=related_tests,
    bugfix_evidence=bugfix_evidence,
    split_hints=split_hints
)
```

- [ ] **Step 3: Update io_utils.py serialization for both types**

Modify `src/io_utils.py:52-95`:

```python
def semantic_case_input_to_dict(case: SemanticCaseInput) -> Dict[str, Any]:
    """Convert SemanticCaseInput to dict for serialization."""
    return {
        'case_id': case.case_id,
        'commit_id': case.commit_id,
        'module': case.module,
        'domain': case.domain,  # Add this field
        'files': case.files,
        'diff_chunks': case.diff_chunks,
        'related_tests': case.related_tests,
        'bugfix_evidence': {
            'weak': case.bugfix_evidence.weak,
            'medium': case.bugfix_evidence.medium,
            'strong': case.bugfix_evidence.strong
        },
        'split_hints': {
            'too_many_files': case.split_hints.too_many_files,
            'too_many_diff_themes': case.split_hints.too_many_diff_themes,
            'mixed_feature_and_bugfix': case.split_hints.mixed_feature_and_bugfix,
            'unrelated_objects_detected': case.split_hints.unrelated_objects_detected
        },
        'semantic_value': case.semantic_value
    }


def semantic_case_output_to_dict(case: SemanticCaseOutput) -> Dict[str, Any]:
    """Convert SemanticCaseOutput to dict for serialization."""
    return {
        'case_id': case.case_id,
        'commit_id': case.commit_id,
        'module': case.module,
        'domain': case.domain,  # Add this field
        'commit_log': case.commit_log,
        'issue_text': case.issue_text,
        'development_type': case.development_type.value,
        'rules': case.rules,
        'invariants': case.invariants,
        'split_suggestion': {
            'needs_split': case.split_suggestion.needs_split,
            'split_reasons': case.split_suggestion.split_reasons
        },
        'semantic_value': case.semantic_value,
        'dedup_key': case.dedup_key,
        'pattern_id': case.pattern_id
    }
```

- [ ] **Step 4: Update generate skill to preserve domain field**

Modify `skills/commit-semantic-generate/run.py:62-72`:

```python
# Assemble final output
case_output = {
    'case_id': case_input['case_id'],
    'commit_id': case_input['commit_id'],
    'module': case_input['module'],
    'domain': case_input.get('domain', case_input['module']),  # Preserve domain from input
    'commit_log': commit_log,
    'issue_text': issue_result['issue_text'],
    'development_type': issue_result['development_type'],
    'rules': rules_invariants['rules'],
    'invariants': rules_invariants['invariants'],
    'split_suggestion': issue_result['split_suggestion']
}
```

- [ ] **Step 5: Run type check**

```bash
cd /Users/yan./git/3p/sematic-harness
python3 -m py_compile src/types.py src/commit_semantic/semantic_case_builder.py src/io_utils.py skills/commit-semantic-generate/run.py
```

Expected: No syntax errors

- [ ] **Step 6: Commit type fixes**

```bash
git add src/types.py src/commit_semantic/semantic_case_builder.py src/io_utils.py skills/commit-semantic-generate/run.py
git commit -m "fix(types): add domain field to match git-semantic-p0.md specification

- Add domain to SemanticCaseInput (P0 line 238)
- Add domain to SemanticCaseOutput (P0 line 250)
- Update serialization in io_utils.py
- Update semantic_case_builder.py to set domain
- Update generate skill to preserve domain

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Create Data Directory Structure

**Files:**
- Create: `data/` directory structure

- [ ] **Step 1: Create all required directories**

```bash
cd /Users/yan./git/3p/sematic-harness
mkdir -p data/raw_commits
mkdir -p data/semantic_case_inputs
mkdir -p data/semantic_cases
mkdir -p data/low_value_cases
mkdir -p data/invalid_cases
mkdir -p data/exports
```

Expected: All directories created

- [ ] **Step 2: Create .gitkeep files**

```bash
touch data/raw_commits/.gitkeep
touch data/semantic_case_inputs/.gitkeep
touch data/semantic_cases/.gitkeep
touch data/low_value_cases/.gitkeep
touch data/invalid_cases/.gitkeep
touch data/exports/.gitkeep
```

- [ ] **Step 3: Add .gitignore for data files**

Create `data/.gitignore`:

```
# Ignore all YAML and JSON files in data directories
*.yaml
*.yml
*.json
*.jsonl

# Keep directory structure
!.gitkeep
```

- [ ] **Step 4: Commit directory structure**

```bash
git add data/
git commit -m "feat(data): create directory structure for semantic case pipeline

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Create Executor Integration Layer

**Files:**
- Create: `src/commit_semantic/executor_bridge.py`

The prompt_runner expects an executor callable from the host environment. We need a bridge layer.

- [ ] **Step 1: Create executor bridge module**

Create `src/commit_semantic/executor_bridge.py`:

```python
"""
Executor bridge for Claude API integration.

This module provides the bridge between prompt_runner and the host
environment's Claude API executor.
"""

from typing import Callable, Optional


# Global executor reference (set by host environment)
_global_executor: Optional[Callable[[str], str]] = None


def set_executor(executor: Callable[[str], str]) -> None:
    """
    Set the global executor for prompt execution.

    Args:
        executor: Callable that takes a prompt string and returns response string
    """
    global _global_executor
    _global_executor = executor


def get_executor() -> Optional[Callable[[str], str]]:
    """Get the current global executor."""
    return _global_executor


def clear_executor() -> None:
    """Clear the global executor."""
    global _global_executor
    _global_executor = None
```

- [ ] **Step 2: Update generate skill to use executor bridge**

Modify `skills/commit-semantic-generate/run.py:14-21`:

```python
from src.commit_semantic.executor_bridge import get_executor, set_executor
```

Modify the main() function at line 136-155:

```python
def main():
    parser = argparse.ArgumentParser(description="Generate semantic fields for cases")
    parser.add_argument("--input-dir", default="data/semantic_case_inputs",
                       help="Input directory with semantic case inputs")
    parser.add_argument("--output-dir", default="data/semantic_cases",
                       help="Output directory for validated cases")
    parser.add_argument("--invalid-dir", default="data/invalid_cases",
                       help="Output directory for invalid cases")

    args = parser.parse_args()

    # Get executor from environment
    executor = get_executor()
    if executor is None:
        print("ERROR: No executor configured. This skill must be run from Claude Code.")
        print("The host environment should call set_executor() before running.")
        sys.exit(1)

    generate_semantics(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        invalid_dir=args.invalid_dir,
        executor=executor
    )
```

- [ ] **Step 3: Run syntax check**

```bash
python3 -m py_compile src/commit_semantic/executor_bridge.py skills/commit-semantic-generate/run.py
```

Expected: No syntax errors

- [ ] **Step 4: Commit executor bridge**

```bash
git add src/commit_semantic/executor_bridge.py skills/commit-semantic-generate/run.py
git commit -m "feat(executor): add executor bridge for Claude API integration

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Create End-to-End Test Script

**Files:**
- Create: `test_e2e_commit_semantic.py`

- [ ] **Step 1: Create test script**

Create `test_e2e_commit_semantic.py`:

```python
#!/usr/bin/env python3
"""
End-to-end test for commit-semantic pipeline.

Tests the full pipeline:
1. collect_cases: Extract semantic cases from git history
2. generate_case_semantics: Generate semantic fields (mocked)
3. export_cases: Export and deduplicate

This test uses a mock executor for prompt generation.
"""

import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from skills.commit_semantic_collect.run import collect_cases
from skills.commit_semantic_generate.run import generate_semantics
from skills.commit_semantic_export.run import export_cases
from src.commit_semantic.executor_bridge import set_executor


def mock_executor(prompt: str) -> str:
    """
    Mock executor for testing.
    Returns valid YAML responses based on prompt content.
    """
    if "generate_commit_log" in prompt:
        return """```yaml
commit_log: "修改解析器以支持新的DSL语法"
```"""
    elif "generate_rules_invariants" in prompt:
        return """```yaml
rules:
  - "解析器必须保持向后兼容"
  - "新语法不能破坏现有DSL"
invariants:
  - "解析结果结构保持稳定"
```"""
    elif "generate_issue_text" in prompt:
        return """```yaml
issue_text: "feat：添加新DSL语法支持"
development_type: "feature"
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    else:
        raise ValueError(f"Unknown prompt type")


def test_e2e_pipeline():
    """Test the full pipeline."""
    print("=" * 60)
    print("End-to-End Test: Commit-Semantic Pipeline")
    print("=" * 60)

    # Setup test directories
    test_data_dir = Path("test_data")
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)

    test_data_dir.mkdir()

    # Set mock executor
    set_executor(mock_executor)

    try:
        # Step 1: Collect cases
        print("\n[1/3] Collecting semantic cases from git history...")
        collect_cases(
            repo_path=".",
            commit_range="HEAD~5..HEAD",
            output_dir=str(test_data_dir / "semantic_case_inputs"),
            low_value_dir=str(test_data_dir / "low_value_cases")
        )

        # Check outputs
        inputs_dir = test_data_dir / "semantic_case_inputs"
        input_files = list(inputs_dir.glob("*.yaml"))
        print(f"✓ Generated {len(input_files)} semantic case inputs")

        if len(input_files) == 0:
            print("⚠ No cases generated - repository may have no recent commits")
            return True

        # Step 2: Generate semantics
        print("\n[2/3] Generating semantic fields...")
        generate_semantics(
            input_dir=str(test_data_dir / "semantic_case_inputs"),
            output_dir=str(test_data_dir / "semantic_cases"),
            invalid_dir=str(test_data_dir / "invalid_cases"),
            executor=mock_executor
        )

        # Check outputs
        cases_dir = test_data_dir / "semantic_cases"
        case_files = list(cases_dir.glob("*.yaml"))
        print(f"✓ Generated {len(case_files)} validated semantic cases")

        # Step 3: Export cases
        print("\n[3/3] Exporting and deduplicating...")
        export_cases(
            input_dir=str(test_data_dir / "semantic_cases"),
            output_dir=str(test_data_dir / "exports"),
            invalid_dir=str(test_data_dir / "invalid_cases"),
            low_value_dir=str(test_data_dir / "low_value_cases")
        )

        # Check exports
        exports_dir = test_data_dir / "exports"
        assert (exports_dir / "cases.jsonl").exists(), "cases.jsonl not found"
        assert (exports_dir / "duplicates.jsonl").exists(), "duplicates.jsonl not found"
        assert (exports_dir / "patterns.jsonl").exists(), "patterns.jsonl not found"
        assert (exports_dir / "summary.json").exists(), "summary.json not found"

        print("\n" + "=" * 60)
        print("✓ End-to-End Test PASSED")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
        print("\n✓ Cleaned up test data")


if __name__ == "__main__":
    success = test_e2e_pipeline()
    sys.exit(0 if success else 1)
```

- [ ] **Step 2: Make test executable**

```bash
chmod +x test_e2e_commit_semantic.py
```

- [ ] **Step 3: Run the test**

```bash
python3 test_e2e_commit_semantic.py
```

Expected: Test passes or reports no recent commits

- [ ] **Step 4: Commit test script**

```bash
git add test_e2e_commit_semantic.py
git commit -m "test(e2e): add end-to-end pipeline test with mock executor

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Create Integration Documentation

**Files:**
- Create: `docs/commit-semantic-integration.md`

- [ ] **Step 1: Create integration guide**

Create `docs/commit-semantic-integration.md`:

```markdown
# Commit-Semantic Integration Guide

## Overview

The commit-semantic system extracts structured semantic cases from git commit history through a three-skill pipeline.

## Architecture

```
git history → collect_cases → semantic_case_inputs/
                                      ↓
                              generate_case_semantics (Claude prompts)
                                      ↓
                              semantic_cases/
                                      ↓
                              export_cases → exports/
```

## Skills

### 1. commit-semantic-collect

Extracts semantic cases from git history.

**Usage:**
```bash
python3 skills/commit-semantic-collect/run.py <repo_path> [options]
```

**Options:**
- `--commit-range`: Commit range (e.g., HEAD~10..HEAD)
- `--author`: Filter by author
- `--since`: Filter by date (e.g., '2024-01-01')
- `--until`: Filter by date
- `--output-dir`: Output directory (default: data/semantic_case_inputs)
- `--low-value-dir`: Low value cases directory (default: data/low_value_cases)

**Outputs:**
- `data/semantic_case_inputs/*.yaml`: High/medium value semantic case inputs
- `data/low_value_cases/*.yaml`: Low value cases (format-only, trivial changes)

### 2. commit-semantic-generate

Generates semantic fields using Claude prompts.

**Usage:**
```bash
python3 skills/commit-semantic-generate/run.py [options]
```

**Options:**
- `--input-dir`: Input directory (default: data/semantic_case_inputs)
- `--output-dir`: Output directory (default: data/semantic_cases)
- `--invalid-dir`: Invalid cases directory (default: data/invalid_cases)

**Requirements:**
- Must be run from Claude Code environment
- Executor must be configured via `set_executor()`

**Outputs:**
- `data/semantic_cases/*.yaml`: Validated semantic cases
- `data/invalid_cases/*.yaml`: Cases that failed validation

### 3. commit-semantic-export

Exports validated cases with deduplication and pattern extraction.

**Usage:**
```bash
python3 skills/commit-semantic-export/run.py [options]
```

**Options:**
- `--input-dir`: Input directory (default: data/semantic_cases)
- `--output-dir`: Output directory (default: data/exports)
- `--invalid-dir`: Invalid cases directory (default: data/invalid_cases)
- `--low-value-dir`: Low value cases directory (default: data/low_value_cases)

**Outputs:**
- `data/exports/cases.jsonl`: Unique semantic cases
- `data/exports/duplicates.jsonl`: Duplicate groups
- `data/exports/patterns.jsonl`: High-frequency patterns
- `data/exports/summary.json`: Statistics and alerts

## Claude Code Integration

When running from Claude Code, the host environment must:

1. Import the executor bridge:
```python
from src.commit_semantic.executor_bridge import set_executor
```

2. Define an executor function:
```python
def claude_executor(prompt: str) -> str:
    # Call Claude API with prompt
    # Return response as string
    pass
```

3. Set the executor before running generate skill:
```python
set_executor(claude_executor)
```

4. Invoke the skill:
```python
# Via skill system
/commit-semantic-generate

# Or directly
python3 skills/commit-semantic-generate/run.py
```

## Data Flow

1. **RawCommit** → extracted from git history
2. **ChangeGroup** → grouped by file relationships
3. **SemanticCaseInput** → merged groups with evidence
4. **SemanticCaseOutput** → generated semantic fields
5. **Exports** → deduplicated and pattern-extracted

## Validation Rules

The system enforces strict validation:

- `development_type` must match `issue_text` prefix
- `commit_log` must not use requirement-style prefixes
- `rules/invariants` must not be generic development hygiene
- `split_suggestion` must be consistent with `needs_split`

## Pattern Extraction (P4)

Pattern fingerprint format:
```
domain|dev_type|action_class|object_class|constraint_class
```

Pattern count thresholds per domain:
- < 10: excellent
- 10-20: acceptable
- 21-30: too high (review abstraction)
- > 30: critical (review urgently)

## Testing

Run end-to-end test:
```bash
python3 test_e2e_commit_semantic.py
```

Run unit tests:
```bash
python3 test_p2_p3_implementation.py
```
```

- [ ] **Step 2: Commit documentation**

```bash
git add docs/commit-semantic-integration.md
git commit -m "docs(integration): add commit-semantic integration guide

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Create README for Quick Start

**Files:**
- Create: `README-commit-semantic.md`

- [ ] **Step 1: Create README**

Create `README-commit-semantic.md`:

```markdown
# Commit-Semantic System

Extract structured semantic cases from git commit history.

## Quick Start

### 1. Setup

Ensure Python 3.10+ and dependencies are installed:

```bash
pip install pyyaml
```

### 2. Collect Cases

Extract semantic cases from your repository:

```bash
python3 skills/commit-semantic-collect/run.py . --commit-range HEAD~20..HEAD
```

This creates:
- `data/semantic_case_inputs/*.yaml` - Cases ready for semantic generation
- `data/low_value_cases/*.yaml` - Low-value cases (format-only, trivial)

### 3. Generate Semantics (Claude Code Required)

From Claude Code, run:

```
/commit-semantic-generate
```

This generates:
- `data/semantic_cases/*.yaml` - Validated semantic cases
- `data/invalid_cases/*.yaml` - Cases that failed validation

### 4. Export Results

```bash
python3 skills/commit-semantic-export/run.py
```

This creates:
- `data/exports/cases.jsonl` - Unique cases
- `data/exports/duplicates.jsonl` - Duplicate groups
- `data/exports/patterns.jsonl` - High-frequency patterns
- `data/exports/summary.json` - Statistics

## What Gets Extracted

Each semantic case includes:

- `commit_log`: What was changed (factual)
- `issue_text`: Compressed requirement (single sentence)
- `development_type`: feature/bugfix/refactor/migration/optimize
- `rules`: Object-specific semantic constraints
- `invariants`: Properties that must be preserved
- `split_suggestion`: Whether case should be split

## Key Concepts

- **semantic_case**: The core unit (not commit or file)
- **change_group**: Related files grouped together
- **bugfix_evidence**: Weak/medium/strong evidence for bugfix classification
- **semantic_value**: high/medium/low quality classification
- **pattern**: High-frequency recurring requirement patterns

## Testing

Run end-to-end test:

```bash
python3 test_e2e_commit_semantic.py
```

## Documentation

See `docs/commit-semantic-integration.md` for detailed integration guide.

See `docs/plan/git-semantic-p0.md` for complete specification.
```

- [ ] **Step 2: Commit README**

```bash
git add README-commit-semantic.md
git commit -m "docs(readme): add quick start guide for commit-semantic system

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Acceptance Criteria

After completing all tasks, the system should:

1. ✅ Have complete type definitions with domain field
2. ✅ Have all data directories created
3. ✅ Have executor bridge for Claude API integration
4. ✅ Pass end-to-end test with mock executor
5. ✅ Have integration documentation
6. ✅ Have quick start README

The system is ready for production use when:

- All three skills run without errors
- End-to-end test passes
- Pattern extraction produces < 20 patterns per domain
- Validation pass rate > 80%
- Documentation is complete

## Notes

- The executor bridge pattern allows the system to work with any Claude API client
- Mock executor in tests demonstrates the expected interface
- P4 architecture (normalize, dedup, patterning) is already complete
- All prompts are already written and validated
- The system is designed for incremental processing (can run skills independently)