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


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from text, handling nested braces."""
    # Try markdown code block first
    json_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    # Try direct JSON - find first { to last }
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


def parse_rules_response(response: str) -> Tuple[List[str], List[str]]:
    """Parse LLM response for rules/invariants."""
    data = _extract_json(response)
    if data:
        return data.get("rules", []), data.get("invariants", [])
    return [], []


def parse_commit_response(response: str) -> Tuple[str, str, List[str]]:
    """Parse LLM response for commit refinement."""
    data = _extract_json(response)
    if data:
        return data.get("title", ""), data.get("body", ""), data.get("commit_log", [])
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
