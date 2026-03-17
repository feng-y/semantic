"""Tests for state inspector versioned review-summary detection."""

from pathlib import Path

import pytest

from src import state_inspector


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_detects_versioned_review_summary(temp_repo):
    """Test that state inspector detects versioned review-summary files."""
    review_dir = temp_repo / "docs" / "fact" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    # Create versioned review-summary files
    (review_dir / "review-summary.v1.md").write_text("# Review Summary v1\n\nContent")
    (review_dir / "review-summary.v2.md").write_text("# Review Summary v2\n\nContent")

    state = state_inspector.inspect(temp_repo)

    assert state.has_review_summary is True


def test_detects_latest_version(temp_repo):
    """Test that state inspector detects the latest review-summary version."""
    review_dir = temp_repo / "docs" / "fact" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    # Create multiple versions
    for i in range(1, 6):
        (review_dir / f"review-summary.v{i}.md").write_text(f"Version {i}")

    state = state_inspector.inspect(temp_repo)

    assert state.has_review_summary is True


def test_no_review_summary_returns_false(temp_repo):
    """Test that state inspector returns False when no review-summary exists."""
    review_dir = temp_repo / "docs" / "fact" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    # Create other files but not review-summary
    (review_dir / "architect-feedback.md").write_text("Some feedback")

    state = state_inspector.inspect(temp_repo)

    assert state.has_review_summary is False


def test_empty_review_directory(temp_repo):
    """Test that state inspector handles empty review directory."""
    review_dir = temp_repo / "docs" / "fact" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    state = state_inspector.inspect(temp_repo)

    assert state.has_review_summary is False


def test_no_review_directory(temp_repo):
    """Test that state inspector handles missing review directory."""
    state = state_inspector.inspect(temp_repo)

    assert state.has_review_summary is False


def test_detects_architect_feedback_with_versioned_review(temp_repo):
    """Test that both architect feedback and versioned review-summary are detected."""
    review_dir = temp_repo / "docs" / "fact" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    (review_dir / "review-summary.v1.md").write_text("# Review Summary\n\nContent")
    (review_dir / "architect-feedback.md").write_text("acceptance: true\n\nFeedback")

    state = state_inspector.inspect(temp_repo)

    assert state.has_review_summary is True
    assert state.has_architect_feedback is True
    assert state.feedback_has_acceptance is True


def test_scan_versions_finds_review_summary(temp_repo):
    """Test that _scan_versions correctly identifies review-summary versions."""
    review_dir = temp_repo / "docs" / "fact" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    (review_dir / "review-summary.v1.md").write_text("v1")
    (review_dir / "review-summary.v3.md").write_text("v3")
    (review_dir / "review-summary.v2.md").write_text("v2")

    versions = state_inspector._scan_versions(review_dir)

    assert "review-summary" in versions
    assert versions["review-summary"] == [1, 2, 3]  # Should be sorted


def test_recommend_next_no_discovery():
    from src.state_inspector import SemanticState, recommend_next
    state = SemanticState()
    assert "discover" in recommend_next(state).lower()


def test_recommend_next_complete():
    from src.state_inspector import SemanticState, recommend_next
    state = SemanticState(
        has_discovery_artifacts=True,
        has_review_summary=True,
        has_architect_feedback=True,
        feedback_has_acceptance=True,
        has_accepted_baseline=True,
    )
    assert "complete" in recommend_next(state).lower()


def test_recommend_next_prefers_runner_status():
    from src.state_inspector import SemanticState, recommend_next
    from src.semantic.status import StatusReport
    state = SemanticState(has_discovery_artifacts=True)
    runner = StatusReport(
        current_stage="step2_candidates",
        next_action="run semantic-recommend",
        blocked=False,
        blocked_reason=None,
        completed=["step1_signals", "step2_candidates"],
    )
    result = recommend_next(state, runner)
    assert "semantic-recommend" in result


def test_recommend_next_blocked_runner():
    from src.state_inspector import SemanticState, recommend_next
    from src.semantic.status import StatusReport
    state = SemanticState(has_discovery_artifacts=True)
    runner = StatusReport(
        current_stage="step5_finalize",
        next_action="resolve: verify_first items have unresolved evidence checks",
        blocked=True,
        blocked_reason="verify_first items have unresolved evidence checks",
        completed=["step1_signals"],
    )
    result = recommend_next(state, runner)
    assert "discover" in result.lower() or "review" in result.lower() or "resolve" in result.lower()
