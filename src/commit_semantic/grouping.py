from typing import List, Dict
from src.types import RawCommit, ChangeGroup, ChangeRole, BugfixEvidence


def analyze_file_role(file_path: str, all_files: List[str]) -> ChangeRole:
    """Determine the role of a file in the change."""
    file_lower = file_path.lower()

    # Test files are supporting
    if 'test' in file_lower or file_path.endswith('_test.py') or file_path.endswith('.test.ts'):
        return ChangeRole.SUPPORTING

    # Config files are supporting
    config_patterns = ['config', 'settings', '.json', '.yaml', '.yml', '.toml', '.ini']
    if any(pattern in file_lower for pattern in config_patterns):
        return ChangeRole.SUPPORTING

    # Flag/feature toggle files
    if 'flag' in file_lower or 'feature' in file_lower:
        return ChangeRole.SUPPORTING

    # Wiring/registration files
    if 'register' in file_lower or 'wiring' in file_lower or '__init__' in file_lower:
        return ChangeRole.SUPPORTING

    # Default to primary for implementation files
    return ChangeRole.PRIMARY


def extract_change_groups(commit: RawCommit) -> List[ChangeGroup]:
    """
    Extract change groups from a commit.
    Groups related changes together based on file relationships.
    """
    groups = []
    primary_files = []
    supporting_files = []

    # Classify files
    for file_path in commit.files:
        role = analyze_file_role(file_path, commit.files)
        if role == ChangeRole.PRIMARY:
            primary_files.append(file_path)
        else:
            supporting_files.append(file_path)

    # If we have primary files, create groups around them
    if primary_files:
        # For now, create one group per primary file
        # In a more sophisticated implementation, we'd group related files
        for idx, primary_file in enumerate(primary_files):
            group_id = f"{commit.commit_id}_group_{idx}"
            theme = extract_theme_from_file(primary_file)

            # Find related supporting files
            related_supporting = find_related_files(primary_file, supporting_files)

            groups.append(ChangeGroup(
                group_id=group_id,
                theme=theme,
                files=[primary_file] + related_supporting,
                role=ChangeRole.PRIMARY,
                diff_chunks=commit.diff_chunks  # Simplified: share all diffs
            ))
    else:
        # All files are supporting - create one group
        group_id = f"{commit.commit_id}_group_0"
        groups.append(ChangeGroup(
            group_id=group_id,
            theme="supporting_changes",
            files=supporting_files,
            role=ChangeRole.SUPPORTING,
            diff_chunks=commit.diff_chunks
        ))

    return groups


def extract_theme_from_file(file_path: str) -> str:
    """Extract a theme/module name from file path."""
    parts = file_path.split('/')
    if len(parts) > 1:
        # Use the directory name as theme
        return parts[-2]
    return parts[0].split('.')[0]


def find_related_files(primary_file: str, supporting_files: List[str]) -> List[str]:
    """Find supporting files related to a primary file."""
    related = []
    primary_base = primary_file.split('/')[-1].split('.')[0]

    for support_file in supporting_files:
        support_base = support_file.split('/')[-1].split('.')[0]
        # Match by base name (e.g., parser.py and parser_test.py)
        if primary_base in support_base or support_base in primary_base:
            related.append(support_file)

    return related


def detect_bugfix_evidence(commit: RawCommit, diff_text: str) -> BugfixEvidence:
    """
    Detect bugfix evidence from commit and diff.
    Returns categorized evidence (weak, medium, strong).
    """
    evidence = BugfixEvidence()

    diff_lower = diff_text.lower()

    # Weak evidence
    if 'if ' in diff_lower and ('else' in diff_lower or 'elif' in diff_lower):
        evidence.weak.append("existing branch structure changed")

    if 'fallback' in diff_lower or 'default' in diff_lower:
        evidence.weak.append("fallback path touched")

    if 'compat' in diff_lower or 'legacy' in diff_lower:
        evidence.weak.append("compatibility path touched")

    # Medium evidence
    if 'boundary' in diff_lower or 'bound' in diff_lower:
        evidence.medium.append("boundary check added")

    if 'invalid' in diff_lower or 'validate' in diff_lower:
        evidence.medium.append("invalid input handling corrected")

    if 'legacy' in diff_lower and 'repair' in diff_lower:
        evidence.medium.append("legacy path repaired")

    # Strong evidence
    if 'regression' in diff_lower and 'test' in diff_lower:
        evidence.strong.append("regression tests added for broken behavior")

    if 'restore' in diff_lower or 'revert' in diff_lower:
        evidence.strong.append("old behavior restored")

    if 'historical' in diff_lower and ('input' in diff_lower or 'compat' in diff_lower):
        evidence.strong.append("historical inputs explicitly kept parseable")

    return evidence
