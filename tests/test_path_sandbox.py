"""Tests for path traversal protection in skill_loader and prompt_loader."""

from pathlib import Path

import pytest

from src.skill_loader import PathSandboxError as SkillPathSandboxError
from src.skill_loader import _validate_path as skill_validate_path
from src.prompt_loader import PathSandboxError as PromptPathSandboxError
from src.prompt_loader import _validate_path as prompt_validate_path
from src.prompt_loader import resolve_prompt_path


@pytest.fixture
def temp_root(tmp_path):
    """Create a temporary root directory."""
    root = tmp_path / "repo"
    root.mkdir()
    return root


# --- skill_loader path validation ---

def test_skill_rejects_absolute_path_outside_root(temp_root):
    """Test that skill_loader rejects absolute paths outside root."""
    outside_path = Path("/etc/passwd")
    with pytest.raises(SkillPathSandboxError):
        skill_validate_path(outside_path, temp_root)


def test_skill_rejects_parent_traversal(temp_root):
    """Test that skill_loader rejects paths with parent traversal."""
    traversal_path = temp_root / ".." / ".." / "etc" / "passwd"
    with pytest.raises(SkillPathSandboxError):
        skill_validate_path(traversal_path, temp_root)


def test_skill_accepts_valid_relative_path(temp_root):
    """Test that skill_loader accepts valid paths within root."""
    valid_path = temp_root / "skills" / "discovery.skill"
    # Should not raise
    skill_validate_path(valid_path, temp_root)


def test_skill_accepts_absolute_path_within_root(temp_root):
    """Test that skill_loader accepts absolute paths within root."""
    valid_path = (temp_root / "skills" / "discovery.skill").resolve()
    # Should not raise
    skill_validate_path(valid_path, temp_root)


# --- prompt_loader path validation ---

def test_prompt_rejects_absolute_path_outside_root(temp_root):
    """Test that prompt_loader rejects absolute paths outside root."""
    outside_path = Path("/etc/passwd")
    with pytest.raises(PromptPathSandboxError):
        prompt_validate_path(outside_path, temp_root)


def test_prompt_rejects_parent_traversal(temp_root):
    """Test that prompt_loader rejects paths with parent traversal."""
    traversal_path = temp_root / ".." / ".." / "etc" / "passwd"
    with pytest.raises(PromptPathSandboxError):
        prompt_validate_path(traversal_path, temp_root)


def test_prompt_accepts_valid_relative_path(temp_root):
    """Test that prompt_loader accepts valid paths within root."""
    valid_path = temp_root / "prompts" / "discover" / "repo-facts.prompt"
    # Should not raise
    prompt_validate_path(valid_path, temp_root)


def test_prompt_accepts_absolute_path_within_root(temp_root):
    """Test that prompt_loader accepts absolute paths within root."""
    valid_path = (temp_root / "prompts" / "discover" / "repo-facts.prompt").resolve()
    # Should not raise
    prompt_validate_path(valid_path, temp_root)


# --- resolve_prompt_path sandbox ---

def test_resolve_prompt_path_rejects_traversal(temp_root):
    """Test that resolve_prompt_path rejects traversal attempts."""
    with pytest.raises(PromptPathSandboxError):
        resolve_prompt_path("../../etc/passwd", temp_root)


def test_resolve_prompt_path_accepts_valid_ref(temp_root):
    """Test that resolve_prompt_path accepts valid prompt references."""
    result = resolve_prompt_path("prompts/discover/repo-facts.prompt", temp_root)
    assert result == temp_root / "prompts" / "discover" / "repo-facts.prompt"
