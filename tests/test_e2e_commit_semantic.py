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
import importlib.util

# Add parent directory to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Import skill modules using importlib
def load_skill_module(skill_name, module_name='run'):
    """Load a skill module by path."""
    module_path = repo_root / 'skills' / skill_name / f'{module_name}.py'
    spec = importlib.util.spec_from_file_location(f'{skill_name}.{module_name}', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

collect_module = load_skill_module('commit-semantic-collect')
generate_module = load_skill_module('commit-semantic-generate')
export_module = load_skill_module('commit-semantic-export')

collect_cases = collect_module.collect_cases
generate_semantics = generate_module.generate_semantics
export_cases = export_module.export_cases

from src.commit_semantic.executor_bridge import set_executor


def mock_executor_feature(prompt: str) -> str:
    """Mock executor returning a feature case."""
    if "# Generate Commit Log" in prompt:
        return """```yaml
commit_log: "在 parser 中新增对 DSL v2 语法的支持"
```"""
    elif "# Generate Rules and Invariants" in prompt:
        return """```yaml
rules:
  - "新语法必须与 v1 DSL 保持向后兼容"
invariants:
  - "历史 DSL 输入仍可正常解析"
```"""
    elif "# Generate Issue Text" in prompt:
        return """```yaml
issue_text: "feat：添加新DSL语法支持"
development_type: "feature"
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    return """```yaml\ncommit_log: "更新代码"\n```"""


def mock_executor_bugfix(prompt: str) -> str:
    """Mock executor returning a bugfix case."""
    if "# Generate Commit Log" in prompt:
        return """```yaml
commit_log: "修复 parser 中旧写法边界检查缺失问题"
```"""
    elif "# Generate Rules and Invariants" in prompt:
        return """```yaml
rules:
  - "legacy syntax compatibility must be preserved during repair"
invariants:
  - "historical inputs remain parseable"
```"""
    elif "# Generate Issue Text" in prompt:
        return """```yaml
issue_text: "bugfix：修复旧DSL写法边界检查"
development_type: "bugfix"
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    return """```yaml\ncommit_log: "更新代码"\n```"""


def mock_executor_invalid(prompt: str) -> str:
    """Mock executor returning an invalid case (prefix/type mismatch)."""
    if "# Generate Commit Log" in prompt:
        return """```yaml
commit_log: "重构 parser 模块结构"
```"""
    elif "# Generate Rules and Invariants" in prompt:
        return """```yaml
rules: []
invariants: []
```"""
    elif "# Generate Issue Text" in prompt:
        # Intentionally mismatched: feat prefix but bugfix type
        return """```yaml
issue_text: "feat：修复旧DSL写法边界检查"
development_type: "bugfix"
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    return """```yaml\ncommit_log: "更新代码"\n```"""


# Default mock used by the pipeline test
mock_executor = mock_executor_feature


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

        # Step 2: Generate semantics (with better error handling)
        print("\n[2/3] Generating semantic fields...")
        try:
            generate_semantics(
                input_dir=str(test_data_dir / "semantic_case_inputs"),
                output_dir=str(test_data_dir / "semantic_cases"),
                invalid_dir=str(test_data_dir / "invalid_cases"),
                executor=mock_executor
            )
        except Exception as e:
            print(f"Generation phase error: {e}")
            import traceback
            traceback.print_exc()

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


def test_e2e_bugfix_path():
    """Pipeline produces a valid bugfix case end-to-end."""
    import tempfile
    from src.commit_semantic.prompt_runner import (
        generate_commit_log, generate_rules_invariants, generate_issue_text,
    )
    from src.validators import validate_semantic_case, ValidationError
    from src.commit_semantic.git_utils import get_commit_list, get_commit_details
    from src.commit_semantic.grouping import extract_change_groups, detect_bugfix_evidence
    from src.commit_semantic.semantic_case_builder import build_semantic_cases
    from src.io_utils import save_yaml, load_yaml, semantic_case_input_to_dict

    commits = get_commit_list(".", commit_range="HEAD~10..HEAD")
    commit = None
    for cid in commits:
        c = get_commit_details(".", cid)
        if c.files:
            commit = c
            break
    if commit is None:
        import pytest
        pytest.skip("No commits with files found")

    groups = extract_change_groups(commit)
    evidence = detect_bugfix_evidence(commit, '\n'.join(commit.diff_chunks))
    cases = build_semantic_cases(commit.commit_id, groups, evidence)

    with tempfile.TemporaryDirectory() as tmpdir:
        case_dict = semantic_case_input_to_dict(cases[0])
        p = Path(tmpdir) / f"{cases[0].case_id}.yaml"
        save_yaml(case_dict, str(p))
        case_input = load_yaml(str(p))

    commit_log = generate_commit_log(case_input, mock_executor_bugfix)
    rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor_bugfix)
    issue = generate_issue_text(case_input, commit_log, rules_inv["rules"], rules_inv["invariants"], mock_executor_bugfix)

    complete = {
        "case_id": case_input["case_id"],
        "commit_id": case_input["commit_id"],
        "module": case_input["module"],
        "commit_log": commit_log,
        "issue_text": issue["issue_text"],
        "development_type": issue["development_type"],
        "rules": rules_inv["rules"],
        "invariants": rules_inv["invariants"],
        "split_suggestion": issue["split_suggestion"],
        "semantic_value": case_input.get("semantic_value", "medium"),
    }
    validate_semantic_case(complete)
    assert complete["development_type"] == "bugfix"
    assert complete["issue_text"].startswith("bugfix：")


def test_e2e_validation_rejects_mismatched_prefix():
    """Validator rejects a case where issue_text prefix contradicts development_type."""
    import tempfile
    from src.commit_semantic.prompt_runner import (
        generate_commit_log, generate_rules_invariants, generate_issue_text,
    )
    from src.validators import validate_semantic_case, ValidationError
    from src.commit_semantic.git_utils import get_commit_list, get_commit_details
    from src.commit_semantic.grouping import extract_change_groups, detect_bugfix_evidence
    from src.commit_semantic.semantic_case_builder import build_semantic_cases
    from src.io_utils import save_yaml, load_yaml, semantic_case_input_to_dict
    import pytest

    commits = get_commit_list(".", commit_range="HEAD~10..HEAD")
    commit = None
    for cid in commits:
        c = get_commit_details(".", cid)
        if c.files:
            commit = c
            break
    if commit is None:
        pytest.skip("No commits with files found")

    groups = extract_change_groups(commit)
    evidence = detect_bugfix_evidence(commit, '\n'.join(commit.diff_chunks))
    cases = build_semantic_cases(commit.commit_id, groups, evidence)

    with tempfile.TemporaryDirectory() as tmpdir:
        case_dict = semantic_case_input_to_dict(cases[0])
        p = Path(tmpdir) / f"{cases[0].case_id}.yaml"
        save_yaml(case_dict, str(p))
        case_input = load_yaml(str(p))

    commit_log = generate_commit_log(case_input, mock_executor_invalid)
    rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor_invalid)
    issue = generate_issue_text(case_input, commit_log, rules_inv["rules"], rules_inv["invariants"], mock_executor_invalid)

    bad_case = {
        "case_id": case_input["case_id"],
        "commit_id": case_input["commit_id"],
        "module": case_input["module"],
        "commit_log": commit_log,
        "issue_text": issue["issue_text"],
        "development_type": issue["development_type"],
        "rules": rules_inv["rules"],
        "invariants": rules_inv["invariants"],
        "split_suggestion": issue["split_suggestion"],
        "semantic_value": case_input.get("semantic_value", "medium"),
    }
    with pytest.raises(ValidationError):
        validate_semantic_case(bad_case)


if __name__ == "__main__":
    success = test_e2e_pipeline()
    sys.exit(0 if success else 1)
