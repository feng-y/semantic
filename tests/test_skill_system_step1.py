"""Step 1 — Skill System Normalization tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.skill_loader import load_skill

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_SKILLS = [
    "semantic-init",
    "semantic-discover",
    "semantic-review",
    "semantic-refine",
    "semantic-baseline",
    "semantic-status",
    "semantic-reset",
]


class TestSkillSystemStep1:
    def test_all_skill_files_exist(self) -> None:
        for name in EXPECTED_SKILLS:
            p = REPO_ROOT / "skills" / name / "SKILL.md"
            assert p.exists(), f"Missing skill file: {name}/SKILL.md"

    def test_all_skills_load(self) -> None:
        for name in EXPECTED_SKILLS:
            p = REPO_ROOT / "skills" / name / "SKILL.md"
            skill = load_skill(p)
            assert skill["name"] == name, f"Skill name mismatch: expected {name}, got {skill['name']}"

    def test_all_skills_have_description(self) -> None:
        for name in EXPECTED_SKILLS:
            p = REPO_ROOT / "skills" / name / "SKILL.md"
            skill = load_skill(p)
            desc = skill.get("description") or skill.get("purpose")
            assert desc, f"Skill {name} missing description/purpose"

    def test_all_skills_have_entrypoint(self) -> None:
        for name in EXPECTED_SKILLS:
            p = REPO_ROOT / "skills" / name / "SKILL.md"
            skill = load_skill(p)
            assert "entrypoint" in skill, f"Skill {name} missing entrypoint"

    def test_prompt_paths_exist(self) -> None:
        """Skills with steps must reference existing prompt files."""
        for name in EXPECTED_SKILLS:
            p = REPO_ROOT / "skills" / name / "SKILL.md"
            skill = load_skill(p)
            steps = skill.get("steps", [])
            if not isinstance(steps, list):
                continue
            for step in steps:
                if isinstance(step, dict) and "run" in step:
                    prompt_path = REPO_ROOT / step["run"]
                    assert prompt_path.exists(), (
                        f"Skill {name}: prompt not found: {step['run']}"
                    )
