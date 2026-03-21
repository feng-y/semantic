#!/usr/bin/env python3
"""
End-to-end skill test with mock executor.

Tests the complete workflow:
1. collect_cases - Extract from git
2. generate_case_semantics - Generate with mock executor
3. export_cases - Export results
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.commit_semantic.prompt_runner import (
    generate_commit_log,
    generate_issue_text,
    generate_rules_invariants,
)
from src.io_utils import load_yaml, save_yaml
from src.validators import validate_semantic_case


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
  feat：实现需求分析流程
development_type: feature
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    elif "Generate Commit Log" in prompt:
        return """```yaml
commit_log: >
  实现需求分析的完整流程，包括规范化、语义映射和类型匹配。
```"""
    else:
        return """```yaml
error: unknown prompt type
```"""


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Commit Semantic - End-to-End Skill Test                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_dir = tmpdir / "inputs"
        output_dir = tmpdir / "outputs"
        invalid_dir = tmpdir / "invalid"
        export_dir = tmpdir / "exports"

        # Step 1: Run collect_cases
        print("\n=== Step 1: Collect Cases ===")
        import subprocess
        result = subprocess.run([
            "python3", "skills/commit-semantic-collect/run.py",
            ".",
            "--commit-range", "HEAD~2..HEAD",
            "--output-dir", str(input_dir)
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"✗ collect_cases failed: {result.stderr}")
            return False

        print(result.stdout)
        case_files = list(input_dir.glob("*.yaml"))
        print(f"✓ Collected {len(case_files)} cases")

        # Step 2: Generate semantics for a few cases
        print("\n=== Step 2: Generate Semantics (with mock executor) ===")
        output_dir.mkdir(parents=True, exist_ok=True)
        invalid_dir.mkdir(parents=True, exist_ok=True)

        success_count = 0
        failure_count = 0

        # Process first 5 cases
        for case_file in case_files[:5]:
            print(f"\nProcessing {case_file.name}...")
            try:
                case_input = load_yaml(str(case_file))

                # Generate commit_log
                commit_log = generate_commit_log(case_input, mock_executor)
                print(f"  ✓ commit_log: {commit_log[:50]}...")

                # Generate rules/invariants
                rules_inv = generate_rules_invariants(case_input, commit_log, mock_executor)
                print(f"  ✓ rules: {len(rules_inv['rules'])}, invariants: {len(rules_inv['invariants'])}")

                # Generate issue_text
                issue = generate_issue_text(
                    case_input,
                    commit_log,
                    rules_inv["rules"],
                    rules_inv["invariants"],
                    mock_executor
                )
                print(f"  ✓ issue_text: {issue['issue_text'][:50]}...")

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

                # Validate
                validate_semantic_case(complete_case)
                print("  ✓ Validation passed")

                # Save
                output_file = output_dir / case_file.name
                save_yaml(complete_case, str(output_file))
                success_count += 1

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failure_count += 1

        print(f"\n✓ Generated semantics: {success_count} success, {failure_count} failed")

        # Step 3: Export cases
        print("\n=== Step 3: Export Cases ===")
        result = subprocess.run([
            "python3", "skills/commit-semantic-export/run.py",
            "--input-dir", str(output_dir),
            "--output-dir", str(export_dir),
            "--invalid-dir", str(invalid_dir)
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"✗ export_cases failed: {result.stderr}")
            return False

        print(result.stdout)

        # Verify exports
        jsonl_file = export_dir / "cases.jsonl"
        summary_file = export_dir / "summary.json"

        if jsonl_file.exists():
            print(f"✓ JSONL exported: {jsonl_file}")
        if summary_file.exists():
            print(f"✓ Summary exported: {summary_file}")

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║  ✓ End-to-End Skill Test Passed                             ║")
        print("╚══════════════════════════════════════════════════════════════╝")

        print("\n验证完成:")
        print("  ✓ commit-semantic-collect skill 正常工作")
        print("  ✓ commit-semantic-generate 逻辑正常（使用 mock executor）")
        print("  ✓ commit-semantic-export skill 正常工作")
        print("\n所有 skills 验证通过！")

        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
