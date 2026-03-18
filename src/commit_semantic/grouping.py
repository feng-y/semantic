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
    Groups related changes together based on semantic coherence.
    Each group represents changes that belong together semantically.
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

    # If we have primary files, group by semantic coherence
    if primary_files:
        # Group primary files by theme/module
        theme_groups: Dict[str, List[str]] = {}
        for primary_file in primary_files:
            theme = extract_theme_from_file(primary_file)
            if theme not in theme_groups:
                theme_groups[theme] = []
            theme_groups[theme].append(primary_file)

        # Track which supporting files have been claimed by a theme group
        claimed_supporting: set = set()

        theme_items = list(theme_groups.items())

        # Create one group per theme
        for idx, (theme, theme_files) in enumerate(theme_items):
            group_id = f"{commit.commit_id}_group_{idx}"

            # Find supporting files related to any file in this theme
            related_supporting = []
            for primary_file in theme_files:
                related = find_related_files(primary_file, supporting_files)
                for support_file in related:
                    if support_file not in related_supporting:
                        related_supporting.append(support_file)
                        claimed_supporting.add(support_file)

            # P0 spec: config/flag/wiring/registration 默认挂主组
            # When there is only one primary theme, attach all remaining
            # supporting files (e.g. config.yaml) to that single group.
            if len(theme_items) == 1:
                for support_file in supporting_files:
                    if support_file not in claimed_supporting:
                        related_supporting.append(support_file)
                        claimed_supporting.add(support_file)

            # Get diff chunks only for files in this group
            group_files = theme_files + related_supporting
            group_diff_chunks = _filter_diff_chunks_for_files(commit.diff_chunks, group_files)

            groups.append(ChangeGroup(
                group_id=group_id,
                theme=theme,
                files=group_files,
                role=ChangeRole.PRIMARY,
                diff_chunks=group_diff_chunks
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


def _filter_diff_chunks_for_files(diff_chunks: List[str], files: List[str]) -> List[str]:
    """
    Filter diff chunks to only include those relevant to the specified files.

    A diff stream looks like:
        diff --git a/foo.py b/foo.py   <- file boundary marker
        --- a/foo.py
        +++ b/foo.py
        @@ ... @@
        <hunk lines>
        diff --git a/bar.py b/bar.py   <- next file boundary

    We track which file we are currently inside.  A new `diff --git` line
    always starts a new file section, so we re-evaluate membership there
    and reset `current_file` to None when the new file is not in our set.
    """
    filtered = []
    current_file = None

    for chunk in diff_chunks:
        if chunk.startswith('diff --git'):
            # New file section — check if it belongs to our set
            current_file = None
            for file_path in files:
                if file_path in chunk:
                    current_file = file_path
                    break
            if current_file is not None:
                filtered.append(chunk)
        elif chunk.startswith('--- ') or chunk.startswith('+++ '):
            # Header lines for the current file
            if current_file is not None:
                filtered.append(chunk)
        else:
            # Hunk content — include only when inside a relevant file
            if current_file is not None:
                filtered.append(chunk)

    return filtered


def extract_theme_from_file(file_path: str) -> str:
    """Extract a semantic object name from file path.

    Uses the filename stem (without extension) as the primary key so that
    files that represent the same object (e.g. parser.py + parser_test.py)
    share a theme, regardless of which directory they live in.

    Strips common suffixes (_test, _spec, _utils, _helpers) so that
    "parser" and "parser_utils" are treated as the same semantic object.
    """
    filename = file_path.split('/')[-1]
    stem = filename.split('.')[0]

    # Strip common auxiliary suffixes to normalise to the core object name
    for suffix in ('_test', '_spec', '_tests', '_utils', '_helpers', '_helper'):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    return stem


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
