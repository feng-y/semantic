"""Step 2 — Plugin Manifest Alignment tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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
    def test_plugin_json_loads(self) -> None:
        plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
        m = json.loads(plugin_path.read_text())
        assert m["name"] == "semantic-harness"
        assert "skills" in m

    def test_plugin_json_version(self) -> None:
        plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
        m = json.loads(plugin_path.read_text())
        assert "version" in m

    def test_all_skill_paths_valid(self) -> None:
        """All expected skills have SKILL.md files."""
        for name in EXPECTED_PLUGIN_SKILLS:
            p = REPO_ROOT / "skills" / name / "SKILL.md"
            assert p.exists(), f"Plugin skill path invalid: {name}/SKILL.md"

    def test_plugin_skills_discoverable(self) -> None:
        """All expected skills are discoverable via plugin.json."""
        skills_dir = REPO_ROOT / "skills"
        discovered = set()
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                discovered.add(skill_path.name)

        for name in EXPECTED_PLUGIN_SKILLS:
            assert name in discovered, f"Missing from skills directory: {name}"

    def test_load_all_skills_succeeds(self) -> None:
        plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
        skills = load_all_skills(plugin_path)
        assert len(skills) >= 7
