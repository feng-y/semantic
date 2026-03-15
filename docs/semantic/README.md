# docs/semantic/

This directory contains **generated semantic state**, not human-written documentation.

## Subdirectories

| Directory | Contents | Written by |
|-----------|----------|------------|
| `discovery/` | Versioned working artifacts (repo-facts, repo-understanding, knowledge-confidence, domain-candidates, sampling-report) | Discovery pipeline (`src/discovery_executor.py`) |
| `review/` | Review summary, architect feedback, semantic change log | Review/refine pipeline (`src/refine_executor.py`) |
| `baseline/` | Accepted baseline artifacts (purpose, domains, concepts, pipelines) + checkpoint | Baseline synthesis (`src/refine_executor.py`) |
| `schemas/` | Structural contracts that artifacts must satisfy | Human-authored (stable) |

## Key distinction

- `docs/semantic/` = machine-generated state (discovery, review, baseline) + contracts (schemas)
- `docs/semantic-design/` = human-written architecture decision records
- `docs/review/` = development reports, audits, migration artifacts
