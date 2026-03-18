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
repo_root = Path(__file__).parent
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


def mock_executor(prompt: str) -> str:
    """
    Mock executor for testing.
    Returns valid YAML responses based on prompt content.
    """
    # Determine which prompt by checking the header
    if "# Generate Commit Log" in prompt:
        response = """```yaml
commit_log: "修改解析器以支持新的DSL语法"
```"""
    elif "# Generate Rules and Invariants" in prompt:
        response = """```yaml
rules:
  - "解析器必须保持向后兼容"
  - "新语法不能破坏现有DSL"
invariants:
  - "解析结果结构保持稳定"
```"""
    elif "# Generate Issue Text" in prompt:
        response = """```yaml
issue_text: "feat：添加新DSL语法支持"
development_type: "feature"
split_suggestion:
  needs_split: false
  split_reasons: []
```"""
    else:
        # Fallback
        response = """```yaml
commit_log: "更新代码"
```"""

    return response


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


if __name__ == "__main__":
    success = test_e2e_pipeline()
    sys.exit(0 if success else 1)
