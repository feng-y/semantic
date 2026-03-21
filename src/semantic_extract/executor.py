"""LLM executor for semantic extract."""

import json
import re
from typing import List, Tuple

# Load prompts once at module level to avoid repeated disk reads
_EXTRACT_PROMPT = None
_REFINES_PROMPT = None


def _get_extract_prompt() -> str:
    global _EXTRACT_PROMPT
    if _EXTRACT_PROMPT is None:
        from src.commit_semantic.prompt_runner import load_prompt
        _EXTRACT_PROMPT = load_prompt("extract")
    return _EXTRACT_PROMPT


def _get_refine_prompt() -> str:
    global _REFINES_PROMPT
    if _REFINES_PROMPT is None:
        from src.commit_semantic.prompt_runner import load_prompt
        _REFINES_PROMPT = load_prompt("refine")
    return _REFINES_PROMPT


def build_rules_prompt(diff: str, commit_msg: str = "") -> str:
    """Build prompt for rules/invariants extraction."""
    prompt = f"""## Git Commit Message
```
{commit_msg}
```

## Diff
```
{diff[:15000]}
```

{_get_extract_prompt()}

Now extract rules and invariants from this diff:"""
    return prompt


def build_commit_prompt(diff: str, commit_msg: str = "") -> str:
    """Build prompt for commit semantic extraction."""
    prompt = f"""## Original Commit Message
```
{commit_msg}
```

## Diff
```
{diff[:15000]}
```

{_get_refine_prompt()}

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
    response = executor_fn(prompt)
    return parse_rules_response(response)


def extract_commit_semantics(diff: str, commit_msg: str, executor_fn) -> Tuple[str, str, List[str]]:
    """Extract commit semantics using LLM."""
    prompt = build_commit_prompt(diff, commit_msg)
    response = executor_fn(prompt)
    return parse_commit_response(response)
