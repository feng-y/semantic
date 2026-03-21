# Commit-Extract & Commit-Semantic Design

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

Two-phase commit analysis system:
- **commit-extract**: Aggregate raw commits by month
- **commit-semantic**: Cross-commit analysis, scoring, pattern extraction

---

## commit-extract

### Purpose
Keep CC-generated commits organized by time, no semantic analysis.

### Input
- Git commits (CC-generated, multi-day, multi-purpose collections)

### Output
```yaml
# data/commit-extract/2024-03.yaml
metadata:
  month: "2024-03"
  total_commits: 45

commits:
  - commit_id: "abc123"
    timestamp: "2024-03-15T10:30:00"
    author: "yan."
    commit_message: |  # Original CC output
      feat: add parser legacy support

      Changes:
      - Add compatibility layer for old DSL
      - Preserve historical input parsing
    files: [...]
    diff_chunks: [...]
```

### Stages
1. **collect**: Group commits by month, save raw data

### Features
- Incremental update support
- State tracking

---

## commit-semantic

### Purpose
Cross-commit semantic analysis, scoring, canonical demand extraction.

### Input
- data/commit-extract/*.yaml

### Output
```
data/commit-semantic/
├── commit-logs/
│   ├── functional/          # Scored
│   │   ├── high/           # Score >= 8
│   │   ├── medium/         # Score 5-7
│   │   └── low/            # Score < 5
│   └── non-functional/     # Not scored
│       └── all/
├── rules/
│   └── all.yaml            # All rules/invariants, deduplicated
└── patterns/
    └── {module}.yaml       # Aggregated by module
```

### Classification

| Prefix | Category | Score |
|--------|----------|-------|
| `feat:` | functional | ✅ |
| `bugfix:` | functional | ✅ |
| `optimize:` | functional | ✅ |
| `refactor:` | non-functional | ❌ |
| `refactor+bugfix:` | functional | ✅ (semantic priority) |
| `test:` | non-functional | ❌ |
| `config:` | non-functional | ❌ |
| `cleanup:` | non-functional | ❌ |

### Scoring Criteria (Functional Only)
- Clarity: Is commit_log clear and specific?
- Domain: Is module/domain identified?
- Reusability: Can this pattern be reused?

### Stages
1. **split**: Parse commit_message by module
2. **analyze**: LLM scoring (functional only)
3. **aggregate**: Group by module, extract patterns
4. **distill**: Extract canonical demands from high-scored

### Rules Processing
- Extract rules/invariants from all commits
- **All rules preserved** (not scored)
- Deduplication at final stage

---

## Data Flow

```
git commits
    ↓
commit-extract (aggregate by month)
    ↓
data/commit-extract/YYYY-MM.yaml
    ↓
commit-semantic (split → analyze → aggregate → distill)
    ↓
functional/high/        → canonical demands
functional/medium/      → review candidates
functional/low/         → discard
non-functional/all/     → reference only
rules/all.yaml          → engineering constraints
patterns/{module}.yaml  → module patterns
```

---

## Key Decisions

1. commit-extract keeps raw commits, no LLM processing
2. commit-semantic does all semantic analysis
3. Only functional commits scored (feat/bugfix/optimize)
4. Rules/invariants extracted from all commits, all preserved
5. Semantic priority: refactor+bugfix → functional

---

## Incremental Support

Both skills support incremental updates:
- commit-extract: Skip processed commits
- commit-semantic: Merge with existing analysis

---

## Test Strategy

- E2E: Test full pipeline with sample repo
- Unit: Test classification, scoring logic
- Integration: Test incremental updates
