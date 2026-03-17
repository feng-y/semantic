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
    validate: repo-facts
  - run: prompts/discover/domain-candidates.prompt
  - run: prompts/discover/repo-understanding.prompt
  - run: prompts/validation/validate-artifact.prompt
    validate: repo-understanding
  - run: prompts/discover/knowledge-confidence.prompt
  - run: prompts/discover/review-summary.prompt
  - apply: protocols/artifact-versioning.md
---

# Semantic Discover

Run the full semantic discovery pipeline to extract repository understanding.

## Pipeline Steps

1. **Repository Sampling** - Sample codebase structure
2. **Fact Extraction** - Extract facts with evidence
3. **Evidence Augmentation** - Enhance facts with context
4. **Validation** - Validate extracted artifacts
5. **Domain Analysis** - Identify domain candidates
6. **Repository Understanding** - Build conceptual model
7. **Validation** - Validate understanding artifacts
8. **Knowledge Confidence** - Assess understanding quality
9. **Review Summary** - Generate review report
10. **Versioning** - Apply artifact versioning protocol

## Usage

```
/semantic-discover
```

## Output

Creates versioned artifacts in `docs/fact/discovery/`:
- `repo-facts.vN.md`
- `domain-candidates.vN.md`
- `repo-understanding.vN.md`
- `knowledge-confidence.vN.md`
- `review/review-summary.vN.md`

## Implementation

Entrypoint: `src.discovery_executor.run_discovery`

The pipeline executes each step sequentially, with validation checkpoints after artifact generation.
