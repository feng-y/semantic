---
name: semantic-extract
description: Extract semantic information from git commits - both commit_log and rules/invariants
---

# semantic-extract

Extract semantic information from git history with two views:
- **commit view**: functional semantics (what the change does)
- **rules view**: engineering constraints (what must not be broken)

## Usage

/semantic-extract --last 10 --view both
/semantic-extract --last 5 --view rules
/semantic-extract --since 2026-01-01 --view commit

## Parameters

- `--last N`: Process last N commits
- `--since YYYY-MM-DD`: Process commits since date
- `--until YYYY-MM-DD`: Process commits until date
- `--range SHA1..SHA2`: Process commit range
- `--view both|commit|rules`: Which view to extract (default: both)
- `--dry-run`: Preview without writing
- `--incremental`: Skip already processed commits
