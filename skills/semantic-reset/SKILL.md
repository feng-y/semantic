---
name: semantic-reset
description: >
  Reset the semantic workspace by removing all working artifacts.
  Preserves accepted baseline and schemas.
entrypoint: src.dispatcher._handle_reset
---

# Semantic Reset

Reset the semantic workspace to start fresh.

## What It Does

Removes all working artifacts while preserving:
- Accepted baseline (immutable)
- Schema definitions
- Configuration

## Usage

```
/semantic-reset
```

**Warning:** This removes all discovery and review artifacts. Use with caution.

## What Gets Removed

- `docs/fact/discovery/` - All discovery artifacts
- `docs/fact/review/` - All review artifacts and feedback

## What Gets Preserved

- `docs/fact/baseline/` - Accepted baseline (immutable)
- `docs/fact/schemas/` - Schema definitions

## Implementation

Entrypoint: `src.dispatcher._handle_reset`

This skill provides a clean slate for starting a new discovery cycle.
