"""
Commit semantic extraction module.

Extracts semantic cases from git commit history.
"""

from .git_utils import get_commit_list, get_commit_details
from .grouping import extract_change_groups, detect_bugfix_evidence
from .semantic_case_builder import build_semantic_cases
from .prompt_runner import (
    generate_commit_log,
    generate_rules_invariants,
    generate_issue_text
)

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
