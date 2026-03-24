# Plugin Standardization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor semantic-harness to 100% Claude Code standard plugin structure

**Architecture:** Convert from manifest.yaml + .skill files to plugin.json + SKILL.md format. Update Python runtime to parse YAML frontmatter. Maintain backward compatibility during migration with phased rollout.

**Tech Stack:** Python 3.12, pytest, YAML, regex for frontmatter parsing

**Spec:** docs/superpowers/specs/2026-03-16-plugin-standardization-design.md

---

## Pre-Implementation Checks

### Task 0: Verify Test Coverage

**Files:**
- Read: `tests/test_skill_system_step1.py`
- Read: `src/skill_loader.py`

- [ ] **Step 1: Check existing test coverage**

Run: `pytest tests/test_skill_system_step1.py -v`

Expected: All tests pass, covering:
- `test_all_skill_files_exist`
- `test_all_skills_load`
- `test_all_skills_have_description`
- `test_all_skills_have_entrypoint`
- `test_prompt_paths_exist`

- [ ] **Step 2: Document manifest.yaml references**

Run: `grep -r "manifest.yaml" --include="*.md" --include="*.py" . | grep -v ".git" | wc -l`

Expected: ~58 references found

Note: These will be updated in Phase 3.

---

## Chunk 1: Phase 1 - Create New Structure

### Task 1: Create plugin.json

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Create plugin.json with metadata**

```json
{
  "name": "semantic-harness",
  "version": "0.0.1",
  "description": "Evidence-driven semantic construction pipeline for Claude Code",
  "author": {
    "name": "feng-y",
    "email": "feng-y@users.noreply.github.com"
  },
  "repository": "https://github.com/feng-y/semantic",
  "homepage": "https://github.com/feng-y/semantic",
  "license": "MIT",
  "keywords": [
    "semantic",
    "repository-analysis",
    "documentation",
    "claude-code",
    "plugin"
  ],
  "skills": "./skills/"
}
```

- [ ] **Step 2: Verify JSON is valid**

Run: `python3 -m json.tool .claude-plugin/plugin.json`

Expected: JSON formatted output, no errors

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: add Claude Code plugin.json manifest"
```

### Task 2: Convert semantic-init skill

**Files:**
- Read: `skills/semantic-init.skill`
- Create: `skills/semantic-init/SKILL.md`

- [ ] **Step 1: Create directory**

Run: `mkdir -p skills/semantic-init`

- [ ] **Step 2: Read current skill content**

Run: `cat skills/semantic-init.skill`

- [ ] **Step 3: Create SKILL.md with frontmatter**

```markdown
---
name: semantic-init
description: Initialize the semantic harness workspace directory structure
entrypoint: src.dispatcher._handle_init
---

# Semantic Init

Initialize the semantic harness workspace with the following structure:

- `docs/fact/schemas/` — artifact schema definitions
- `docs/fact/discovery/` — versioned working artifacts
- `docs/fact/review/` — review summary, architect feedback
- `docs/fact/baseline/` — accepted baseline (immutable)

## Usage

Run this command first before any semantic operations:

```
/semantic-init
```

## Output

Creates the `docs/fact/` directory structure if it doesn't exist.

## Implementation

Entrypoint: `src.dispatcher._handle_init`

This skill has no steps - it's a simple initialization command.
```

- [ ] **Step 4: Verify frontmatter syntax**

Run: `python3 -c "import yaml, re; text=open('skills/semantic-init/SKILL.md').read(); m=re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL); print(yaml.safe_load(m.group(1)) if m else 'FAIL')"`

Expected: Dict with name, description, entrypoint

- [ ] **Step 5: Commit**

```bash
git add skills/semantic-init/
git commit -m "feat: convert semantic-init to SKILL.md format"
```

### Task 3: Convert semantic-discover skill

**Files:**
- Read: `skills/semantic-discover.skill`
- Create: `skills/semantic-discover/SKILL.md`

- [ ] **Step 1: Create directory**

Run: `mkdir -p skills/semantic-discover`

- [ ] **Step 2: Read current skill content**

Run: `cat skills/semantic-discover.skill`

- [ ] **Step 3: Create SKILL.md with frontmatter including steps**

```markdown
---
name: semantic-discover
description: >
  Run full semantic discovery pipeline: sampling, fact extraction,
  evidence augmentation, domain analysis, repo understanding,
  knowledge confidence, and review summary.
entrypoint: src.discovery_executor.run_discovery
steps:
  - run: prompts/discover/repo-sampling.prompt
  - run: prompts/discover/repo-facts.prompt
  - run: prompts/discover/evidence-extraction.prompt
  - run: prompts/validation/validate-artifact.prompt
  - run: prompts/discover/domain-candidates.prompt
  - run: prompts/discover/repo-understanding.prompt
  - run: prompts/validation/validate-artifact.prompt
  - run: prompts/discover/knowledge-confidence.prompt
  - run: prompts/discover/review-summary.prompt
  - apply: protocols/artifact-versioning.md
---

# Semantic Discover

Run the full semantic discovery pipeline to extract repository understanding.

## Pipeline Steps

1. **Repository Sampling** - Sample codebase structure
2. **Fact Extraction** - Extract facts with evidence
3. **Evidence Augmentation** - Enhance facts with context
4. **Domain Analysis** - Identify domain candidates
5. **Repository Understanding** - Build conceptual model
6. **Knowledge Confidence** - Assess understanding quality
7. **Review Summary** - Generate review report

## Usage

```
/semantic-discover
```

## Output

Creates versioned artifacts in `docs/fact/discovery/`:
- `repo-facts.vN.md`
- `domain-candidates.vN.md`
- `repo-understanding.vN.md`
- `knowledge-confidence.vN.md`
- `review/review-summary.vN.md`

## Implementation

Entrypoint: `src.discovery_executor.run_discovery`

The pipeline executes each step sequentially, with validation checkpoints.
```

- [ ] **Step 4: Verify frontmatter with steps array**

Run: `python3 -c "import yaml, re; text=open('skills/semantic-discover/SKILL.md').read(); m=re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL); data=yaml.safe_load(m.group(1)) if m else {}; print(f\"steps: {len(data.get('steps', []))}\")"`

Expected: `steps: 10`

- [ ] **Step 5: Commit**

```bash
git add skills/semantic-discover/
git commit -m "feat: convert semantic-discover to SKILL.md format"
```

### Task 4: Convert semantic-review skill

**Files:**
- Read: `skills/semantic-review.skill`
- Create: `skills/semantic-review/SKILL.md`

- [ ] **Step 1: Create directory and SKILL.md**

Run: `mkdir -p skills/semantic-review`

Content:
```markdown
---
name: semantic-review
description: Present discovery artifacts for architect review
entrypoint: src.dispatcher._handle_review
---

# Semantic Review

Present the latest discovery artifacts for review.

## What It Shows

- Latest version of all discovery artifacts
- Review summary
- Instructions for providing feedback

## Usage

```
/semantic-review
```

## Next Steps

After review, edit `docs/fact/review/architect-feedback.md` with your feedback, then run `/semantic-refine`.

## Implementation

Entrypoint: `src.dispatcher._handle_review`
```

- [ ] **Step 2: Commit**

```bash
git add skills/semantic-review/
git commit -m "feat: convert semantic-review to SKILL.md format"
```

### Task 5: Convert semantic-refine skill

**Files:**
- Read: `skills/semantic-refine.skill`
- Create: `skills/semantic-refine/SKILL.md`

- [ ] **Step 1: Create directory and SKILL.md**

Run: `mkdir -p skills/semantic-refine`

Content:
```markdown
---
name: semantic-refine
description: Patch discovery artifacts using architect feedback
entrypoint: src.refine_executor.run_refine
---

# Semantic Refine

Apply architect feedback to refine discovery artifacts.

## What It Does

1. Reads `docs/fact/review/architect-feedback.md`
2. Patches artifacts based on feedback
3. Increments version numbers
4. Logs changes to `semantic-change-log.md`
5. If `acceptance: true` in feedback, synthesizes baseline

## Usage

```
/semantic-refine
```

## Prerequisites

- Discovery artifacts exist
- Architect feedback has been written

## Output

- Updated versioned artifacts in `docs/fact/discovery/`
- Change log in `docs/fact/review/semantic-change-log.md`
- Baseline artifacts (if accepted)

## Implementation

Entrypoint: `src.refine_executor.run_refine`
```

- [ ] **Step 2: Commit**

```bash
git add skills/semantic-refine/
git commit -m "feat: convert semantic-refine to SKILL.md format"
```

### Task 6: Convert semantic-baseline skill

**Files:**
- Read: `skills/semantic-baseline.skill`
- Create: `skills/semantic-baseline/SKILL.md`

- [ ] **Step 1: Create directory and SKILL.md**

Run: `mkdir -p skills/semantic-baseline`

Content:
```markdown
---
name: semantic-baseline
description: Synthesize accepted baseline from discovery artifacts
entrypoint: src.refine_executor.run_baseline
---

# Semantic Baseline

Synthesize immutable baseline artifacts from accepted discovery.

## What It Creates

- `docs/fact/baseline/purpose.md`
- `docs/fact/baseline/domains.md`
- `docs/fact/baseline/concepts.md`
- `docs/fact/baseline/pipelines.md`
- `docs/fact/baseline/checkpoint.json`

## Usage

```
/semantic-baseline
```

## Prerequisites

- Discovery artifacts accepted (via `/semantic-refine` with `acceptance: true`)
- All structural gates passed

## Implementation

Entrypoint: `src.refine_executor.run_baseline`
```

- [ ] **Step 2: Commit**

```bash
git add skills/semantic-baseline/
git commit -m "feat: convert semantic-baseline to SKILL.md format"
```

### Task 7: Convert semantic-status skill

**Files:**
- Read: `skills/semantic-status.skill`
- Create: `skills/semantic-status/SKILL.md`

- [ ] **Step 1: Create directory and SKILL.md**

Run: `mkdir -p skills/semantic-status`

Content:
```markdown
---
name: semantic-status
description: Report current semantic harness state
entrypoint: src.state_inspector.report_status
---

# Semantic Status

Report the current state of the semantic harness workspace.

## What It Shows

- Latest artifact versions
- Baseline status
- Pending feedback
- Workspace health

## Usage

```
/semantic-status
```

## Implementation

Entrypoint: `src.state_inspector.report_status`
```

- [ ] **Step 2: Commit**

```bash
git add skills/semantic-status/
git commit -m "feat: convert semantic-status to SKILL.md format"
```

### Task 8: Convert semantic-reset skill

**Files:**
- Read: `skills/semantic-reset.skill`
- Create: `skills/semantic-reset/SKILL.md`

- [ ] **Step 1: Create directory and SKILL.md**

Run: `mkdir -p skills/semantic-reset`

Content:
```markdown
---
name: semantic-reset
description: Reset semantic harness working state
entrypoint: src.dispatcher._handle_reset
---

# Semantic Reset

Reset the working state (discovery and review artifacts), preserving baseline.

## What It Does

- Deletes `docs/fact/discovery/` contents
- Deletes `docs/fact/review/` contents (except schemas)
- Preserves `docs/fact/baseline/` (immutable)
- Preserves `docs/fact/schemas/`

## Usage

```
/semantic-reset
```

## Warning

This is destructive. Use when you want to start discovery from scratch.

## Implementation

Entrypoint: `src.dispatcher._handle_reset`
```

- [ ] **Step 2: Commit**

```bash
git add skills/semantic-reset/
git commit -m "feat: convert semantic-reset to SKILL.md format"
```

---

## Chunk 2: Phase 1.5 - Verification

### Task 9: Verify Claude Code Recognition

**Files:**
- Test: `.claude-plugin/plugin.json`
- Test: `skills/*/SKILL.md`

- [ ] **Step 1: Test local plugin installation**

Run: `/plugin install /Users/yan./git/3p/sematic-harness`

Expected: Plugin installs successfully

- [ ] **Step 2: Verify plugin appears in list**

Run: `/plugin list`

Expected: `semantic-harness` appears in the list

- [ ] **Step 3: Check skill discovery**

Type: `/semantic-` and check autocomplete

Expected: All 7 skills appear:
- semantic-init
- semantic-discover
- semantic-review
- semantic-refine
- semantic-baseline
- semantic-status
- semantic-reset

- [ ] **Step 4: Verify no errors in console**

Check Claude Code console for any plugin loading errors.

Expected: No errors related to semantic-harness

**GATE: Only proceed to Phase 2 if all verification steps pass.**

---

## Chunk 3: Phase 2 - Update Python Runtime

### Task 10: Update skill_loader.py to parse frontmatter

**Files:**
- Modify: `src/skill_loader.py:37-66`

- [ ] **Step 1: Add frontmatter parsing to load_skill()**

Replace the current `yaml.safe_load(text)` logic with frontmatter extraction:

```python
def load_skill(skill_path: str | Path, root: Path | None = None) -> dict[str, Any]:
    """Parse a SKILL.md file with YAML frontmatter and return a structured dict.

    Format:
    ---
    name: skill-name
    description: ...
    entrypoint: ...
    steps:
      - run: ...
    ---

    # Markdown content
    """
    import re

    path = Path(skill_path)
    if root is not None:
        _validate_path(path, root)
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {path}")

    text = path.read_text(encoding='utf-8')

    # Extract YAML frontmatter
    # Handle both \n and \r\n line endings
    frontmatter_pattern = r'^---\r?\n(.*?)\r?\n---\r?\n'
    frontmatter_match = re.match(frontmatter_pattern, text, re.DOTALL)

    if not frontmatter_match:
        raise SkillLoadError(f"No YAML frontmatter found in {path}")

    frontmatter_text = frontmatter_match.group(1)
    try:
        skill = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise SkillLoadError(f"Invalid YAML frontmatter in {path}: {e}") from e

    if not isinstance(skill, dict):
        raise SkillLoadError(f"Skill frontmatter must be a YAML mapping, got {type(skill).__name__}: {path}")

    missing = REQUIRED_FIELDS - skill.keys()
    if missing:
        raise SkillLoadError(f"Missing required fields {missing} in {path}")

    skill["_path"] = str(path)
    return skill
```

- [ ] **Step 2: Verify the change compiles**

Run: `python3 -m py_compile src/skill_loader.py`

Expected: No syntax errors

- [ ] **Step 3: Commit**

```bash
git add src/skill_loader.py
git commit -m "feat: update skill_loader to parse YAML frontmatter from SKILL.md"
```

### Task 11: Update tests for new skill format

**Files:**
- Modify: `tests/test_skill_system_step1.py:28-65`

- [ ] **Step 1: Update test to look for SKILL.md files**

Replace skill file paths:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_skill_system_step1.py -v`

Expected: All 5 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_skill_system_step1.py
git commit -m "test: update skill tests for SKILL.md format"
```

### Task 12: Run full test suite

**Files:**
- Test: All test files

- [ ] **Step 1: Run pytest**

Run: `pytest -v`

Expected: All tests pass (108 tests)

- [ ] **Step 2: If any tests fail, investigate and fix**

Check test output for failures related to skill loading.

- [ ] **Step 3: Verify skill loading works end-to-end**

Run: `python3 -c "from src.skill_loader import load_skill; from pathlib import Path; skill = load_skill(Path('skills/semantic-init/SKILL.md')); print(skill['name'])"`

Expected: `semantic-init`

---

## Chunk 4: Phase 3 - Cleanup

### Task 13: Delete old skill files

**Files:**
- Delete: `skills/*.skill` (7 files)
- Delete: `manifest.yaml`

- [ ] **Step 1: Verify new format works before deletion**

Run: `pytest tests/test_skill_system_step1.py -v`

Expected: All tests pass

- [ ] **Step 2: Delete old .skill files**

Run: `rm skills/*.skill`

Expected: 7 files deleted

- [ ] **Step 3: Delete manifest.yaml**

Run: `rm manifest.yaml`

- [ ] **Step 4: Verify tests still pass**

Run: `pytest tests/test_skill_system_step1.py -v`

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove old .skill files and manifest.yaml"
```

### Task 14: Update documentation references

**Files:**
- Modify: `README.md`
- Modify: `INSTALL.md`
- Modify: `USER_GUIDE.md`
- Modify: All files with manifest.yaml references

- [ ] **Step 1: Find all manifest.yaml references**

Run: `grep -r "manifest.yaml" --include="*.md" --include="*.py" . | grep -v ".git"`

Expected: ~58 references

- [ ] **Step 2: Update README.md**

Remove references to manifest.yaml, update plugin installation instructions.

- [ ] **Step 3: Update INSTALL.md**

Add plugin installation methods, remove manifest.yaml references.

- [ ] **Step 4: Update USER_GUIDE.md**

Update skill invocation examples to use `/semantic-*` format.

- [ ] **Step 5: Update any Python files referencing manifest.yaml**

Check `src/` directory for any remaining references.

- [ ] **Step 6: Verify no references remain**

Run: `grep -r "manifest.yaml" --include="*.md" --include="*.py" . | grep -v ".git" | wc -l`

Expected: 0

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: update all manifest.yaml references to plugin.json"
```

---

## Chunk 5: Phase 4 - Final Verification

### Task 15: Test plugin installation

**Files:**
- Test: Complete plugin structure

- [ ] **Step 1: Uninstall plugin if installed**

Run: `/plugin uninstall semantic-harness`

- [ ] **Step 2: Reinstall plugin**

Run: `/plugin install /Users/yan./git/3p/sematic-harness`

Expected: Plugin installs successfully

- [ ] **Step 3: Verify all skills work**

Test each skill:
- `/semantic-init` - should create directory structure
- `/semantic-status` - should report status
- `/semantic-discover` - should run discovery (may take time)
- `/semantic-review` - should show artifacts
- `/semantic-refine` - should apply feedback
- `/semantic-baseline` - should synthesize baseline
- `/semantic-reset` - should reset state

- [ ] **Step 4: Run full test suite**

Run: `pytest -v`

Expected: All 108 tests pass

### Task 16: Update CHANGELOG and finalize

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add entry to CHANGELOG.md**

```markdown
## [0.0.2] - 2026-03-17

### Changed
- **BREAKING**: Migrated to Claude Code standard plugin structure
- Replaced `manifest.yaml` with `.claude-plugin/plugin.json`
- Converted all skills from `.skill` to `SKILL.md` format
- Updated `skill_loader.py` to parse YAML frontmatter
- Updated all documentation to reflect new structure

### Migration Guide
- Plugin now installable via `/plugin install`
- Skills invoked with `/semantic-*` commands
- No changes to skill functionality or behavior
- Python runtime updated to support new format
```

- [ ] **Step 2: Update version in plugin.json**

Change version from "0.0.1" to "0.0.2"

- [ ] **Step 3: Update version in pyproject.toml**

Change version from "0.0.1" to "0.0.2"

- [ ] **Step 4: Update version in marketplace.json**

Change version from "0.0.1" to "0.0.2" (both marketplace and plugin entries)

- [ ] **Step 5: Verify version consistency**

Run: `grep -E '"version":|version =' .claude-plugin/plugin.json .claude-plugin/marketplace.json pyproject.toml`

Expected: All show "0.0.2"

- [ ] **Step 6: Final commit**

```bash
git add CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json pyproject.toml
git commit -m "chore: bump version to 0.0.2 for plugin standardization release"
```

- [ ] **Step 7: Create git tag**

```bash
git tag -a v0.0.2 -m "Plugin standardization release"
```

---

## Success Criteria

- [x] `.claude-plugin/plugin.json` exists and is valid
- [x] All 7 skills have `skills/<name>/SKILL.md` files
- [x] `manifest.yaml` is deleted
- [x] All pytest tests pass (108 tests)
- [x] Plugin installs successfully via `/plugin install`
- [x] All skills appear in `/` command list
- [x] All skills execute correctly
- [x] Documentation is updated (0 manifest.yaml references)
- [x] Version bumped to 0.0.2 consistently

## Timeline

- **Phase 1:** 45 minutes (create structure + 7 skills)
- **Phase 1.5:** 10 minutes (verification)
- **Phase 2:** 30 minutes (update Python runtime + tests)
- **Phase 3:** 45 minutes (cleanup + docs)
- **Phase 4:** 20 minutes (final verification)
- **Total:** ~2.5 hours

## Notes

- Keep old files until Phase 3 for safety
- Phase 1.5 verification is critical - do not skip
- Test coverage exists (test_skill_system_step1.py)
- 58 manifest.yaml references need updating
- Version sync across 3 files (plugin.json, marketplace.json, pyproject.toml)
