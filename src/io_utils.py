import yaml
import json
from pathlib import Path
from typing import Any, Dict, List
from src.types import SemanticCaseInput, SemanticCaseOutput


def save_yaml(data: Dict[str, Any], file_path: str) -> None:
    """Save data as YAML file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """Load YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_jsonl(data: List[Dict[str, Any]], file_path: str) -> None:
    """Save data as JSONL file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """Save data as JSON file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(file_path: str) -> Dict[str, Any]:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def semantic_case_input_to_dict(case: SemanticCaseInput) -> Dict[str, Any]:
    """Convert SemanticCaseInput to dict for serialization."""
    return {
        'case_id': case.case_id,
        'commit_id': case.commit_id,
        'module': case.module,
        'files': case.files,
        'diff_chunks': case.diff_chunks,
        'related_tests': case.related_tests,
        'bugfix_evidence': {
            'weak': case.bugfix_evidence.weak,
            'medium': case.bugfix_evidence.medium,
            'strong': case.bugfix_evidence.strong
        },
        'split_hints': {
            'too_many_files': case.split_hints.too_many_files,
            'too_many_diff_themes': case.split_hints.too_many_diff_themes,
            'mixed_feature_and_bugfix': case.split_hints.mixed_feature_and_bugfix,
            'unrelated_objects_detected': case.split_hints.unrelated_objects_detected
        },
        'semantic_value': case.semantic_value
    }


def semantic_case_output_to_dict(case: SemanticCaseOutput) -> Dict[str, Any]:
    """Convert SemanticCaseOutput to dict for serialization."""
    return {
        'case_id': case.case_id,
        'commit_id': case.commit_id,
        'module': case.module,
        'commit_log': case.commit_log,
        'issue_text': case.issue_text,
        'development_type': case.development_type.value,
        'rules': case.rules,
        'invariants': case.invariants,
        'split_suggestion': {
            'needs_split': case.split_suggestion.needs_split,
            'split_reasons': case.split_suggestion.split_reasons
        },
        'semantic_value': case.semantic_value,
        'dedup_key': case.dedup_key,
        'pattern_id': case.pattern_id
    }
