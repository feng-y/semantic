# AGENTS.md — Agent-First Onboarding for semantic-harness

> Map, not manual. Keep this ~100 lines. Agents read this first.

## What This Repo Is

Semantic Harness is a **Claude Code skill repository** for extracting structured semantic knowledge from a codebase and its git history. Five independent capabilities:

1. **fact** — repo structure discovery → versioned baseline (`docs/fact/`)
2. **semantic** — domain extraction (signals → candidates → review → assets)
3. **demand** — requirement mapping (issue → demand card)
4. **commit-semantic** — git history → semantic cases (in progress)
5. **semantic-extract** — commit + rules/invariants extraction

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Top-level overview, all 5 capabilities |
| `src/dispatcher.py` | Command routing: init/discover/refine/status/reset |
| `src/discovery_executor.py` | Runs FACT discovery pipeline |
| `src/refine_executor.py` | Runs FACT refine + baseline synthesis |
| `src/skill_loader.py` | Loads and routes skill commands |
| `src/semantic/` | Semantic layer (signals, candidates, score, review, finalize) |
| `src/commit_semantic/` | Git history → semantic cases pipeline |
| `src/commit_refine/` | Commit refine + rules/invariants extraction |
| `src/demand/` | Issue → demand card pipeline |
| `skills/` | 20+ Claude Code skill definitions |
| `prompts/` | LLM prompt templates |
| `protocols/` | Artifact versioning, validation, refine rules, review feedback |
| `docs/fact/` | Versioned FACT artifacts (schemas/, discovery/, review/, baseline/) |
| `docs/semantic-design/` | Architecture decision records (001–012) |

## How to Run

```bash
# Install
pip install -e ".[test]"

# Tests (46 passing)
pytest tests/test_system.py -q

# Skill commands (via Claude Code)
/semantic-fact-pipeline    # discover → review → refine → baseline
/semantic-extract --last 10
```

## Architecture Notes

- **Python-only** repo (3.10+), minimal deps (pyyaml + pytest)
- **Skill system**: `skills/<name>/run.py` + `SKILL.md`; dispatcher routes to Python handlers
- **Artifact versioning**: `docs/fact/discovery/repo-facts.vN.md` style; keep latest 3
- **Baseline**: `docs/fact/baseline/` — immutable once accepted
- **Refine loop**: architect writes feedback → `refine` patches artifacts → repeat → `acceptance: true` → baseline
- **Executor injection**: skills accept optional `executor` for LLM calls; use fake executors in tests

## Code Conventions

- **snake_case** throughout Python
- `src/` contains all runtime code; `tests/` mirrors `src/` structure
- Test files: `test_<module>.py`; fixtures: `tests/fixtures/`
- Skills: `skills/<category>/SKILL.md` + `run.py`

## Common Tasks

| Task | How |
|------|-----|
| Add a new skill | Create `skills/<name>/SKILL.md` + `run.py`, register in `.claude-plugin/plugin.json` |
| Add a new semantic stage | Add to `src/semantic/stage_registry.py` |
| Add a new test | Create `tests/test_<module>.py`, use fixtures in `tests/fixtures/` |
| Run discovery | `dispatch("discover", root)` or `/semantic-discover` |
| Inspect state | `from src.state_inspector import inspect` |
| Understand versioning | Read `protocols/artifact-versioning.md` |
