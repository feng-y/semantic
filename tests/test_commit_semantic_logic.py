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
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.commit_semantic.git_utils import get_commit_details, get_commit_list
from src.commit_semantic.grouping import detect_bugfix_evidence, extract_change_groups
from src.commit_semantic.semantic_case_builder import build_semantic_cases
from src.io_utils import load_yaml, save_yaml, semantic_case_input_to_dict
from src.types import DevelopmentType
from src.validators import ValidationError, validate_semantic_case


@pytest.fixture(scope="module")
def commit():
    """Provide a real commit with files from the current repo."""
    commits = get_commit_list(".", commit_range="HEAD~10..HEAD")
    for commit_id in commits:
        c = get_commit_details(".", commit_id)
        if len(c.files) > 0:
            return c
    pytest.skip("No commits with files found in HEAD~10..HEAD")


def mock_executor(prompt: str) -> str:
    """Mock executor for testing.

    Match on the prompt template header at the start of the prompt,
    not anywhere in the body (diff chunks may contain other prompt headers).
    """
    if prompt.startswith("# Generate Commit Log"):
        return """```yaml
commit_log: >
  在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。
```"""
    elif prompt.startswith("# Generate Rules and Invariants"):
        return """```yaml
rules:
  - legacy syntax compatibility must be preserved during repair
invariants:
  - historical inputs remain parseable
```"""
    elif prompt.startswith("# Generate Issue Text"):
        return """```yaml
issue_text: >
  bugfix：修复旧DSL写法边界检查
development_type: bugfix
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    else:
        return """```yaml
error: unknown prompt type
```"""


def test_git_utils():
    """Test git utility functions."""
    repo_path = "."
    commits = get_commit_list(repo_path, commit_range="HEAD~10..HEAD")
    assert len(commits) > 0, "Should find commits"

    found = None
    for commit_id in commits:
        c = get_commit_details(repo_path, commit_id)
        if len(c.files) > 0:
            found = c
            break

    assert found is not None, "Should find at least one commit with files"


def test_grouping(commit):
    """Test change grouping logic."""
    groups = extract_change_groups(commit)
    assert len(groups) > 0, "Should create at least one group"

    diff_text = '\n'.join(commit.diff_chunks)
    evidence = detect_bugfix_evidence(commit, diff_text)
    assert evidence is not None


def test_semantic_case_builder(commit):
    """Test semantic case building."""
    groups = extract_change_groups(commit)
    diff_text = '\n'.join(commit.diff_chunks)
    evidence = detect_bugfix_evidence(commit, diff_text)

    cases = build_semantic_cases(commit.commit_id, groups, evidence)
    assert len(cases) > 0, "Should create at least one semantic case"


def test_io_utils(commit):
    """Test IO utilities."""
    groups = extract_change_groups(commit)
    diff_text = '\n'.join(commit.diff_chunks)
    evidence = detect_bugfix_evidence(commit, diff_text)
    cases = build_semantic_cases(commit.commit_id, groups, evidence)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        for case in cases:
            case_dict = semantic_case_input_to_dict(case)
            output_file = tmpdir / f"{case.case_id}.yaml"
            save_yaml(case_dict, str(output_file))
            assert output_file.exists()

        loaded_cases = []
        for yaml_file in tmpdir.glob("*.yaml"):
            loaded = load_yaml(str(yaml_file))
            loaded_cases.append(loaded)
            assert "case_id" in loaded
            assert "files" in loaded

        assert len(loaded_cases) == len(cases)


def test_generate_semantics(commit):
    """Test semantic generation with mock executor."""
    from src.commit_semantic.prompt_runner import (
        generate_commit_log,
        generate_issue_text,
        generate_rules_invariants,
    )

    groups = extract_change_groups(commit)
    diff_text = '\n'.join(commit.diff_chunks)
    evidence = detect_bugfix_evidence(commit, diff_text)
    cases = build_semantic_cases(commit.commit_id, groups, evidence)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        case_dict = semantic_case_input_to_dict(cases[0])
        save_yaml(case_dict, str(tmpdir / f"{cases[0].case_id}.yaml"))
        case_input = load_yaml(str(tmpdir / f"{cases[0].case_id}.yaml"))

    commit_log = generate_commit_log(case_input, mock_executor)
    assert isinstance(commit_log, str)
    assert len(commit_log) > 0

    rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor)
    assert "rules" in rules_inv
    assert "invariants" in rules_inv

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


def test_validators(commit):
    """Test validation logic."""
    from src.commit_semantic.prompt_runner import (
        generate_commit_log,
        generate_issue_text,
        generate_rules_invariants,
    )

    groups = extract_change_groups(commit)
    diff_text = '\n'.join(commit.diff_chunks)
    evidence = detect_bugfix_evidence(commit, diff_text)
    cases = build_semantic_cases(commit.commit_id, groups, evidence)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        case_dict = semantic_case_input_to_dict(cases[0])
        save_yaml(case_dict, str(tmpdir / f"{cases[0].case_id}.yaml"))
        case_input = load_yaml(str(tmpdir / f"{cases[0].case_id}.yaml"))

    commit_log = generate_commit_log(case_input, mock_executor)
    rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor)
    issue = generate_issue_text(
        case_input, commit_log,
        rules_inv["rules"], rules_inv["invariants"],
        mock_executor
    )

    complete_case = {
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

    validate_semantic_case(complete_case)

    # Missing field
    invalid_case1 = complete_case.copy()
    del invalid_case1["commit_log"]
    with pytest.raises(ValidationError):
        validate_semantic_case(invalid_case1)

    # Invalid development_type
    invalid_case2 = complete_case.copy()
    invalid_case2["development_type"] = "invalid_type"
    with pytest.raises(ValidationError):
        validate_semantic_case(invalid_case2)

    # Inconsistent prefix
    invalid_case3 = complete_case.copy()
    invalid_case3["issue_text"] = "feat：新功能"
    invalid_case3["development_type"] = "bugfix"
    with pytest.raises(ValidationError):
        validate_semantic_case(invalid_case3)


def test_data_structures():
    """Test data structure definitions."""
    from src.types import (
        ChangeGroup,
        ChangeRole,
        RawCommit,
        SemanticCaseInput,
        SemanticCaseOutput,
    )

    commit = RawCommit(
        commit_id="abc123",
        author="test",
        timestamp="123456",
        files=["file.py"],
        diff_chunks=["diff"],
        related_tests=[]
    )
    assert commit.commit_id == "abc123"

    group = ChangeGroup(
        group_id="g1",
        theme="test",
        files=["file.py"],
        role=ChangeRole.PRIMARY
    )
    assert group.role == ChangeRole.PRIMARY

    case_input = SemanticCaseInput(
        case_id="c1",
        commit_id="abc123",
        module="test",
        files=["file.py"],
        diff_chunks=["diff"]
    )
    assert case_input.case_id == "c1"

    case_output = SemanticCaseOutput(
        case_id="c1",
        commit_id="abc123",
        module="test",
        commit_log="test log",
        issue_text="feat：test",
        development_type=DevelopmentType.FEATURE
    )
    assert case_output.development_type == DevelopmentType.FEATURE

    assert DevelopmentType.BUGFIX.value == "bugfix"
    assert ChangeRole.SUPPORTING.value == "supporting"


