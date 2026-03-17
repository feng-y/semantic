# User Guide

## Workflow Overview

Semantic Harness follows a four-phase workflow:

```
init → discover → review → refine → baseline
```

Each phase produces versioned artifacts in `docs/fact/`. The architect (you) controls convergence through feedback and acceptance.

## Initialize

Run `init` to create the workspace:

```
docs/fact/
  schemas/       — artifact schema definitions
  discovery/     — versioned working artifacts
  review/        — review summary, architect feedback
  baseline/      — accepted baseline (immutable)
```

> **Important:** These directories contain generated semantic state, not human-written documentation. The pipeline writes artifacts here at runtime. `schemas/` defines the structural contracts each artifact must satisfy. Human-written design docs are in `docs/semantic-design/`.

## Run Discovery

Discovery extracts semantic understanding from your repository:

1. Samples the repository structure
2. Extracts repo facts with evidence
3. Identifies domain candidates
4. Builds repo understanding (purpose, pipelines, concepts)
5. Assesses knowledge confidence
6. Generates review summary

Output artifacts (versioned):
- `discovery/repo-facts.vN.md`
- `discovery/domain-candidates.vN.md`
- `discovery/repo-understanding.vN.md`
- `discovery/knowledge-confidence.vN.md`
- `review/review-summary.vN.md`

## Review and Refine

After discovery, review the outputs and write feedback:

1. Read `review/review-summary.vN.md`
2. Edit `review/architect-feedback.md` with corrections, missing concepts, clarifications
3. Run `refine` — patches artifacts using your feedback
4. Review the updated artifacts and `review/semantic-change-log.md`
5. Repeat until satisfied

## Acceptance and Baseline

When artifacts are ready, add to `architect-feedback.md`:

```
acceptance: true
```

Run `refine` again. The system will:
1. Verify 4 structural gates (acceptance field, knowledge-confidence sections, repo-understanding sections, domain-candidates non-empty)
2. Synthesize baseline artifacts: `purpose.md`, `domains.md`, `concepts.md`, `pipelines.md`
3. Write `baseline/checkpoint.json` with source version traceability

Baseline artifacts are immutable and never auto-pruned.

## Artifact Locations

| Artifact | Location |
|----------|----------|
| Sampling report | `discovery/sampling-report.md` |
| Repo facts | `discovery/repo-facts.vN.md` |
| Domain candidates | `discovery/domain-candidates.vN.md` |
| Repo understanding | `discovery/repo-understanding.vN.md` |
| Knowledge confidence | `discovery/knowledge-confidence.vN.md` |
| Review summary | `review/review-summary.vN.md` |
| Architect feedback | `review/architect-feedback.md` |
| Change log | `review/semantic-change-log.md` |
| Baseline | `baseline/{purpose,domains,concepts,pipelines}.md` |
| Checkpoint | `baseline/checkpoint.json` |

All paths are relative to `docs/fact/`.

## Failure Handling

The system halts safely on errors:

- **Validation failure**: artifact missing required schema sections → pipeline stops, prior valid artifacts preserved
- **Version skew**: cross-artifact version inconsistency detected → pipeline halts before any writes
- **Executor failure**: malformed output → staged writes prevent partial state, nothing committed
- **Baseline failure**: incomplete synthesis output → baseline not written, working state intact

After any failure, fix the issue and rerun. The system recovers from the last valid state.

## Best Practices

- Review artifacts after each discovery/refine cycle
- Write specific, actionable feedback in `architect-feedback.md`
- Only add `acceptance: true` when you're confident in the semantic model
- Keep feedback focused on corrections and missing knowledge, not style
- Check `semantic-change-log.md` to track what changed between refine cycles
