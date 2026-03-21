#!/usr/bin/env python3
"""
Test executor integration for commit-semantic-generate.

This test verifies that the prompt_runner can work with a mock executor.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.prompt_runner import (
    extract_yaml_from_response,
    generate_commit_log,
    generate_issue_text,
    generate_rules_invariants,
    run_prompt_with_claude,
)


def mock_executor(prompt: str) -> str:
    """
    Mock executor that returns sample YAML responses.

    In real usage, this would be provided by Claude Code host environment.
    """
    # Detect which prompt is being called based on the prompt title
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
        # Fallback for unknown prompts
        return """```yaml
error: unknown prompt type
```"""


def test_extract_yaml():
    """Test YAML extraction from response."""
    print("Testing YAML extraction...")

    # Test with code block
    response1 = """```yaml
key: value
```"""
    result1 = extract_yaml_from_response(response1)
    assert "key: value" in result1
    print("  ✓ Code block extraction works")

    # Test without code block
    response2 = "key: value"
    result2 = extract_yaml_from_response(response2)
    assert "key: value" in result2
    print("  ✓ Plain text extraction works")


def test_run_prompt_with_executor():
    """Test running prompt with mock executor."""
    print("\nTesting prompt execution with mock executor...")

    # Use a prompt that will match our mock executor
    prompt = "# Generate Commit Log\n\ngenerate_commit_log for testing"
    input_data = {
        "case_id": "test_001",
        "files": ["parser.py", "test_parser.py"]
    }

    result = run_prompt_with_claude(prompt, input_data, mock_executor)

    assert "commit_log" in result
    assert "parser" in result["commit_log"] or "legacy" in result["commit_log"]
    print("  ✓ Prompt execution works")
    print(f"  Result: {result['commit_log'][:50]}...")


def test_generate_functions():
    """Test the three generate functions."""
    print("\nTesting generate functions...")

    case_input = {
        "case_id": "test_001",
        "commit_id": "abc123",
        "module": "parser",
        "files": ["parser.py", "test_parser.py"],
        "diff_chunks": ["+ boundary check"],
        "related_tests": ["test_parser.py"]
    }

    # Test generate_commit_log
    print("  Testing generate_commit_log...")
    commit_log = generate_commit_log(case_input, mock_executor)
    assert isinstance(commit_log, str)
    assert len(commit_log) > 0
    print(f"    ✓ commit_log: {commit_log[:50]}...")

    # Test generate_rules_invariants
    print("  Testing generate_rules_invariants...")
    try:
        rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor)
        assert "rules" in rules_inv
        assert "invariants" in rules_inv
        assert isinstance(rules_inv["rules"], list)
        assert isinstance(rules_inv["invariants"], list)
        print(f"    ✓ rules: {len(rules_inv['rules'])} items")
        print(f"    ✓ invariants: {len(rules_inv['invariants'])} items")
    except Exception as e:
        print(f"    ✗ Error: {e}")
        # Debug: print what we got
        from src.commit_semantic.prompt_runner import (
            load_prompt,
            run_prompt_with_claude,
        )
        prompt = load_prompt("generate_rules_invariants")
        input_with_log = case_input.copy()
        input_with_log['commit_log'] = commit_log
        result = run_prompt_with_claude(prompt, input_with_log, mock_executor)
        print(f"    Debug - result keys: {result.keys()}")
        print(f"    Debug - result: {result}")
        raise

    # Test generate_issue_text
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
    print(f"    ✓ issue_text: {issue['issue_text'][:50]}...")
    print(f"    ✓ development_type: {issue['development_type']}")


def test_without_executor():
    """Test that it raises error without executor."""
    print("\nTesting error handling without executor...")

    try:
        run_prompt_with_claude("test", {}, None)
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError as e:
        assert "No executor provided" in str(e)
        print("  ✓ Correctly raises error without executor")


def main():
    """Run all tests."""
    print("=== Testing Commit Semantic Executor Integration ===\n")

    try:
        test_extract_yaml()
        test_run_prompt_with_executor()
        test_generate_functions()
        test_without_executor()

        print("\n=== All Tests Passed ✓ ===")
        print("\nIntegration verified:")
        print("  - YAML extraction works")
        print("  - Executor interface works")
        print("  - All generate functions work")
        print("  - Error handling works")
        print("\nReady for Claude Code host integration!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
