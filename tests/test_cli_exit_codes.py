"""Tests for CLI exit codes."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.main import main


def test_cli_returns_zero_on_success(tmp_path):
    """Test that CLI returns exit code 0 on success."""
    # Mock dispatcher to return success
    with patch("src.dispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = {"command": "init", "status": "ok"}
        exit_code = main(["--root", str(tmp_path), "init"])
    assert exit_code == 0


def test_cli_returns_one_on_validation_failed(tmp_path):
    """Test that CLI returns exit code 1 on validation_failed."""
    with patch("src.dispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = {
            "command": "discover",
            "status": "validation_failed",
            "validation_failures": [],
        }
        exit_code = main(["--root", str(tmp_path), "discover"])
    assert exit_code == 1


def test_cli_returns_one_on_execution_unavailable(tmp_path):
    """Test that CLI returns exit code 1 on execution_unavailable."""
    with patch("src.dispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = {
            "command": "discover",
            "status": "execution_unavailable",
        }
        exit_code = main(["--root", str(tmp_path), "discover"])
    assert exit_code == 1


def test_cli_returns_one_on_version_skew(tmp_path):
    """Test that CLI returns exit code 1 on version_skew."""
    with patch("src.dispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = {
            "command": "discover",
            "status": "version_skew",
            "validation_failures": [],
        }
        exit_code = main(["--root", str(tmp_path), "discover"])
    assert exit_code == 1


def test_cli_returns_one_on_error(tmp_path):
    """Test that CLI returns exit code 1 on error."""
    with patch("src.dispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = {
            "command": "discover",
            "status": "error",
        }
        exit_code = main(["--root", str(tmp_path), "discover"])
    assert exit_code == 1


def test_cli_returns_zero_on_ok_status(tmp_path):
    """Test that CLI returns exit code 0 for ok status."""
    with patch("src.dispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = {
            "command": "status",
            "status": "ok",
        }
        exit_code = main(["--root", str(tmp_path), "status"])
    assert exit_code == 0


def test_cli_no_command_returns_one():
    """Test that CLI returns exit code 1 when no command is given."""
    exit_code = main([])
    assert exit_code == 1
