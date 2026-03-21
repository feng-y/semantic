"""LLM executor for semantic extract."""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def load_prompt(prompt_name: str) -> str:
    """Load prompt template from prompts/commit-semantic directory."""
    # Reuse existing prompt_loader from commit_semantic
    from src.commit_semantic.prompt_runner import load_prompt as _load_prompt
    return _load_prompt(prompt_name)


def build_rules_prompt(diff: str, commit_msg: str = "") -> str:
    """Build prompt for rules/invariants extraction."""
    template = load_prompt("extract")

    prompt = f"""## Git Commit Message
```
{commit_msg}
```

## Diff
```
{diff[:15000]}
```

{template}

Now extract rules and invariants from this diff:"""

    return prompt


def build_commit_prompt(diff: str, commit_msg: str = "") -> str:
    """Build prompt for commit semantic extraction."""
    template = load_prompt("refine")

    prompt = f"""## Original Commit Message
```
{commit_msg}
```

## Diff
```
{diff[:15000]}
```

{template}

Now generate the refined commit:"""

    return prompt


def parse_rules_response(response: str) -> Tuple[List[str], List[str]]:
    """Parse LLM response for rules/invariants."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            rules = data.get("rules", [])
            invariants = data.get("invariants", [])
            return rules, invariants
        except json.JSONDecodeError:
            pass

    # Fallback: try direct JSON
    try:
        data = json.loads(response)
        return data.get("rules", []), data.get("invariants", [])
    except json.JSONDecodeError:
        return [], []


def parse_commit_response(response: str) -> Tuple[str, str, List[str]]:
    """Parse LLM response for commit refinement."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            title = data.get("title", "")
            body = data.get("body", "")
            commit_log = data.get("commit_log", [])
            return title, body, commit_log
        except json.JSONDecodeError:
            pass

    # Fallback
    return "", "", []


def extract_rules_invariants(diff: str, commit_msg: str, executor_fn) -> Tuple[List[str], List[str]]:
    """Extract rules/invariants using LLM."""
    prompt = build_rules_prompt(diff, commit_msg)

    try:
        response = executor_fn(prompt)
        return parse_rules_response(response)
    except Exception as e:
        print(f"Error extracting rules: {e}")
        return [], []


def extract_commit_semantics(diff: str, commit_msg: str, executor_fn) -> Tuple[str, str, List[str]]:
    """Extract commit semantics using LLM."""
    prompt = build_commit_prompt(diff, commit_msg)

    try:
        response = executor_fn(prompt)
        return parse_commit_response(response)
    except Exception as e:
        print(f"Error extracting commit: {e}")
        return "", "", []
