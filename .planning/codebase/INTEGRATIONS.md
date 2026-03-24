# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**Host LLM execution:**
- Claude Code host environment - Executes prompt-based artifact generation for discovery and team-agent skills.
  - SDK/Client: No direct SDK dependency is imported; execution is injected through the `HostExecutor` protocol in `src/host_executor.py` and consumed by `src/discovery_executor.py`.
  - Auth: Managed outside this repository by the host environment; no env var names are referenced in source.

**Source control / repository inspection:**
- Git CLI - Reads repository trees and commit history for semantic extraction.
  - SDK/Client: Native `git` subprocess calls in `src/context_builder.py`, `src/commit_semantic/git_utils.py`, and `src/commit_semantic/domain_utils.py`.
  - Auth: Uses the caller's local git configuration and repository access; no repo-level auth wiring is implemented here.

**CI service:**
- GitHub Actions - Runs automated test, lint, and typecheck workflows.
  - SDK/Client: Workflow definition in `.github/workflows/ci.yml` using `actions/checkout@v4` and `actions/setup-python@v5`.
  - Auth: Standard GitHub Actions runner context; no custom token handling is defined in the repository.

## Data Storage

**Databases:**
- Not detected
  - Connection: Not applicable
  - Client: Not applicable

**File Storage:**
- Local filesystem only
  - Versioned FACT artifacts are stored under `docs/fact/` by `src/artifact_writer.py`.
  - Runtime state is stored under `.harness/` by `src/harness_state.py`.
  - Commit-analysis outputs are written under `data/commit-extract/` and `data/commit-semantic/`, documented in `README.md` and `skills/commit-*/SKILL.md`.

**Caching:**
- Local filesystem caches only
  - Semantic stage cache in `src/semantic/stage_cache.py`.
  - Semantic signal cache in `src/semantic/signal_cache.py`.
  - Change detection cache in `src/semantic/change_detector.py`.
- No Redis, Memcached, or hosted cache integration is implemented.

## Authentication & Identity

**Auth Provider:**
- None in repository code
  - Implementation: The repository delegates model execution and user identity to the surrounding Claude Code host environment via `src/host_executor.py`; there is no in-repo login, session, OAuth, or token exchange flow.

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Python logging - Used for runtime diagnostics in modules such as `src/commit_semantic/domain_utils.py` and wrapped by `src/semantic/logger.py`.
- CLI/stdout JSON results - Command entry points like `src/main.py` and `src/demand/run.py` print structured JSON summaries to stdout.

## CI/CD & Deployment

**Hosting:**
- GitHub repository plus Claude Code plugin distribution metadata via `.claude-plugin/plugin.json`.
- Local CLI execution via the `semantic-harness` console script declared in `pyproject.toml`.

**CI Pipeline:**
- GitHub Actions in `.github/workflows/ci.yml`
  - Test job installs `.[test]` and runs `pytest tests/test_system.py -q`.
  - Lint job installs Ruff and runs `ruff check src/ tests/`.
  - Typecheck job installs mypy and runs `mypy src/ --ignore-missing-imports || true`.

## Environment Configuration

**Required env vars:**
- Not detected in repository code.
- The project relies on host-provided execution context rather than repo-defined env vars; no `os.getenv(...)`-based configuration was found during this audit.

**Secrets location:**
- No secret files were read.
- If Claude Code or GitHub credentials are required, they are expected to live outside the repository in the host environment or CI runner configuration.

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

---

*Integration audit: 2026-03-24*
