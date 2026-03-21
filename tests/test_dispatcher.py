"""Tests for dispatcher executor forwarding and CLI exit codes."""

from unittest.mock import MagicMock, patch

import pytest

from src import dispatcher
from src.host_executor import HostExecutor


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_dispatcher_forwards_executor_to_discover(temp_repo):
    """Test that dispatcher forwards executor parameter to discover handler."""
    mock_executor = MagicMock(spec=HostExecutor)

    # Mock skill_loader to avoid FileNotFoundError for missing manifest
    with patch("src.discovery_executor.skill_loader.load_all_skills") as mock_skills:
        mock_skills.return_value = {}  # No skills found -> error status
        result = dispatcher.dispatch(
            "discover",
            temp_repo,
            executor=mock_executor,
        )

    # The executor was forwarded — status is "error" (no discovery skill),
    # not "execution_unavailable" (which would mean executor was None)
    assert result["command"] == "discover"
    assert result["status"] == "error"
    assert result["status"] != "execution_unavailable"


def test_dispatcher_forwards_executor_to_refine(temp_repo):
    """Test that dispatcher forwards executor parameter to refine handler."""
    mock_executor = MagicMock(spec=HostExecutor)

    result = dispatcher.dispatch(
        "refine",
        temp_repo,
        executor=mock_executor,
    )

    assert result["command"] == "refine"
    # Should not be execution_unavailable since executor was provided
    assert result["status"] != "execution_unavailable"


def test_dispatcher_discover_no_executor_returns_execution_unavailable(temp_repo):
    """Test that discover without executor returns execution_unavailable."""
    result = dispatcher.dispatch("discover", temp_repo)
    assert result["status"] == "execution_unavailable"


def test_dispatcher_refine_no_executor_returns_execution_unavailable(temp_repo):
    """Test that refine without executor returns execution_unavailable."""
    result = dispatcher.dispatch("refine", temp_repo)
    assert result["status"] == "execution_unavailable"
