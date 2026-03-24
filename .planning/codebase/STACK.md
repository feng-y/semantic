# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.10+ - All runtime code, CLIs, pipeline orchestration, and skill implementations live under `src/` and `skills/`; version floor is declared in `pyproject.toml`.

**Secondary:**
- Markdown - Prompt templates, skill definitions, and architecture/protocol docs live under `prompts/`, `skills/*/SKILL.md`, `protocols/`, and `docs/`.
- YAML - Skill frontmatter and runtime artifacts are loaded and written in `src/skill_loader.py`, `src/io_utils.py`, `src/demand/*.py`, and `src/semantic/*.py`.
- JSON / JSONL - Plugin metadata and pipeline outputs are stored in `.claude-plugin/plugin.json`, `data/commit-extract/*.jsonl`, `data/commit-semantic/*.jsonl`, and `data/commit-semantic/summary.json`.

## Runtime

**Environment:**
- CPython 3.10 minimum in development and packaging, defined by `pyproject.toml`.
- Python 3.12 in CI, configured in `.github/workflows/ci.yml`.
- Git CLI is a runtime dependency for repository introspection and commit-history pipelines, invoked from `src/context_builder.py`, `src/commit_semantic/git_utils.py`, and `src/commit_semantic/domain_utils.py`.

**Package Manager:**
- pip / setuptools - Package build backend and editable installs are defined in `pyproject.toml`.
- Lockfile: missing

## Frameworks

**Core:**
- Claude Code skill/plugin runtime - The repository is packaged as a Claude Code skill repository via `.claude-plugin/plugin.json`, with skill discovery implemented in `src/skill_loader.py` and dispatching in `src/dispatcher.py`.
- Custom pipeline framework - Stateful multi-stage execution is implemented by `src/skill_runner.py` and `src/harness_state.py`, then specialized in `skills/*/run.py` and `src/semantic/run.py`.

**Testing:**
- pytest 8+ - Test runner configured in `pyproject.toml` and executed in `.github/workflows/ci.yml`.

**Build/Dev:**
- setuptools - Packaging backend in `pyproject.toml`.
- ruff 0.9.0+ - Linting configured in `pyproject.toml`; CI runs `ruff check src/ tests/` in `.github/workflows/ci.yml`.
- mypy 1.0+ - Type checking configured in `pyproject.toml`; CI runs `mypy src/ --ignore-missing-imports` in `.github/workflows/ci.yml`.

## Key Dependencies

**Critical:**
- `pyyaml>=6.0` - Central serialization dependency for skill metadata and semantic artifacts, used in `src/skill_loader.py`, `src/io_utils.py`, `src/demand/*.py`, and `src/semantic/*.py`.
- Python standard library - `argparse`, `json`, `pathlib`, `dataclasses`, `logging`, and `subprocess` provide the CLI, persistence, and orchestration backbone across `src/main.py`, `src/skill_runner.py`, `src/discovery_executor.py`, and `src/commit_semantic/*.py`.

**Infrastructure:**
- `pytest>=8.0` - Test dependency declared in `pyproject.toml`.
- `ruff>=0.9.0` - Lint dependency declared in `pyproject.toml`.
- `mypy>=1.0` - Type-check dependency declared in `pyproject.toml`.
- Claude Code host executor - LLM execution is intentionally injected by protocol rather than imported SDKs; see `src/host_executor.py` and `src/discovery_executor.py`.

## Configuration

**Environment:**
- No `.env` files were detected in the project root during this audit.
- Runtime configuration is file-based and CLI-argument-based rather than environment-variable-based; examples include `--root` in `src/main.py`, stage arguments in `skills/commit-semantic/run.py`, and output-path arguments in `src/demand/run.py`.
- Host LLM execution is supplied externally by Claude Code through the `HostExecutor` protocol in `src/host_executor.py`; this repo does not configure SDK credentials directly.

**Build:**
- `pyproject.toml` - Packaging, Python version, pytest, ruff, and mypy configuration.
- `.github/workflows/ci.yml` - CI test, lint, and informational typecheck pipeline.
- `.claude-plugin/plugin.json` - Claude Code plugin metadata and skills directory registration.

## Platform Requirements

**Development:**
- Python 3.10+ with editable install support via `pip install -e ".[test]"`, documented in `README.md` and encoded in `pyproject.toml`.
- Git must be available on PATH for repo sampling and commit history analysis, as used in `src/context_builder.py`, `src/commit_semantic/git_utils.py`, and `src/commit_semantic/domain_utils.py`.
- Claude Code host environment is required to execute prompt-driven stages through the injected executor defined by `src/host_executor.py`.

**Production:**
- Primary deployment target is local or host-driven CLI execution as a Claude Code plugin/skill repository, exposed by `.claude-plugin/plugin.json` and the `semantic-harness` console script in `pyproject.toml`.
- CI validation runs on GitHub Actions Ubuntu runners in `.github/workflows/ci.yml`; no separate server, container, or cloud deployment target is defined.

---

*Stack analysis: 2026-03-24*
