# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**Type safety backlog remains active:**
- Issue: Static typing is configured but not enforced as a quality gate. `pyproject.toml` enables mypy, `.github/workflows/ci.yml` runs `mypy src/ --ignore-missing-imports || true`, and a live run still reports 15 errors across `src/commit_semantic/git_utils.py`, `src/normalize.py`, `src/skill_runner.py`, `src/commit_semantic/domain_utils.py`, `src/demand/build_demand_card.py`, and `src/dispatcher.py`.
- Files: `pyproject.toml`, `.github/workflows/ci.yml`, `src/commit_semantic/git_utils.py`, `src/normalize.py`, `src/skill_runner.py`, `src/commit_semantic/domain_utils.py`, `src/demand/build_demand_card.py`, `src/dispatcher.py`, `tech-debt-tracker.md`
- Impact: Type regressions can ship even when CI is green, especially in orchestration code and pipeline glue where bad state shapes propagate widely.
- Fix approach: Make the current mypy errors actionable first, then remove `|| true` from `.github/workflows/ci.yml` and keep the typecheck lane blocking for `src/`.

**Import-path strategy is brittle and split-brained:**
- Issue: Runtime and tests rely on manual `sys.path.insert(...)` and mixed absolute/import-fallback patterns instead of a single package import model. `src/skill_runner.py` mutates `sys.path`; many tests do the same; multiple semantic modules import both `semantic.*` and `src.semantic.*` depending on execution mode.
- Files: `src/skill_runner.py`, `src/semantic/run.py`, `src/semantic/cache_cli.py`, `src/semantic/build_candidates.py`, `src/semantic/score_recommend.py`, `src/semantic/apply_review.py`, `src/state_inspector.py`, `tests/test_commit_semantic_domain.py`, `tests/e2e/test_commit_semantic.py`, `tests/semantic/test_build_candidates.py`, `tests/semantic/test_export.py`
- Impact: Execution depends on current working directory and import side effects. Packaging, CLI execution, and test isolation are more fragile than necessary.
- Fix approach: Standardize on package-qualified imports from `src`-installed modules, remove `sys.path` mutation, and keep CLI entrypoints thin.

**Large orchestration modules concentrate unrelated responsibilities:**
- Issue: Several files are large enough to mix state management, validation, artifact IO, prompt orchestration, and recovery logic in single modules.
- Files: `src/refine_executor.py`, `src/discovery_executor.py`, `src/semantic/score_recommend.py`, `src/semantic/extract_signals.py`, `src/commit_semantic/domain_utils.py`, `src/artifact_writer.py`, `src/context_builder.py`, `src/semantic/signal_cache.py`
- Impact: Local changes have broad blast radius, targeted unit testing gets harder, and contributors must reload large mental context before making safe edits.
- Fix approach: Split executors into smaller service modules around prompt execution, validation, artifact persistence, and state transitions. Keep each stage module focused on one responsibility.

**Demand pipeline interface lags current commit-semantic design:**
- Issue: repo TODOs explicitly record that demand must adapt to new `commit-semantic` outputs such as `domains-aggregated.jsonl` and `canonical-demands.jsonl`, but `load_semantic_foundation_assets()` still only loads foundation maps.
- Files: `TODOS.md`, `src/demand/run.py`, `src/demand/map_semantics.py`, `src/demand/build_demand_card.py`
- Impact: The documented downstream integration point is incomplete, so commit-history semantic output cannot yet flow cleanly into demand generation.
- Fix approach: Define the exact downstream contract, load the new artifacts explicitly in `src/demand/map_semantics.py`, and add integration coverage for the new path.

## Known Bugs

**Typecheck reports concrete defects today:**
- Symptoms: `mypy src/` fails with real issues such as implicit `Optional` misuse in `src/commit_semantic/git_utils.py`, invalid `callable` typing in `src/skill_runner.py`, wrong argument types in `src/demand/build_demand_card.py`, and assignment mismatch in `src/dispatcher.py`.
- Files: `src/commit_semantic/git_utils.py`, `src/skill_runner.py`, `src/demand/build_demand_card.py`, `src/dispatcher.py`, `src/normalize.py`, `src/commit_semantic/domain_utils.py`
- Trigger: Run `python3 -m mypy src` from the project root.
- Workaround: None in code. CI tolerates the failure because `.github/workflows/ci.yml` explicitly allows mypy to fail.

**Demand pipeline does not yet consume new domain aggregation outputs:**
- Symptoms: The demand stage loads semantic foundation maps, but repo TODOs state that downstream support for `domains-aggregated.jsonl` and `canonical-demands.jsonl` is still pending.
- Files: `TODOS.md`, `src/demand/run.py`, `src/demand/map_semantics.py`
- Trigger: Attempt to use demand generation as a downstream consumer of the rewritten `commit-semantic` domain aggregation flow.
- Workaround: Use the existing foundation-map inputs only; the new commit-semantic outputs are not wired in yet.

## Security Considerations

**Prompt context file loading permits path traversal outside intended repo scope:**
- Risk: `read_selected_files()` trusts file paths parsed from the sampling report and resolves them with `root / rel_path` without checking that the resolved path stays under the repository root.
- Files: `src/context_builder.py`
- Current mitigation: Missing files and unreadable files are handled defensively, and content per file is truncated to 10,000 characters.
- Recommendations: Resolve with `Path.resolve()`, reject any path whose resolved location is outside `root.resolve()`, and only allow files returned by repo inventory such as `git ls-files`.

**Validation bypass exists in runtime CLI:**
- Risk: The semantic runner exposes `--skip-validation`, which bypasses post-stage validation intended to guard artifact quality.
- Files: `src/semantic/run.py`, `tests/semantic/test_runner_validate.py`
- Current mitigation: The flag is labeled “for debugging,” and default execution keeps validation on.
- Recommendations: Restrict this flag to local debugging, make production/CI paths reject it, or emit explicit warnings and mark produced artifacts as tainted.

**Silent exception swallowing hides failure modes:**
- Risk: Several paths catch broad exceptions and either return fallback values or suppress the error entirely. Examples include LLM intent fallback, runner-state inspection, and cache handling.
- Files: `src/intent_router.py`, `src/state_inspector.py`, `src/discovery_executor.py`, `src/demand/run.py`, `src/semantic/signal_cache.py`
- Current mitigation: Most call sites degrade gracefully instead of crashing.
- Recommendations: Narrow exception classes, log degraded behavior explicitly, and preserve enough error context for debugging and auditability.

## Performance Bottlenecks

**Commit detail extraction loads full diffs into memory per commit:**
- Problem: `get_commit_details()` shells out multiple times per commit and reads the full `git show` output before splitting it into chunks.
- Files: `src/commit_semantic/git_utils.py`
- Cause: Per-commit subprocess calls plus full diff materialization create avoidable overhead on large histories or large commits.
- Improvement path: Batch metadata where possible, add size guards, and stream or limit diff extraction for oversized commits.

**Prompt context assembly has incomplete scaling controls:**
- Problem: `build_repo_tree_summary()` truncates repo file listing to 200 files, while `read_selected_files()` reads every selected file with only a per-file cap and no overall token/byte budget.
- Files: `src/context_builder.py`
- Cause: Fixed caps are simple, but they do not adapt to large repositories or unusually large selected-file sets.
- Improvement path: Add total-budget accounting, prioritize files by relevance, and expose truncation metadata so downstream stages know context was partial.

## Fragile Areas

**Discovery/refine artifact pipeline:**
- Files: `src/discovery_executor.py`, `src/refine_executor.py`, `src/artifact_writer.py`, `src/artifact_validation.py`, `src/context_builder.py`
- Why fragile: Multi-step orchestration spans prompt loading, executor calls, validation, version allocation, pruning, and baseline checkpoints. A small contract change can break several stages at once.
- Safe modification: Change one stage at a time, preserve artifact naming/versioning contracts, and re-run artifact/versioning tests after any edit.
- Test coverage: There is good unit coverage around versioning and validation, but end-to-end coverage still depends on mocked or deterministic executors rather than real host behavior.

**Commit-semantic discover/classify path:**
- Files: `skills/commit-semantic/run.py`, `src/commit_semantic/domain_utils.py`, `tests/e2e/test_commit_semantic.py`, `tests/test_commit_semantic_domain.py`
- Why fragile: The repo explicitly notes that discover requires an LLM and most end-to-end tests skip it. The non-LLM stages are covered, but the real model-driven branch is not exercised in normal CI.
- Safe modification: Preserve JSON contracts for domain discovery/classification, keep deterministic fallbacks stable, and add fixture-backed golden outputs before changing prompts or parsing.
- Test coverage: `tests/e2e/test_commit_semantic.py` covers ingest→export well, but it skips discover; real discover/classify integration remains a gap.

**State handling depends on current working directory:**
- Files: `src/harness_state.py`, `src/skill_runner.py`
- Why fragile: `get_harness_root()` always returns relative `.harness`, and CLI helpers rely on ambient cwd plus import-path mutation.
- Safe modification: Convert state roots to absolute repo-based paths early and thread them explicitly through runners.
- Test coverage: There is coverage for state utilities, but cwd-sensitive behavior can still vary across invocation environments.

## Scaling Limits

**Repo-scale context generation is bounded but lossy:**
- Current capacity: `build_repo_tree_summary()` includes at most 200 tracked files; `read_selected_files()` truncates individual file content at 10,000 characters.
- Limit: Large repositories will receive partial context, and the selection is based on order rather than an explicit relevance ranking.
- Scaling path: Introduce deterministic prioritization, overall prompt budgets, and structured summaries instead of raw concatenation.

**Versioned artifact history is intentionally shallow:**
- Current capacity: `DEFAULT_VERSION_WINDOW = 3` retains only the latest three working versions per artifact family unless protected by accepted baseline metadata.
- Limit: Short retention reduces disk growth but also narrows local debugging history for discovery/refine regressions.
- Scaling path: Make retention configurable per artifact type and preserve additional history for high-churn stages in development environments.

## Dependencies at Risk

**mypy is present but operationally optional:**
- Risk: The dependency exists, but the project treats failures as informational only.
- Impact: The repo carries a false sense of typed safety while shipping known type defects in core paths.
- Migration plan: Fix the current error set, then enforce mypy in CI for `src/` and document any intentional exclusions.

## Missing Critical Features

**No verified downstream contract from commit-semantic to demand:**
- Problem: The repo documents demand as a downstream consumer, but the new aggregated outputs are not yet integrated.
- Blocks: End-to-end commit → semantic → demand workflows remain incomplete.

**Auditability and correction loop are still pending:**
- Problem: The TODO list explicitly calls out missing traceability to original diff/file/hunk evidence, confidence markers for inferred rules, and reviewer correction loops.
- Blocks: Repo-level trust, explainability, and safe iterative improvement of commit-semantic outputs.
- Files: `TODOS.md`, `src/commit_semantic/domain_utils.py`, `skills/commit-semantic/run.py`

## Test Coverage Gaps

**CI only runs one test file in the main test job:**
- What's not tested: The default `test` job in CI runs only `tests/test_system.py`, while the repo contains a much larger suite across `tests/semantic/`, `tests/demand/`, and `tests/e2e/`.
- Files: `.github/workflows/ci.yml`, `tests/test_system.py`, `tests/e2e/test_commit_semantic.py`, `tests/demand/test_demand_pipeline_e2e.py`
- Risk: Regressions outside the single selected test file can merge undetected unless manually run.
- Priority: High

**Real LLM-driven discover path is not part of automated regression coverage:**
- What's not tested: `tests/e2e/test_commit_semantic.py` states that discover requires an LLM and therefore most tests skip it, covering ingest→export instead.
- Files: `tests/e2e/test_commit_semantic.py`, `skills/commit-semantic/run.py`
- Risk: Prompt/schema drift or parser regressions in the discover stage can go unnoticed until manual runs.
- Priority: High

**Many semantic tests skip when fixture artifacts are absent:**
- What's not tested: Multiple tests in `tests/semantic/` skip if files such as `signals.yaml`, `candidates.yaml`, or `recommendations.yaml` are missing.
- Files: `tests/semantic/test_build_candidates.py`, `tests/semantic/test_extract_signals.py`, `tests/semantic/test_apply_review.py`, `tests/semantic/test_score_recommend.py`, `tests/semantic/test_evidence_check.py`
- Risk: Local confidence can vary by environment, and skipped tests may mask broken fixture expectations.
- Priority: Medium

---

*Concerns audit: 2026-03-24*
