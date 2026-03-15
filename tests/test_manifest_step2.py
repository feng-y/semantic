"""Step 2 — Plugin Manifest Alignment tests."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.skill_loader import load_all_skills

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_PLUGIN_SKILLS = [
    "semantic-init",
    "semantic-discover",
    "semantic-review",
    "semantic-refine",
    "semantic-baseline",
    "semantic-status",
    "semantic-reset",
]


class TestManifestStep2:
    def test_manifest_loads(self) -> None:
        m = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text())
        assert m["name"] == "semantic-harness"
        assert "skills" in m

    def test_manifest_version(self) -> None:
        m = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text())
        assert m["version"] == "1.0.0"

    def test_all_skill_paths_valid(self) -> None:
        m = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text())
        for role, rel_path in m["skills"].items():
            p = REPO_ROOT / rel_path
            assert p.exists(), f"Manifest skill path invalid: {role} -> {rel_path}"

    def test_plugin_skills_in_manifest(self) -> None:
        m = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text())
        skill_files = set(m["skills"].values())
        for name in EXPECTED_PLUGIN_SKILLS:
            expected_path = f"skills/{name}.skill"
            assert expected_path in skill_files, f"Missing from manifest: {expected_path}"

    def test_load_all_skills_succeeds(self) -> None:
        skills = load_all_skills(REPO_ROOT / "manifest.yaml")
        assert len(skills) >= 7
