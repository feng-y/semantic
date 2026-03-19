#!/usr/bin/env python3
"""
commit-semantic-generate skill implementation.

Generates semantic fields for semantic cases using Claude prompts.
"""

import sys
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import load_yaml, save_yaml
from src.commit_semantic.prompt_runner import (
    generate_commit_log,
    generate_rules_invariants,
    generate_issue_text
)
from src.validators import validate_semantic_case, ValidationError
from src.commit_semantic.executor_bridge import get_executor


def _with_retry(fn, max_retries: int = 3, base_delay: float = 5.0):
    """Call fn(), retrying on rate-limit (429) errors with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = "429" in msg or "rate_limit" in msg or "concurrency" in msg
            if is_rate_limit and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠ Rate limit hit, retrying in {delay:.0f}s ({attempt+1}/{max_retries-1})...")
                time.sleep(delay)
            else:
                raise


def generate_semantics_for_case(case_input_path: str, output_dir: str, invalid_dir: str, executor=None):
    """
    Generate semantic fields for a single case.

    Args:
        case_input_path: Path to the input YAML file
        output_dir: Directory for validated outputs
        invalid_dir: Directory for invalid outputs
        executor: Optional callable for prompt execution (provided by host)
    """
    if executor is None:
        raise ValueError("Executor must be provided by host environment")

    print(f"Processing {case_input_path}...")

    try:
        # Load case input
        case_input = load_yaml(case_input_path)

        # Step 1: Generate commit_log
        print("  Generating commit_log...")
        commit_log = _with_retry(lambda: generate_commit_log(case_input, executor))
        print(f"  commit_log: {commit_log[:120]}{'...' if len(commit_log) > 120 else ''}")

        # Step 2: Generate rules and invariants
        print("  Generating rules and invariants...")
        rules_invariants = _with_retry(lambda: generate_rules_invariants(case_input, commit_log, executor))

        # Step 3: Generate issue_text, development_type, split_suggestion
        print("  Generating issue_text...")
        issue_result = _with_retry(lambda: generate_issue_text(
            case_input,
            commit_log,
            rules_invariants['rules'],
            rules_invariants['invariants'],
            executor
        ))

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
            'split_suggestion': issue_result['split_suggestion'],
            'semantic_value': case_input['semantic_value']  # Preserve semantic_value from input
        }

        # Validate
        print("  Validating...")
        validate_semantic_case(case_output)

        # Save to output directory
        output_path = Path(output_dir) / f"{case_output['case_id']}.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_yaml(case_output, str(output_path))

        print(f"  ✓ Saved to {output_path}")
        return True

    except ValidationError as e:
        print(f"  ✗ Validation failed: {e.reason}")
        # Save to invalid directory
        invalid_path = Path(invalid_dir) / Path(case_input_path).name
        invalid_path.parent.mkdir(parents=True, exist_ok=True)
        # Copy input to invalid dir with error annotation
        case_data = load_yaml(case_input_path)
        case_data['validation_error'] = e.reason
        save_yaml(case_data, str(invalid_path))
        return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        # Save to invalid directory for auditability
        invalid_path = Path(invalid_dir) / Path(case_input_path).name
        invalid_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            case_data = load_yaml(case_input_path)
            case_data['generation_error'] = str(e)
            save_yaml(case_data, str(invalid_path))
        except Exception:
            pass  # Best effort - don't fail on error logging
        return False


def generate_semantics(
    input_dir: str = "data/semantic_case_inputs",
    output_dir: str = "data/semantic_cases",
    invalid_dir: str = "data/invalid_cases",
    executor=None
):
    """
    Generate semantics for all cases in input directory.

    Args:
        input_dir: Directory with semantic case inputs
        output_dir: Directory for validated cases
        invalid_dir: Directory for invalid cases
        executor: Optional callable for prompt execution (provided by host)
    """
    input_path = Path(input_dir)
    case_files = list(input_path.glob("*.yaml"))

    print(f"Found {len(case_files)} cases to process")

    success_count = 0
    failure_count = 0

    for case_file in case_files:
        if generate_semantics_for_case(str(case_file), output_dir, invalid_dir, executor):
            success_count += 1
        else:
            failure_count += 1

    print(f"\nProcessing complete:")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failure_count}")


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


if __name__ == "__main__":
    main()
