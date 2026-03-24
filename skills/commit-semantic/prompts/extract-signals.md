# Extract Commit-Level Semantic Signals

You are performing **commit-first semantic analysis** over structured `commit-extract` records.

**Return JSON only. No markdown fences. No explanation text outside the JSON.**

---

## Task

For each commit record, extract semantic signals about **what operation was performed and what it means**. These signals feed into downstream capability synthesis.

**You are not classifying commits into buckets.** You are extracting signals that can be aggregated across commits.

---

## What to extract

### capability
A stable functional unit this commit builds, refines, hardens, or evolves. The signal comes from the *operation* (what was added/removed/changed), not from the file that was modified.

### concept
A semantic object, artifact, or entity being manipulated.

### rule
A constraint, invariant, or judgment logic being enforced or clarified.

### domain_hint
A weak clue about problem space. Not a final domain.

---

## Output schema

```json
{
  "signals": [
    {
      "kind": "capability | concept | rule | domain_hint",
      "name": "string",
      "description": "string",
      "source_commit": "string",
      "evidence_refs": ["string"],
      "confidence": "high | medium | low",
      "flags": ["string"],
      "related_capability_names": ["string"]
    }
  ]
}
```

Evidence refs: `sha:<commit>`, `summary:<commit>:<section>:<item>`, `rule:<commit>:<index>`

---

## Signal strength rules (hard constraints)

**Ask first: "What operation was performed and what does it mean?"**

### Emit as primary signal only when:
- The commit performs a **process operation** with clear intent: feat, fix, bugfix, optimize, refactor with concrete semantic content
- The operation's intent and logic are the semantic content — what capability was added, removed, or changed
- The change is about logic/behavior, not about the container of that logic

### Do NOT emit as primary signal when:
- The commit is **config-only** (`.yaml`, `.json`, `.toml`, `.ini`, env vars): the operation is "set a value" — only the resulting state carries semantic weight, and only if that state has independent meaning
- The commit is **doc-only**: the operation is "write docs" — writing docs is the work itself, not a side-effect of meaningful work
- The commit is **low-signal boilerplate**: "Modified N file(s)", "Changes in:", generic wording with no concrete semantic object

### Down-rank rules:
- Config change with clear final-state semantics (e.g., "security rule now enforces X", "feature Y disabled") → `confidence: medium` or `low`
- Config change with no stated intent or consequence → do not emit as capability signal
- Docs-only → `confidence: low` unless it clarifies a significant semantic distinction
- Low-signal overall → emit at most weak/low-confidence signals, do not invent strong capabilities

---

## Per-commit extraction strategy

For each commit, first identify the **primary capability/change vector** if one exists. Then:

1. Anchor on the semantic center — this becomes the primary signal
2. Treat remaining edits as supporting evidence or secondary signals
3. Do NOT flatten everything into many equally-weighted fragments

For mixed commits (multiple semantic concerns):
- Record the dominant signal
- Add `"mixed"` to `flags`
- Use `related_capability_names` to preserve secondary concerns

For commits with both high-information and low-signal content:
- Anchor on the high-information item
- Treat the low-signal item only as weak supporting evidence

---

## Noise suppression (hard constraints — do NOT treat as primary signal)

- `.claude/*`, `.planning/*`, agent metadata, generated workflow scaffolding
- generated files
- broad formatting / cleanup / review-note churn
- test-only support changes

These may remain as supporting evidence but must not become the dominant capability signal.

---

## Observability and runtime-control

Do NOT treat as mere plumbing by default. If observability, metrics, runtime controls, scheduling, or operator-facing behavior materially changes how operators control, observe, or reason about the runtime → emit as capability signal.

---

## Confidence calibration

| Situation | Confidence |
|-----------|-----------|
| Concrete process operation with clear intent | `high` |
| Config change with clear final-state semantics | `medium` or `low` |
| Config change with no stated intent | do not emit as capability |
| Low-signal overall, no clear operation | `low` or skip |
| Doc-only | `low` unless it clarifies significant semantics |

---

## Few-shot examples

### Example 1: Strong process operation → emit capability

**Input:**
```json
{
  "sha": "abc123",
  "sections": [
    {
      "name": "Auth",
      "theme": "auth",
      "importance": "primary",
      "items": [
        {"op": "feat", "summary": "Add login with OAuth2 and session management"}
      ]
    }
  ]
}
```

**Output:**
```json
{
  "signals": [
    {
      "kind": "capability",
      "name": "oauth2-login",
      "description": "Add OAuth2 login with session management",
      "source_commit": "abc123",
      "evidence_refs": ["sha:abc123", "summary:abc123:0:0"],
      "confidence": "high",
      "flags": [],
      "related_capability_names": []
    }
  ]
}
```

### Example 2: Config-only → low confidence or skip

**Input:**
```json
{
  "sha": "def456",
  "sections": [
    {
      "name": "Config",
      "theme": "config",
      "importance": "primary",
      "items": [
        {"op": "chore", "summary": "Set timeout to 30s"}
      ]
    }
  ]
}
```

**Output:**
```json
{
  "signals": []
}
```

### Example 3: Config with clear final-state semantics → medium

**Input:**
```json
{
  "sha": "ghi789",
  "sections": [
    {
      "name": "Security",
      "theme": "security",
      "importance": "primary",
      "items": [
        {"op": "fix", "summary": "Require API key for all endpoints — removed allowlist bypass"}
      ]
    }
  ]
}
```

**Output:**
```json
{
  "signals": [
    {
      "kind": "capability",
      "name": "api-key-auth-required",
      "description": "All API endpoints now require API key authentication; bypass removed",
      "source_commit": "ghi789",
      "evidence_refs": ["sha:ghi789", "summary:ghi789:0:0"],
      "confidence": "medium",
      "flags": [],
      "related_capability_names": []
    }
  ]
}
```

### Example 4: Doc-only → low

**Input:**
```json
{
  "sha": "doc001",
  "sections": [
    {
      "name": "Docs",
      "theme": "docs",
      "importance": "primary",
      "items": [
        {"op": "docs", "summary": "Update README with new installation steps"}
      ]
    }
  ]
}
```

**Output:**
```json
{
  "signals": [
    {
      "kind": "concept",
      "name": "installation-documentation",
      "description": "Installation steps documented",
      "source_commit": "doc001",
      "evidence_refs": ["summary:doc001:0:0"],
      "confidence": "low",
      "flags": ["docs-only"],
      "related_capability_names": []
    }
  ]
}
```

### Example 5: Mixed — primary + secondary

**Input:**
```json
{
  "sha": "mix001",
  "is_mixed": true,
  "sections": [
    {
      "name": "Auth",
      "theme": "auth",
      "importance": "primary",
      "items": [
        {"op": "feat", "summary": "Add login"}
      ]
    },
    {
      "name": "Tests",
      "theme": "test",
      "importance": "secondary",
      "items": [
        {"op": "test", "summary": "Add login tests"}
      ]
    }
  ]
}
```

**Output:**
```json
{
  "signals": [
    {
      "kind": "capability",
      "name": "login",
      "description": "Add login capability",
      "source_commit": "mix001",
      "evidence_refs": ["sha:mix001", "summary:mix001:0:0"],
      "confidence": "high",
      "flags": ["mixed"],
      "related_capability_names": ["login-tests"]
    },
    {
      "kind": "concept",
      "name": "login-tests",
      "description": "Login test coverage",
      "source_commit": "mix001",
      "evidence_refs": ["summary:mix001:1:0"],
      "confidence": "medium",
      "flags": ["test-only"],
      "related_capability_names": []
    }
  ]
}
```
