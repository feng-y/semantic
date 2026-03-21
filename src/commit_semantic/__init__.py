"""
Commit semantic extraction module.

Extracts semantic cases from git commit history.
"""

from .git_utils import get_commit_details, get_commit_list
from .grouping import detect_bugfix_evidence, extract_change_groups
from .prompt_runner import (
    generate_commit_log,
    generate_issue_text,
    generate_rules_invariants,
)
from .semantic_case_builder import build_semantic_cases

__all__ = [
    'get_commit_list',
    'get_commit_details',
    'extract_change_groups',
    'detect_bugfix_evidence',
    'build_semantic_cases',
    'generate_commit_log',
    'generate_rules_invariants',
    'generate_issue_text',
]
