#!/usr/bin/env python3
"""
End-to-end test for commit-semantic logic.

Tests the complete flow:
1. collect_cases - Extract semantic cases from git history
2. generate_case_semantics - Generate semantic fields
3. export_cases - Export and statistics
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.commit_semantic.git_utils import get_commit_list, get_commit_details
from src.commit_semantic.grouping import extract_change_groups, detect_bugfix_evidence
from src.commit_semantic.semantic_case_builder import build_semantic_cases
from src.io_utils import save_yaml, load_yaml, semantic_case_input_to_dict
from src.validators import validate_semantic_case, ValidationError
from src.types import DevelopmentType


def mock_executor(prompt: str) -> str:
    """Mock executor for testing."""
    if "Generate Rules and Invariants" in prompt:
        return """```yaml
rules:
  - legacy syntax compatibility must be preserved during repair
invariants:
  - historical inputs remain parseable
```"""
    elif "Generate Issue Text" in prompt:
        return """```yaml
issue_text: >
  bugfix：修复旧DSL写法边界检查
development_type: bugfix
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    elif "Generate Commit Log" in prompt:
        return """```yaml
commit_log: >
  在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。
```"""
    else:
        return """```yaml
error: unknown prompt type
```"""


def test_git_utils():
    """Test git utility functions."""
    print("\n=== Testing Git Utils ===")

    # Test with current repo
    repo_path = "."

    print("  Testing get_commit_list...")
    commits = get_commit_list(repo_path, commit_range="HEAD~10..HEAD")
    assert len(commits) > 0, "Should find commits"
    print(f"    ✓ Found {len(commits)} commits")

    print("  Testing get_commit_details...")
    # Find a commit with files
    commit = None
    for commit_id in commits:
        c = get_commit_details(repo_path, commit_id)
        if len(c.files) > 0:
            commit = c
            break

    assert commit is not None, "Should find at least one commit with files"
    print(f"    ✓ Commit {commit.commit_id[:8]} has {len(commit.files)} files")

    return commit.commit_id, commit


def test_grouping(commit):
    """Test change grouping logic."""
    print("\n=== Testing Change Grouping ===")

    print("  Testing extract_change_groups...")
    groups = extract_change_groups(commit)
    assert len(groups) > 0, "Should create at least one group"
    print(f"    ✓ Created {len(groups)} change group(s)")

    for i, group in enumerate(groups):
        print(f"    Group {i}: {group.theme}, {len(group.files)} files, role={group.role.value}")

    print("  Testing detect_bugfix_evidence...")
    diff_text = '\n'.join(commit.diff_chunks)
    evidence = detect_bugfix_evidence(commit, diff_text)
    print(f"    ✓ Evidence: weak={len(evidence.weak)}, medium={len(evidence.medium)}, strong={len(evidence.strong)}")

    return groups, evidence


def test_semantic_case_builder(commit_id, groups, evidence):
    """Test semantic case building."""
    print("\n=== Testing Semantic Case Builder ===")

    print("  Testing build_semantic_cases...")
    cases = build_semantic_cases(commit_id, groups, evidence)
    assert len(cases) > 0, "Should create at least one semantic case"
    print(f"    ✓ Built {len(cases)} semantic case(s)")

    for i, case in enumerate(cases):
        print(f"    Case {i}: {case.case_id}")
        print(f"      Module: {case.module}")
        print(f"      Files: {len(case.files)}")
        print(f"      Tests: {len(case.related_tests)}")
        print(f"      Split hints: too_many_files={case.split_hints.too_many_files}")

    return cases


def test_io_utils(cases):
    """Test IO utilities."""
    print("\n=== Testing IO Utils ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        print("  Testing save_yaml...")
        for case in cases:
            case_dict = semantic_case_input_to_dict(case)
            output_file = tmpdir / f"{case.case_id}.yaml"
            save_yaml(case_dict, str(output_file))
            assert output_file.exists()
        print(f"    ✓ Saved {len(cases)} YAML files")

        print("  Testing load_yaml...")
        loaded_cases = []
        for yaml_file in tmpdir.glob("*.yaml"):
            loaded = load_yaml(str(yaml_file))
            loaded_cases.append(loaded)
            assert "case_id" in loaded
            assert "files" in loaded
        print(f"    ✓ Loaded {len(loaded_cases)} YAML files")

        return loaded_cases


def test_generate_semantics(case_input):
    """Test semantic generation with mock executor."""
    print("\n=== Testing Semantic Generation ===")

    from src.commit_semantic.prompt_runner import (
        generate_commit_log,
        generate_rules_invariants,
        generate_issue_text
    )

    print("  Testing generate_commit_log...")
    commit_log = generate_commit_log(case_input, mock_executor)
    assert isinstance(commit_log, str)
    assert len(commit_log) > 0
    print(f"    ✓ Generated: {commit_log[:60]}...")

    print("  Testing generate_rules_invariants...")
    rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor)
    assert "rules" in rules_inv
    assert "invariants" in rules_inv
    print(f"    ✓ Rules: {len(rules_inv['rules'])}, Invariants: {len(rules_inv['invariants'])}")

    print("  Testing generate_issue_text...")
    issue = generate_issue_text(
        case_input,
        commit_log,
        rules_inv["rules"],
        rules_inv["invariants"],
        mock_executor
    )
    assert "issue_text" in issue
    assert "development_type" in issue
    assert "split_suggestion" in issue
    print(f"    ✓ Issue: {issue['issue_text'][:60]}...")
    print(f"    ✓ Type: {issue['development_type']}")

    # Assemble complete case
    complete_case = {
        "case_id": case_input["case_id"],
        "commit_id": case_input["commit_id"],
        "module": case_input["module"],
        "commit_log": commit_log,
        "issue_text": issue["issue_text"],
        "development_type": issue["development_type"],
        "rules": rules_inv["rules"],
        "invariants": rules_inv["invariants"],
        "split_suggestion": issue["split_suggestion"]
    }

    return complete_case


def test_validators(complete_case):
    """Test validation logic."""
    print("\n=== Testing Validators ===")

    print("  Testing validate_semantic_case...")
    try:
        validate_semantic_case(complete_case)
        print("    ✓ Validation passed")
    except ValidationError as e:
        print(f"    ✗ Validation failed: {e.reason}")
        raise

    # Test invalid cases
    print("  Testing validation failures...")

    # Missing field
    invalid_case1 = complete_case.copy()
    del invalid_case1["commit_log"]
    try:
        validate_semantic_case(invalid_case1)
        assert False, "Should fail on missing field"
    except ValidationError:
        print("    ✓ Correctly rejects missing field")

    # Invalid development_type
    invalid_case2 = complete_case.copy()
    invalid_case2["development_type"] = "invalid_type"
    try:
        validate_semantic_case(invalid_case2)
        assert False, "Should fail on invalid type"
    except ValidationError:
        print("    ✓ Correctly rejects invalid development_type")

    # Inconsistent prefix
    invalid_case3 = complete_case.copy()
    invalid_case3["issue_text"] = "feat：新功能"
    invalid_case3["development_type"] = "bugfix"
    try:
        validate_semantic_case(invalid_case3)
        assert False, "Should fail on inconsistent prefix"
    except ValidationError:
        print("    ✓ Correctly rejects inconsistent prefix")


def test_data_structures():
    """Test data structure definitions."""
    print("\n=== Testing Data Structures ===")

    from src.types import (
        RawCommit, ChangeGroup, SemanticCaseInput, SemanticCaseOutput,
        BugfixEvidence, SplitHints, SplitSuggestion,
        DevelopmentType, ChangeRole
    )

    print("  Testing RawCommit...")
    commit = RawCommit(
        commit_id="abc123",
        author="test",
        timestamp="123456",
        files=["file.py"],
        diff_chunks=["diff"],
        related_tests=[]
    )
    assert commit.commit_id == "abc123"
    print("    ✓ RawCommit works")

    print("  Testing ChangeGroup...")
    group = ChangeGroup(
        group_id="g1",
        theme="test",
        files=["file.py"],
        role=ChangeRole.PRIMARY
    )
    assert group.role == ChangeRole.PRIMARY
    print("    ✓ ChangeGroup works")

    print("  Testing SemanticCaseInput...")
    case_input = SemanticCaseInput(
        case_id="c1",
        commit_id="abc123",
        module="test",
        files=["file.py"],
        diff_chunks=["diff"]
    )
    assert case_input.case_id == "c1"
    print("    ✓ SemanticCaseInput works")

    print("  Testing SemanticCaseOutput...")
    case_output = SemanticCaseOutput(
        case_id="c1",
        commit_id="abc123",
        module="test",
        commit_log="test log",
        issue_text="feat：test",
        development_type=DevelopmentType.FEATURE
    )
    assert case_output.development_type == DevelopmentType.FEATURE
    print("    ✓ SemanticCaseOutput works")

    print("  Testing enums...")
    assert DevelopmentType.BUGFIX.value == "bugfix"
    assert ChangeRole.SUPPORTING.value == "supporting"
    print("    ✓ Enums work")


def main():
    """Run all tests."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Commit Semantic - Complete Logic Verification              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    try:
        # Test data structures
        test_data_structures()

        # Test git operations
        commit_id, commit = test_git_utils()

        # Test grouping
        groups, evidence = test_grouping(commit)

        # Test semantic case building
        cases = test_semantic_case_builder(commit_id, groups, evidence)

        # Test IO
        loaded_cases = test_io_utils(cases)

        # Test semantic generation
        complete_case = test_generate_semantics(loaded_cases[0])

        # Test validation
        test_validators(complete_case)

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║  ✓ All Logic Tests Passed                                   ║")
        print("╚══════════════════════════════════════════════════════════════╝")

        print("\n验证完成:")
        print("  ✓ 数据结构定义正确")
        print("  ✓ Git 操作正常")
        print("  ✓ 变更分组逻辑正确")
        print("  ✓ Semantic case 构建正确")
        print("  ✓ IO 操作正常")
        print("  ✓ 语义生成正确")
        print("  ✓ 校验逻辑正确")
        print("\ncommit-semantic 完整逻辑验证通过！")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
