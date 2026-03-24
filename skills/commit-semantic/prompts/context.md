# Synthesize Repo Semantic Priors

You are analyzing a repository to synthesize **repo-local semantic priors** for commit-first semantic extraction.

Return **JSON only**.

## Required output shape

```json
{
  "local_capabilities": ["string"],
  "aliases": [{"alias": "string", "canonical": "string"}],
  "ownership_hints": [{"path_prefix": "string", "capability": "string"}],
  "seed_concepts": ["string"],
  "doc_sources": ["string"],
  "confidence": "high | medium | low"
}
```

## Goal

Infer the smallest useful set of priors that will help later semantic analysis understand commits in this repo.

## Constraints

- Use docs as **prior**, not truth.
- Do not invent capabilities unsupported by the docs or commit preview.
- Prefer fewer, stronger `local_capabilities` over broad noisy lists.
- Aliases should only be added when they clearly refer to the same semantic thing.
- `ownership_hints` should be high-signal and sparse, not exhaustive.
- `seed_concepts` should be meaningful semantic objects, not random filenames.
- Keep the result compact and high-signal.

## Decision guidance

### local_capabilities
Include only repo-local capability surfaces that are explicitly described or strongly implied.

### aliases
Include only durable naming variants, e.g. old name vs new name, internal vs public name.

### ownership_hints
Use only when a path family clearly implies a capability surface. Avoid speculative mappings.

### seed_concepts
Prefer semantic objects / artifacts / entities over modules or actions.

## Output rules

- JSON only
- No markdown fences
- No explanation text outside the JSON
