import re
import yaml
from pathlib import Path
from typing import Dict, Any, Callable, Optional

# Compile regex patterns at module level
YAML_BLOCK_PATTERN = re.compile(r'```yaml\s*\n(.*?)\n```', re.DOTALL)
CODE_BLOCK_PATTERN = re.compile(r'```\s*\n(.*?)\n```', re.DOTALL)


def load_prompt(prompt_name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = Path("prompts") / "commit-semantic" / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def run_prompt_with_claude(
    prompt_template: str,
    input_data: Dict[str, Any],
    executor: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """
    Run a prompt with Claude via host executor.

    Args:
        prompt_template: The prompt template text
        input_data: Input data to be converted to YAML
        executor: Optional host executor callable. If None, raises NotImplementedError.

    Returns:
        Parsed YAML response as dict

    The executor should be provided by the host environment (Claude Code).
    When called from a skill, the skill runner should inject the executor.
    """
    # Convert input data to YAML for the prompt
    input_yaml = yaml.dump(input_data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # Construct the full prompt
    full_prompt = f"{prompt_template}\n\n---\n\nInput:\n\n```yaml\n{input_yaml}\n```"

    if executor is None:
        raise NotImplementedError(
            "No executor provided. When running from a skill, the host environment "
            "(Claude Code) should provide an executor function that takes a prompt "
            "string and returns the response string."
        )

    # Call the executor
    response = executor(full_prompt)

    # Parse YAML response
    # The response should be in YAML format, possibly wrapped in ```yaml blocks
    yaml_content = extract_yaml_from_response(response)
    result = yaml.safe_load(yaml_content)

    if not isinstance(result, dict):
        raise ValueError(f"Expected dict from YAML, got {type(result)}")

    return result


def extract_yaml_from_response(response: str) -> str:
    """Extract YAML content from response, handling code blocks."""
    # Try to find YAML code block
    match = YAML_BLOCK_PATTERN.search(response)

    if match:
        return match.group(1)

    # Try generic code block
    match = CODE_BLOCK_PATTERN.search(response)

    if match:
        return match.group(1)

    # Assume the entire response is YAML
    return response.strip()


def generate_commit_log(case_input: Dict[str, Any], executor: Optional[Callable[[str], str]] = None) -> str:
    """Generate commit_log using the generate_commit_log prompt.

    If commit_message is present and diff is small, use it directly without an LLM call.
    If diff_chunks are very large, truncate them before sending to the LLM.
    """
    commit_message = case_input.get('commit_message', '').strip()
    diff_chunks = case_input.get('diff_chunks', [])
    total_diff_chars = sum(len(c) for c in diff_chunks)

    # For simple/clean commits: use commit message directly if diff is small
    SMALL_DIFF_THRESHOLD = 2000  # chars
    if commit_message and total_diff_chars <= SMALL_DIFF_THRESHOLD:
        return commit_message

    # For large diffs: truncate before sending to LLM
    MAX_DIFF_CHARS = 8000
    if total_diff_chars > MAX_DIFF_CHARS:
        truncated_chunks = []
        budget = MAX_DIFF_CHARS
        for chunk in diff_chunks:
            if budget <= 0:
                break
            truncated_chunks.append(chunk[:budget])
            budget -= len(chunk)
        case_input = dict(case_input)
        case_input['diff_chunks'] = truncated_chunks
        case_input['diff_truncated'] = True

    prompt = load_prompt("generate_commit_log")
    result = run_prompt_with_claude(prompt, case_input, executor)
    return result['commit_log']


def generate_rules_invariants(
    case_input: Dict[str, Any],
    commit_log: str,
    executor: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """Generate rules and invariants using the generate_rules_invariants prompt."""
    prompt = load_prompt("generate_rules_invariants")

    # Add commit_log to input
    input_with_log = case_input.copy()
    input_with_log['commit_log'] = commit_log

    result = run_prompt_with_claude(prompt, input_with_log, executor)
    return {
        'rules': result['rules'],
        'invariants': result['invariants']
    }


def generate_issue_text(
    case_input: Dict[str, Any],
    commit_log: str,
    rules: list,
    invariants: list,
    executor: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """Generate issue_text, development_type, and split_suggestion."""
    prompt = load_prompt("generate_issue_text")

    # Prepare input with all previous results
    input_data = case_input.copy()
    input_data['commit_log'] = commit_log
    input_data['rules'] = rules
    input_data['invariants'] = invariants

    result = run_prompt_with_claude(prompt, input_data, executor)
    return {
        'issue_text': result['issue_text'],
        'development_type': result['development_type'],
        'split_suggestion': result['split_suggestion']
    }

