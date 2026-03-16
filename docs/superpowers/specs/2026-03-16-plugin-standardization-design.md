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

**File: src/dispatcher.py**

**Current:**
```python
# Reads manifest.yaml
with open('manifest.yaml') as f:
    config = yaml.safe_load(f)
```

**New:**
```python
# Reads .claude-plugin/plugin.json
import json
from pathlib import Path

plugin_root = Path(__file__).parent.parent
plugin_json = plugin_root / '.claude-plugin' / 'plugin.json'

with open(plugin_json) as f:
    config = json.load(f)
```

**Changes needed:**
- Update config loading in `dispatcher.py`
- Update skill discovery logic (if any)
- Update tests that reference `manifest.yaml`

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
4. Keep old `.skill` files temporarily

### Phase 2: Update Python Runtime
5. Update `src/dispatcher.py` to read `plugin.json`
6. Update any other code that reads `manifest.yaml`
7. Update tests to use `plugin.json`
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
