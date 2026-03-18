from typing import List
from src.types import (
    ChangeGroup, SemanticCaseInput, BugfixEvidence,
    SplitHints, ChangeRole
)


def build_semantic_cases(
    commit_id: str,
    groups: List[ChangeGroup],
    bugfix_evidence: BugfixEvidence
) -> List[SemanticCaseInput]:
    """
    Build semantic cases from change groups.
    Groups are merged if they can be compressed into a single issue_text.
    """
    if not groups:
        return []

    # Separate primary and supporting groups
    primary_groups = [g for g in groups if g.role == ChangeRole.PRIMARY]
    supporting_groups = [g for g in groups if g.role == ChangeRole.SUPPORTING]

    # If only one primary group, merge all supporting into it
    if len(primary_groups) == 1:
        return [_merge_groups_into_case(
            commit_id,
            primary_groups[0],
            supporting_groups,
            bugfix_evidence
        )]

    # Multiple primary groups - check if they should be merged
    if len(primary_groups) > 1:
        # Check if themes are related
        if _should_merge_groups(primary_groups):
            # Merge all into one case
            main_group = primary_groups[0]
            other_groups = primary_groups[1:] + supporting_groups
            return [_merge_groups_into_case(
                commit_id,
                main_group,
                other_groups,
                bugfix_evidence
            )]
        else:
            # Create separate cases for each primary group
            cases = []
            for idx, primary_group in enumerate(primary_groups):
                case = _create_case_from_group(
                    commit_id,
                    primary_group,
                    bugfix_evidence,
                    case_suffix=f"_{idx}"
                )
                cases.append(case)
            return cases

    # Only supporting groups - create one case
    if supporting_groups:
        return [_create_case_from_group(
            commit_id,
            supporting_groups[0],
            bugfix_evidence
        )]

    return []


def _should_merge_groups(groups: List[ChangeGroup]) -> bool:
    """
    Determine if multiple groups should be merged into one semantic case.
    """
    # If all groups share the same theme, merge them
    themes = set(g.theme for g in groups)
    if len(themes) == 1:
        return True

    # If total file count is small, merge them
    total_files = sum(len(g.files) for g in groups)
    if total_files <= 5:
        return True

    # Otherwise, keep them separate
    return False


def _merge_groups_into_case(
    commit_id: str,
    main_group: ChangeGroup,
    other_groups: List[ChangeGroup],
    bugfix_evidence: BugfixEvidence
) -> SemanticCaseInput:
    """Merge multiple groups into a single semantic case."""
    all_files = main_group.files.copy()
    all_diff_chunks = main_group.diff_chunks.copy()

    for group in other_groups:
        all_files.extend(group.files)
        all_diff_chunks.extend(group.diff_chunks)

    # Identify test files
    related_tests = [f for f in all_files if 'test' in f.lower()]

    # Generate split hints
    split_hints = SplitHints(
        too_many_files=len(all_files) > 10,
        too_many_diff_themes=len(set(g.theme for g in [main_group] + other_groups)) > 3,
        mixed_feature_and_bugfix=False,  # Will be determined later
        unrelated_objects_detected=len(set(g.theme for g in [main_group] + other_groups)) > 2
    )

    case_id = f"{commit_id}_case_0"

    return SemanticCaseInput(
        case_id=case_id,
        commit_id=commit_id,
        module=main_group.theme,
        files=all_files,
        diff_chunks=all_diff_chunks,
        domain=main_group.theme,  # Set domain to module by default
        related_tests=related_tests,
        bugfix_evidence=bugfix_evidence,
        split_hints=split_hints
    )


def _create_case_from_group(
    commit_id: str,
    group: ChangeGroup,
    bugfix_evidence: BugfixEvidence,
    case_suffix: str = "_0"
) -> SemanticCaseInput:
    """Create a semantic case from a single group."""
    related_tests = [f for f in group.files if 'test' in f.lower()]

    split_hints = SplitHints(
        too_many_files=len(group.files) > 10,
        too_many_diff_themes=False,
        mixed_feature_and_bugfix=False,
        unrelated_objects_detected=False
    )

    case_id = f"{commit_id}_case{case_suffix}"

    return SemanticCaseInput(
        case_id=case_id,
        commit_id=commit_id,
        module=group.theme,
        files=group.files,
        diff_chunks=group.diff_chunks,
        domain=group.theme,  # Set domain to module by default
        related_tests=related_tests,
        bugfix_evidence=bugfix_evidence,
        split_hints=split_hints
    )
