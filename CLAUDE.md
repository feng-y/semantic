# Semantic Harness

> For agents: Read this first.

## What This Repo Is

Semantic Harness is a **Claude Code skill repository** for extracting structured semantic knowledge from a codebase and its git history. Four independent capabilities:

1. **fact** — repo structure discovery → versioned baseline (`docs/fact/`)
2. **semantic** — domain extraction (signals → candidates → review → assets)
3. **demand** — requirement mapping (issue → demand card)
4. **commit** — commit-extract + commit-semantic for git history analysis (in progress)

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Top-level overview, all 4 capabilities |
| `src/dispatcher.py` | Command routing: init/discover/refine/status/reset |
| `src/discovery_executor.py` | Runs FACT discovery pipeline |
| `src/refine_executor.py` | Runs FACT refine + baseline synthesis |
| `src/skill_loader.py` | Loads and routes skill commands |
| `src/semantic/` | Semantic layer (signals, candidates, score, review, finalize) |
| `src/commit_semantic/` | Git history → semantic cases pipeline |
| `src/commit_refine/` | Commit refine + rules/invariants extraction |
| `src/demand/` | Issue → demand card pipeline |
| `skills/` | Claude Code skill definitions |
| `prompts/` | LLM prompt templates |
| `protocols/` | Artifact versioning, validation, refine rules, review feedback |
| `docs/superpowers/` | Design specs, plans, architecture docs |
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
/commit-extract run
/commit-semantic run
```

## Architecture

Two skill patterns:
- **Python skill**: `skills/<name>/run.py` + `SKILL.md` (deterministic ETL tasks)
- **Team Agent skill**: `SKILL.md` as instruction template + `prompts/` for worker agents (for LLM analysis tasks)

**Team Agent pattern:** Main agent orchestrates via Task tool, workers do isolated LLM analysis. See [docs/superpowers/ARCHITECTURE.md](docs/superpowers/ARCHITECTURE.md).

## Architecture Notes

- **Python-only** repo (3.10+), minimal deps (pyyaml + pytest)
- **Artifact versioning**: `docs/fact/discovery/repo-facts.vN.md` style; keep latest 3
- **Baseline**: `docs/fact/baseline/` — immutable once accepted
- **Refine loop**: architect writes feedback → `refine` patches artifacts → repeat → `acceptance: true` → baseline
- **Executor injection**: skills accept optional `executor` for LLM calls; use fake executors in tests

## Common Tasks

| Task | How |
|------|-----|
| Add a new skill | Create `skills/<name>/SKILL.md` + `run.py`, see [docs/superpowers/ARCHITECTURE.md](docs/superpowers/ARCHITECTURE.md) for Team Agent pattern |
| Add a new semantic stage | Add to `src/semantic/stage_registry.py` |
| Add a new test | Create `tests/test_<module>.py`, use fixtures in `tests/fixtures/` |
| Run discovery | `dispatch("discover", root)` or `/semantic-discover` |
| Inspect state | `from src.state_inspector import inspect` |
| Understand versioning | Read `protocols/artifact-versioning.md` |

## Code Conventions

- **snake_case** throughout Python
- `src/` contains all runtime code; `tests/` mirrors `src/` structure
- Test files: `test_<module>.py`; fixtures: `tests/fixtures/`
- Skills: `skills/<category>/SKILL.md` + `run.py`

## Working Style

- When a design doc or plan exists (`docs/superpowers/specs/`, `docs/plan/`), follow it exactly. Do not deviate without asking first. If you think a different approach is better, explain why and wait for approval.
- When asked for a plan, give a plan — not code. When asked for something simple, keep it simple. Match the level of detail and complexity being asked for.
- Always analyze the repository before generating documentation (CLAUDE.md, AGENTS.md, etc). Never produce generic content — read the actual codebase first.
- CLAUDE.md and AGENTS.md serve different agent systems. Never symlink or unify them without explicit approval.
