"""
Tests for grouping boundary cases per P0 spec (section 七, lines 276-285).

P0 rules:
  - 同对象优先归一组  (same object → same group)
  - 主逻辑 + 测试归一组  (impl + test → same group)
  - 只有独立主动作才新开组  (only independent primary actions get their own group)
  - 能共同压缩成一个短的单主体 issue_text 的 group → 合并为一个 semantic_case
  - 多个独立主动作时不合并
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.types import RawCommit, BugfixEvidence
from src.commit_semantic.grouping import (
    extract_theme_from_file,
    extract_change_groups,
    _filter_diff_chunks_for_files,
)
from src.commit_semantic.semantic_case_builder import build_semantic_cases, _should_merge_groups
from src.types import ChangeGroup, ChangeRole


# ---------------------------------------------------------------------------
# extract_theme_from_file
# ---------------------------------------------------------------------------

def test_theme_uses_filename_stem_not_directory():
    """Theme should be the object name (filename stem), not the parent dir."""
    assert extract_theme_from_file("src/parser/parser.py") == "parser"
    assert extract_theme_from_file("src/parser/lexer.py") == "lexer"


def test_theme_strips_test_suffix():
    assert extract_theme_from_file("tests/parser_test.py") == "parser"
    assert extract_theme_from_file("tests/test_parser.py") == "test_parser"  # prefix not stripped


def test_theme_strips_utils_suffix():
    assert extract_theme_from_file("src/parser_utils.py") == "parser"


def test_theme_strips_helpers_suffix():
    assert extract_theme_from_file("src/auth_helpers.py") == "auth"


def test_theme_flat_file():
    assert extract_theme_from_file("parser.py") == "parser"


# ---------------------------------------------------------------------------
# extract_change_groups — same-object grouping
# ---------------------------------------------------------------------------

def _make_commit(files, diff_chunks=None):
    return RawCommit(
        commit_id="abc123",
        author="test",
        timestamp="0",
        files=files,
        diff_chunks=diff_chunks or [],
    )


def test_impl_and_test_grouped_together():
    """parser.py and parser_test.py share theme 'parser' → one group."""
    commit = _make_commit(["src/parser.py", "tests/parser_test.py"])
    groups = extract_change_groups(commit)
    assert len(groups) == 1, f"Expected 1 group, got {len(groups)}: {[g.theme for g in groups]}"


def test_two_independent_objects_get_separate_groups():
    """parser.py and lexer.py are different objects → two groups."""
    commit = _make_commit(["src/parser.py", "src/lexer.py"])
    groups = extract_change_groups(commit)
    assert len(groups) == 2, f"Expected 2 groups, got {len(groups)}: {[g.theme for g in groups]}"


def test_config_file_attached_to_primary_group():
    """config.yaml is SUPPORTING and should be attached to the primary group."""
    commit = _make_commit(["src/parser.py", "config.yaml"])
    groups = extract_change_groups(commit)
    # Only one primary theme → one group containing both files
    assert len(groups) == 1
    all_files = groups[0].files
    assert "config.yaml" in all_files


def test_utils_file_same_theme_as_primary():
    """parser_utils.py strips to 'parser' → same group as parser.py."""
    commit = _make_commit(["src/parser.py", "src/parser_utils.py"])
    groups = extract_change_groups(commit)
    assert len(groups) == 1


# ---------------------------------------------------------------------------
# _filter_diff_chunks_for_files
# ---------------------------------------------------------------------------

def test_filter_keeps_relevant_file_chunks():
    chunks = [
        "diff --git a/parser.py b/parser.py",
        "--- a/parser.py",
        "+++ b/parser.py",
        "@@ -1,3 +1,4 @@",
        " def parse(): pass",
        "diff --git a/lexer.py b/lexer.py",
        "--- a/lexer.py",
        "+++ b/lexer.py",
        "@@ -1,2 +1,2 @@",
        " def lex(): pass",
    ]
    result = _filter_diff_chunks_for_files(chunks, ["parser.py"])
    assert "diff --git a/parser.py b/parser.py" in result
    assert "diff --git a/lexer.py b/lexer.py" not in result
    assert " def parse(): pass" in result
    assert " def lex(): pass" not in result


def test_filter_empty_when_no_match():
    chunks = ["diff --git a/foo.py b/foo.py", " some line"]
    result = _filter_diff_chunks_for_files(chunks, ["bar.py"])
    assert result == []


def test_filter_multiple_files():
    chunks = [
        "diff --git a/a.py b/a.py",
        " line a",
        "diff --git a/b.py b/b.py",
        " line b",
        "diff --git a/c.py b/c.py",
        " line c",
    ]
    result = _filter_diff_chunks_for_files(chunks, ["a.py", "c.py"])
    assert " line a" in result
    assert " line b" not in result
    assert " line c" in result


# ---------------------------------------------------------------------------
# _should_merge_groups — tightened merge criterion
# ---------------------------------------------------------------------------

def _make_group(theme, files, diff_chunks=None):
    return ChangeGroup(
        group_id=f"g_{theme}",
        theme=theme,
        files=files,
        role=ChangeRole.PRIMARY,
        diff_chunks=diff_chunks or [],
    )


def test_same_theme_merges():
    g1 = _make_group("parser", ["parser.py"])
    g2 = _make_group("parser", ["parser_utils.py"])
    assert _should_merge_groups([g1, g2]) is True


def test_small_scope_different_themes_merges():
    """≤3 files AND ≤50 non-zero diff lines → merge even with different themes."""
    g1 = _make_group("parser", ["parser.py"], diff_chunks=["x"] * 20)
    g2 = _make_group("lexer", ["lexer.py"], diff_chunks=["y"] * 20)
    # total_files=2, total_diff_lines=40 → small scope, should merge
    assert _should_merge_groups([g1, g2]) is True


def test_zero_diff_different_themes_no_merge():
    """Two distinct objects with no diff content should NOT be merged."""
    g1 = _make_group("parser", ["parser.py"], diff_chunks=[])
    g2 = _make_group("lexer", ["lexer.py"], diff_chunks=[])
    assert _should_merge_groups([g1, g2]) is False


def test_large_scope_different_themes_no_merge():
    """Independent actions with many files should NOT be merged (P0: 多个独立主动作时不合并)."""
    g1 = _make_group("parser", ["a.py", "b.py", "c.py"], diff_chunks=["x"] * 30)
    g2 = _make_group("lexer", ["d.py", "e.py", "f.py"], diff_chunks=["y"] * 30)
    assert _should_merge_groups([g1, g2]) is False


def test_theme_substring_no_longer_triggers_merge():
    """
    The old heuristic merged 'parser' + 'parser_utils' even with 4-5 files.
    After the fix, only same-theme or small-scope triggers a merge.
    This test uses 4 files with different themes (no substring relation after
    the utils-stripping fix) to confirm the old path is gone.
    """
    # 4 files, themes are genuinely different (not same after stripping)
    g1 = _make_group("auth", ["auth.py", "auth_middleware.py"], diff_chunks=["x"] * 30)
    g2 = _make_group("session", ["session.py", "session_store.py"], diff_chunks=["y"] * 30)
    # total_files=4, total_diff_lines=60 → exceeds small-scope threshold
    assert _should_merge_groups([g1, g2]) is False


# ---------------------------------------------------------------------------
# build_semantic_cases — integration
# ---------------------------------------------------------------------------

def test_two_independent_objects_produce_two_cases():
    """Two distinct primary groups → two separate semantic cases."""
    commit = _make_commit(["src/parser.py", "src/lexer.py"])
    groups = extract_change_groups(commit)
    evidence = BugfixEvidence()
    cases = build_semantic_cases("abc123", groups, evidence)
    assert len(cases) == 2, f"Expected 2 cases, got {len(cases)}"


def test_same_object_impl_and_test_produce_one_case():
    """parser.py + parser_test.py → one semantic case."""
    commit = _make_commit(["src/parser.py", "tests/parser_test.py"])
    groups = extract_change_groups(commit)
    evidence = BugfixEvidence()
    cases = build_semantic_cases("abc123", groups, evidence)
    assert len(cases) == 1, f"Expected 1 case, got {len(cases)}"
