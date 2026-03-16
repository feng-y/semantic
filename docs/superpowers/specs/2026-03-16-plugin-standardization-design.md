# Plugin Standardization Design

**Date:** 2026-03-16
**Status:** Approved for Implementation

## Problem

The semantic-harness plugin cannot be installed via Claude Code's plugin system because:

1. Missing `.claude-plugin/plugin.json` (required by Claude Code)
2. Using non-standard `manifest.yaml` (not recognized by Claude Code)
3. Skills use `.skill` file format instead of standard `SKILL.md` format
4. Skills are flat files instead of subdirectories with `SKILL.md`

## Solution

Refactor to 100% Claude Code standard plugin structure:

1. Create `.claude-plugin/plugin.json` as the single source of truth
2. Delete `manifest.yaml`
3. Convert 7 skills from `.skill` files to `skills/<name>/SKILL.md` format
4. Update Python runtime to read `plugin.json` instead of `manifest.yaml`
5. Keep `.claude-plugin/marketplace.json` for marketplace distribution

## Architecture

### Directory Structure

```
semantic-harness/
├── .claude-plugin/
│   ├── plugin.json          # NEW: Main plugin manifest
│   └── marketplace.json     # KEEP: Marketplace metadata
├── skills/                  # RESTRUCTURE
│   ├── semantic-init/       # NEW: Directory per skill
│   │   └── SKILL.md        # NEW: YAML frontmatter + markdown
│   ├── semantic-discover/
│   │   └── SKILL.md
│   ├── semantic-review/
│   │   └── SKILL.md
│   ├── semantic-refine/
│   │   └── SKILL.md
│   ├── semantic-baseline/
│   │   └── SKILL.md
│   ├── semantic-status/
│   │   └── SKILL.md
│   └── semantic-reset/
│       └── SKILL.md
├── src/                     # UPDATE: Read plugin.json
│   ├── dispatcher.py        # UPDATE: Load from plugin.json
│   └── ...
├── manifest.yaml            # DELETE
└── pyproject.toml          # KEEP
```

### plugin.json Structure

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

### SKILL.md Format

**Key Discovery:** Claude Code uses YAML frontmatter + Markdown body format. The frontmatter contains ALL metadata including complex fields like `steps` arrays.

**Reference:** Verified from oh-my-claudecode plugin at `~/.claude/plugins/cache/omc/oh-my-claudecode/4.8.2/skills/cancel/SKILL.md`

Each skill follows this structure:

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

Run this command first before any semantic operations.

## Output

Creates the `docs/fact/` directory structure if it doesn't exist.
```

**For skills with steps (like semantic-discover):**

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

[Documentation content here]
```

**Critical:** The `steps` array stays in YAML frontmatter, NOT in markdown body.

## Component Details

### 1. Plugin Manifest (plugin.json)

**Purpose:** Single source of truth for plugin metadata and configuration.

**Fields:**
- `name`: Plugin identifier (must match directory name)
- `version`: Semantic version (sync with pyproject.toml)
- `description`: One-line description
- `author`: Author metadata (name, email)
- `repository`: Git repository URL
- `homepage`: Documentation/homepage URL
- `license`: License identifier (MIT)
- `keywords`: Search tags for marketplace
- `skills`: Path to skills directory (`./skills/`)

**Auto-discovery:** Claude Code automatically discovers all `SKILL.md` files in the skills directory.

### 2. Skills Migration

**Current Format (.skill files):**
```yaml
name: semantic-init
description: Initialize the semantic harness workspace directory structure.
entrypoint: src.dispatcher._handle_init
prompt: null
```

**New Format (SKILL.md):**
```markdown
---
name: semantic-init
description: Initialize the semantic harness workspace directory structure
entrypoint: src.dispatcher._handle_init
---

# Semantic Init

[Documentation content here]
```

**Migration for each skill:**

1. **semantic-init**
   - Entrypoint: `src.dispatcher._handle_init`
   - No prompt
   - Simple initialization

2. **semantic-discover**
   - Entrypoint: `src.discovery_executor.run_discovery`
   - Multi-step pipeline
   - References prompts and protocols

3. **semantic-review**
   - Entrypoint: `src.dispatcher._handle_review`
   - Presents artifacts for review

4. **semantic-refine**
   - Entrypoint: `src.refine_executor.run_refine`
   - Patches artifacts with feedback

5. **semantic-baseline**
   - Entrypoint: `src.refine_executor.run_baseline`
   - Synthesizes accepted baseline

6. **semantic-status**
   - Entrypoint: `src.state_inspector.report_status`
   - Reports current state

7. **semantic-reset**
   - Entrypoint: `src.dispatcher._handle_reset`
   - Resets working state

### 3. Python Runtime Updates

**CORRECTION:** The file that needs updating is `src/skill_loader.py`, NOT `dispatcher.py`.

**File: src/skill_loader.py**

**Current implementation:**
```python
def load_skill(skill_path: str | Path, root: Path | None = None) -> dict[str, Any]:
    """Parse a .skill YAML file and return a structured dict."""
    path = Path(skill_path)
    # ... validation ...
    text = path.read_text()
    skill = yaml.safe_load(text)  # Loads entire file as YAML
    # ... validation ...
    return skill
```

**New implementation (parse YAML frontmatter from markdown):**
```python
import re

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
    path = Path(skill_path)
    # ... validation ...
    text = path.read_text()

    # Extract YAML frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not frontmatter_match:
        raise SkillLoadError(f"No YAML frontmatter found in {path}")

    frontmatter_text = frontmatter_match.group(1)
    try:
        skill = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise SkillLoadError(f"Invalid YAML frontmatter in {path}: {e}") from e

    # ... validation ...
    skill["_path"] = str(path)
    return skill
```

**File: src/skill_loader.py - load_all_skills()**

**Current:**
```python
def load_all_skills(manifest_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load all skills referenced in manifest.yaml."""
    # Reads manifest.yaml, loads each .skill file
```

**New (Option A - Keep manifest.yaml internally):**
```python
def load_all_skills(manifest_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load all skills referenced in manifest.yaml.

    Note: manifest.yaml is kept for internal use. Claude Code discovers
    skills via plugin.json pointing to ./skills/ directory.
    """
    # Same logic, but now loads SKILL.md files instead of .skill files
    # Update path resolution: skills/semantic-init.skill -> skills/semantic-init/SKILL.md
```

**New (Option B - Read from plugin.json):**
```python
def load_all_skills(plugin_json_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load all skills from plugin.json skills directory.

    Auto-discovers all SKILL.md files in the skills directory.
    """
    import json
    path = Path(plugin_json_path)
    with open(path) as f:
        config = json.load(f)

    skills_dir = path.parent.parent / config["skills"].lstrip("./")
    skills = {}

    # Auto-discover all SKILL.md files
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skill = load_skill(skill_file, root=skills_dir.parent)
                skills[skill["name"]] = skill

    return skills
```

**Recommendation:** Use Option A during migration (keep manifest.yaml for Python runtime), then migrate to Option B later if needed.

**Changes needed:**
1. Update `load_skill()` to parse YAML frontmatter from markdown
2. Update `load_all_skills()` to look for `SKILL.md` files in subdirectories
3. Update path resolution: `skills/semantic-init.skill` → `skills/semantic-init/SKILL.md`
4. Update tests that reference `.skill` files

### 4. Marketplace Configuration

**Keep existing `.claude-plugin/marketplace.json`:**

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "semantic-harness-marketplace",
  "version": "0.0.1",
  "description": "Marketplace for semantic harness plugin",
  "owner": {
    "name": "feng-y",
    "email": "feng-y@users.noreply.github.com"
  },
  "plugins": [
    {
      "name": "semantic-harness",
      "version": "0.0.1",
      "description": "Evidence-driven semantic construction pipeline for Claude Code",
      "author": {
        "name": "feng-y",
        "email": "feng-y@users.noreply.github.com"
      },
      "source": "./",
      "category": "productivity",
      "homepage": "https://github.com/feng-y/semantic",
      "tags": [
        "semantic",
        "repository-analysis",
        "documentation"
      ]
    }
  ]
}
```

**Note:** This file is separate from `plugin.json` and only used for marketplace distribution.

### 5. Skill Discovery Mechanism

**How Claude Code discovers skills:**

Based on verified oh-my-claudecode plugin structure at `~/.claude/plugins/cache/omc/oh-my-claudecode/4.8.2/`:
- `plugin.json` contains: `"skills": "./skills/"`
- Claude Code auto-discovers all subdirectories in `./skills/`
- Each subdirectory must contain a `SKILL.md` file
- Skill name comes from YAML frontmatter `name` field, NOT directory name
- Directory name convention: use skill name (e.g., `semantic-init/` for skill named `semantic-init`)

**Auto-discovery rules:**
```
skills/
  ├── semantic-init/
  │   └── SKILL.md          # name: semantic-init
  ├── semantic-discover/
  │   └── SKILL.md          # name: semantic-discover
  └── semantic-review/
      └── SKILL.md          # name: semantic-review
```

Claude Code scans `./skills/` and loads all `SKILL.md` files found in subdirectories.

**No explicit registration needed** - the `"skills": "./skills/"` pointer triggers auto-discovery.

### 6. Entrypoint Field Clarification

**Question:** Does Claude Code support Python entrypoints?

**Answer:** Yes, but indirectly through our Python runtime:

1. **SKILL.md frontmatter** contains: `entrypoint: src.dispatcher._handle_init`
2. **Claude Code** invokes the skill (triggers our Python runtime)
3. **Python runtime** (`src/dispatcher.py`) reads the skill definition
4. **Dispatcher** calls the entrypoint function specified in the skill

**How it works:**
- Claude Code doesn't directly call Python functions
- Instead, it invokes the skill as a command
- Our Python runtime receives the command
- Dispatcher reads the skill definition and calls the entrypoint function

**This means:**
- Entrypoint format stays the same: `src.module.function`
- Python runtime must be invokable (via `python -m` or entry point script)
- The skill system is a layer on top of our Python runtime

**No changes needed to entrypoint format** - it's consumed by our Python code, not by Claude Code directly.

## Installation Methods

After this refactor, the plugin will support all standard installation methods:

### Local Installation
```bash
# Plugin lives in project directory
/path/to/project/.claude-plugin/
```

### Marketplace Installation
```bash
# Add marketplace
/plugin marketplace add https://github.com/feng-y/semantic

# Install plugin
/plugin install semantic-harness
```

### Git Installation
```bash
# Direct from GitHub
/plugin install github:feng-y/semantic
```

## Testing Strategy

### 1. Structure Validation
- Verify `.claude-plugin/plugin.json` exists and is valid JSON
- Verify all 7 skills have `skills/<name>/SKILL.md` files
- Verify YAML frontmatter is valid in each SKILL.md
- Verify `manifest.yaml` is deleted

### 2. Functional Testing
- Run existing pytest suite (should still pass)
- Test each skill invocation via Claude Code
- Verify Python runtime loads plugin.json correctly
- Verify entrypoints still work

### 3. Installation Testing
- Test local installation (copy to project)
- Test marketplace installation (if published)
- Verify skills appear in `/` command list
- Verify skill execution works

## Migration Steps

### Phase 1: Create New Structure (No Breaking Changes)
1. Create `.claude-plugin/plugin.json`
2. Create `skills/<name>/` directories
3. Create `SKILL.md` files with content from `.skill` files
4. Keep old `.skill` files and `manifest.yaml` temporarily

### Phase 1.5: Verify Claude Code Recognition (CRITICAL)

**Goal:** Confirm Claude Code recognizes the plugin before modifying Python runtime.

**Steps:**
1. Test local installation: `/plugin install /path/to/semantic-harness`
2. Verify plugin appears: `/plugin list`
3. Check skills are discoverable: try `/semantic-init`, `/semantic-discover`, etc.
4. Check Claude Code console for errors

**Success Criteria:**
- ✅ Plugin shows up in `/plugin list`
- ✅ All 7 skills are discoverable (appear in autocomplete)
- ✅ Skills can be invoked (even if execution fails due to Python runtime)
- ✅ No errors in Claude Code console about plugin structure

**If verification fails:**
- DO NOT proceed to Phase 2
- Debug plugin.json format
- Check SKILL.md frontmatter syntax
- Verify directory structure matches standard
- Consult Claude Code documentation or working plugin examples

**Only proceed to Phase 2 after successful verification.**

### Phase 2: Update Python Runtime
5. Update `src/skill_loader.py` to parse YAML frontmatter from SKILL.md
6. Update `src/skill_loader.py` load_all_skills() to discover SKILL.md files
7. Update tests to use new skill format
8. Run pytest to verify no regressions

### Phase 3: Cleanup
9. Delete `manifest.yaml`
10. Delete old `.skill` files
11. Update documentation (README.md, INSTALL.md, USER_GUIDE.md)
12. Commit changes

### Phase 4: Verification
13. Test local installation
14. Test skill invocation
15. Run full test suite
16. Update CHANGELOG.md

## Documentation Updates

### README.md
- Update installation instructions
- Update "Repository Structure" section
- Remove references to `manifest.yaml`
- Add plugin installation methods

### INSTALL.md
- Add plugin installation instructions
- Update verification steps
- Add troubleshooting for plugin issues

### USER_GUIDE.md
- Update skill invocation examples
- Add plugin-specific notes

## Risks and Mitigations

### Risk 1: Breaking Existing Tests
**Mitigation:** Phase 1 keeps old files, allowing gradual migration and testing.

### Risk 2: Python Runtime Fails to Load plugin.json
**Mitigation:** Add comprehensive error handling and fallback logic.

### Risk 3: Skills Don't Appear in Claude Code
**Mitigation:** Follow exact standard format from official examples, test locally before cleanup.

### Risk 4: Entrypoints Break
**Mitigation:** Keep entrypoint paths identical, only change config loading.

## Success Criteria

1. ✅ `.claude-plugin/plugin.json` exists and is valid
2. ✅ All 7 skills have `skills/<name>/SKILL.md` files
3. ✅ `manifest.yaml` is deleted
4. ✅ All pytest tests pass
5. ✅ Plugin installs successfully via `/plugin install`
6. ✅ All skills appear in `/` command list
7. ✅ All skills execute correctly
8. ✅ Documentation is updated

## Timeline

- **Phase 1:** 30 minutes (create new structure)
- **Phase 2:** 45 minutes (update Python runtime)
- **Phase 3:** 15 minutes (cleanup)
- **Phase 4:** 30 minutes (verification)
- **Total:** ~2 hours

## References

- [Claude Code Plugin Documentation](https://code.claude.com/docs/en/plugin-marketplaces)
- [Official Plugin Examples](https://github.com/anthropics/claude-plugins-official)
- [oh-my-claudecode Plugin Structure](https://github.com/Yeachan-Heo/oh-my-claudecode)
- Research findings from document-specialist agent
