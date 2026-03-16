---
name: semantic-init
description: Initialize the semantic harness workspace directory structure
entrypoint: src.dispatcher._handle_init
---

# Semantic Init

Initialize the semantic harness workspace with the following structure:

- `docs/fact/schemas/` — artifact schema definitions
- `docs/fact/discovery/` — versioned working artifacts
- `docs/fact/review/` — review summary, architect feedback
- `docs/fact/baseline/` — accepted baseline (immutable)

## Usage

Run this command first before any semantic operations:

```
/semantic-init
```

## Output

Creates the `docs/fact/` directory structure if it doesn't exist.

## Implementation

Entrypoint: `src.dispatcher._handle_init`

This skill has no steps - it's a simple initialization command that creates the required directory structure for the semantic harness workflow.
