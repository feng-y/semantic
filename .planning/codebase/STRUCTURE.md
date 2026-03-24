# Directory Structure

**Analysis Date:** 2026-03-24

## Root Layout

```
semantic-harness/
├── .claude-plugin/          # Claude Code plugin metadata
├── .github/workflows/       # CI configuration
├── .planning/               # Planning artifacts (this codebase map)
├── data/                    # Runtime outputs (gitignored)
├── docs/                    # Documentation and generated artifacts
├── prompts/                 # LLM prompt templates
├── skills/                  # Claude Code skill definitions
├── src/                     # Python runtime implementation
├── tests/                   # Test suite
├── CLAUDE.md               # Project instructions for agents
├── README.md               # Project documentation
├── pyproject.toml          # Package configuration
└── TODOS.md                # Active work tracking
```

## Key Directories

### `src/` — Runtime Implementation

```
src/
├── main.py                  # CLI entry point
├── dispatcher.py            # Command routing
├── discovery_executor.py    # FACT discovery pipeline
├── refine_executor.py       # Artifact refinement pipeline
├── skill_runner.py          # Base class for staged skills
├── skill_loader.py          # Skill definition parsing
├── context_builder.py       # Prompt context assembly
├── artifact_writer.py       # Versioned artifact I/O
├── artifact_validation.py   # Structural validation
├── prompt_loader.py         # Prompt resolution
├── state_inspector.py       # State inspection
├── host_executor.py         # Host LLM protocol
├── harness_state.py         # State dataclasses
├── types.py                 # Shared type definitions
├── io_utils.py              # JSONL/YAML utilities
├── normalize.py             # Text normalization
├── intent_router.py         # Intent parsing
├── demand/                  # Demand pipeline
│   ├── run.py
│   ├── build_demand_card.py
│   ├── map_semantics.py
│   ├── match_development_type.py
│   ├── normalize_issue.py
│   ├── validate_demand_card.py
│   ├── models.py
│   └── stage_registry.py
├── semantic/                # Semantic layer pipeline
│   ├── run.py
│   ├── extract_signals.py
│   ├── build_candidates.py
│   ├── score_recommend.py
│   ├── apply_review.py
│   ├── finalize_assets.py
│   ├── export.py
│   ├── validate.py
│   ├── stage_registry.py
│   ├── models.py
│   ├── runner_models.py
│   ├── review_models.py
│   ├── finalize_models.py
│   ├── status.py
│   ├── signal_cache.py
│   ├── stage_cache.py
│   ├── change_detector.py
│   ├── lsp_extractor.py
│   ├── evidence_check.py
│   ├── auto_accept.py
│   ├── feedback.py
│   └── logger.py
└── commit_semantic/         # Commit-semantic utilities
    ├── git_utils.py
    └── domain_utils.py
```

### `skills/` — Skill Definitions

```
skills/
├── semantic-fact-pipeline/     # Capability 1: FACT discovery
│   └── SKILL.md
├── semantic-pipeline/          # Capability 2: Semantic extraction
│   └── SKILL.md
├── demand-pipeline/            # Capability 3: Demand mapping
│   └── SKILL.md
├── commit-extract/             # Commit history extraction
│   ├── SKILL.md
│   └── run.py
├── commit-semantic/            # Commit-semantic pipeline
│   ├── SKILL.md
│   └── run.py
├── semantic-*/                 # Individual semantic skills
│   └── SKILL.md
└── repo_structure/             # Repo structure skill (optional)
    └── run.py
```

### `prompts/` — LLM Prompts

```
prompts/
└── discover/
    ├── repo-sampling.prompt
    ├── repo-facts.prompt
    ├── domain-candidates.prompt
    ├── repo-understanding.prompt
    ├── knowledge-confidence.prompt
    ├── review-summary.prompt
    └── evidence-extraction.prompt
```

### `docs/` — Documentation & Artifacts

```
docs/
├── fact/                       # FACT pipeline artifacts
│   ├── schemas/                # Schema definitions
│   ├── templates/              # Artifact templates
│   ├── discovery/              # Working discovery outputs (versioned)
│   ├── review/                 # Review outputs and feedback
│   └── baseline/               # Accepted immutable baseline
├── semantic-design/            # Architecture decision records (001–012)
├── demand/                     # Demand pipeline design docs
├── commit-semantic/            # Commit-semantic user guides
└── superpowers/                # Design specs and architecture docs
```

### `data/` — Runtime Outputs (gitignored)

```
data/
├── commit-extract/             # Monthly JSONL commit data
│   └── YYYY-MM.jsonl
├── commit-semantic/            # Domain aggregation outputs
│   ├── domains.json
│   ├── domains-aggregated.jsonl
│   ├── canonical-demands.jsonl
│   └── summary.json
├── semantic_case_inputs/       # Semantic case inputs
└── semantic_cases/             # Semantic case outputs
```

### `tests/` — Test Suite

```
tests/
├── test_*.py                   # General unit tests
├── fake_executors.py           # Test-only stub executors
├── fixtures/                   # Test fixtures
├── semantic/                   # Semantic layer tests
│   ├── test_runner.py
│   ├── test_extract_signals.py
│   ├── test_build_candidates.py
│   ├── test_score_recommend.py
│   └── ...
├── demand/                     # Demand pipeline tests
│   ├── test_map_semantics.py
│   └── test_demand_pipeline_e2e.py
└── e2e/                        # End-to-end tests
    ├── conftest.py
    ├── test_commit_extract.py
    ├── test_commit_semantic.py
    └── test_pipeline_e2e.py
```

## Naming Conventions

### Files
- Python: `snake_case.py`
- Tests: `test_<module>.py`
- Skills: `SKILL.md` in skill directory
- Artifacts: `name.vN.md` (versioned), `name.md` (unversioned/baseline)

### Directories
- Source modules: descriptive, lowercase (e.g., `semantic/`, `demand/`)
- Skills: hyphenated lowercase (e.g., `semantic-fact-pipeline/`)

### Code
- snake_case for functions, variables, modules
- PascalCase for classes
- UPPER_CASE for module-level constants

---

*Structure analysis: 2026-03-24*
