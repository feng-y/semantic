# Shared Bootstrap Context Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and land the layered `repo-context.json` contract for the shared bootstrap migration so both `commit-extract` and `commit-semantic` can implement against one stable schema.

**Architecture:** This subproject is schema-first and behavior-light. It does not move producer ownership yet. It only defines the shared context artifact shape, updates the current `commit-semantic` context stage to emit the new layered contract in a backward-compatible way, and locks the contract with tests, fixtures, and docs.

**Tech Stack:** Python 3.10+, pytest, JSON artifact IO, existing `SkillRunner` / `HostExecutor` patterns.

---

## Naming Resolution

For this subproject, the canonical shared contract artifact name is:
- `repo-context.json`

Compatibility artifact:
- `repo-hints.json` remains emitted in this subproject with its current flat shape
- It is compatibility-only and **not** the canonical contract target for new producer/consumer work

This resolves the CEO-plan ambiguity: `repo-context.json` is the long-term shared context file, while `repo-hints.json` survives temporarily so current paths do not break during migration.

---

## File Structure

### Files to modify
- `skills/commit-semantic/run.py`
  - Keep current context stage orchestration.
  - Change emitted `repo-context.json` shape to the new layered contract.
  - Preserve current downstream behavior through `semantic_context`.
  - Continue emitting backward-compatible `repo-hints.json` in this subproject.
- `skills/commit-semantic/SKILL.md`
  - Update stage documentation and output schema to describe the layered `repo-context.json` contract.
  - Explicitly state that producer ownership has **not** migrated yet.
- `tests/e2e/test_commit_semantic.py`
  - Update context-stage assertions to the new artifact contract.

### Files to create
- `tests/test_shared_repo_context_contract.py`
  - Focused contract tests for the new `repo-context.json` schema.
- `tests/fixtures/shared_repo_context/example_repo_context.json`
  - Normative golden example of the layered artifact used by contract tests.

### Files to inspect while implementing
- `docs/superpowers/specs/2026-03-24-commit-semantic-general-semantic-asset-extraction-design.md`
  - Source of truth for docs-as-prior, minimal hints, and failure-mode constraints.
- `tests/e2e/test_commit_extract.py`
  - Confirm no assumptions about the new contract leak into extract tests yet.
- `TODOS.md`
  - Keep TODO-2 in mind; do not accidentally expand this subproject into auditability or correction-loop work.

### Contract boundary for this subproject
This plan intentionally does **not** implement:
- `commit-extract` bootstrap producer ownership
- freshness / staleness checks
- adaptive fallback / bypass
- health summary behavior guarantees beyond schema placeholders
- prompt injection changes
- eval fixtures

Those belong to later subprojects.

---

## Normative Contract

### Canonical artifact: `repo-context.json`

```json
{
  "shared_hints": {
    "local_capabilities": [],
    "aliases": [],
    "ownership_hints": [],
    "seed_concepts": [],
    "source_provenance": {},
    "hint_confidence": {},
    "conflicts": [],
    "source_snapshot": {
      "docs": [],
      "codebase_map": []
    }
  },
  "semantic_context": {
    "local_capabilities": [],
    "ownership_hints": [],
    "aliases": [],
    "seed_concepts": [],
    "confidence": "medium"
  },
  "summary": {
    "bootstrap_status": "full",
    "hint_count": 0,
    "source_counts": {
      "docs": 0,
      "codebase_map": 0
    }
  }
}
```

### Field-by-field contract

#### Top-level

| Field | Type | Required | Empty allowed | Semantics |
|-------|------|----------|---------------|-----------|
| `shared_hints` | object | yes | no | Compact reusable context layer |
| `semantic_context` | object | yes | no | `commit-semantic`-local interpreted view |
| `summary` | object | yes | no | Minimal schema anchor for health/status |

#### `shared_hints`

| Field | Type | Required | Empty allowed | Semantics |
|-------|------|----------|---------------|-----------|
| `local_capabilities` | list[str] | yes | yes | Repo-local stable capability labels |
| `aliases` | list[object] | yes | yes | Alias relationships between terms |
| `ownership_hints` | list[object] | yes | yes | Subsystem / ownership / boundary hints |
| `seed_concepts` | list[object] | yes | yes | High-value concept seeds |
| `source_provenance` | dict[str, list[str]] | yes | yes | Field-level or item-level source attribution |
| `hint_confidence` | dict[str, str] | yes | yes | Confidence map keyed by stable hint key |
| `conflicts` | list[object] | yes | yes | Detected contradictions between sources |
| `source_snapshot` | object | yes | no | Raw source file lists used to build context |

#### `aliases` item shape

```json
{
  "canonical": "commit-extract",
  "alias": "extract",
  "kind": "term"
}
```

Rules:
- `canonical`: required, non-empty string
- `alias`: required, non-empty string
- `kind`: required, string enum for this subproject: `term|subsystem|concept`

#### `ownership_hints` item shape

```json
{
  "scope": "commit-extract",
  "owner": "extract pipeline",
  "note": "Produces structured commit records"
}
```

Rules:
- `scope`: required, non-empty string
- `owner`: required, non-empty string
- `note`: required, non-empty string

#### `seed_concepts` item shape

```json
{
  "name": "repo context",
  "description": "Shared context prior used by semantic pipelines"
}
```

Rules:
- `name`: required, non-empty string
- `description`: required, non-empty string

#### `source_provenance`

Example:

```json
{
  "local_capabilities.commit-extract": ["docs:README.md", "codebase_map:ARCHITECTURE.md"],
  "aliases.commit-extract.extract": ["docs:CLAUDE.md"]
}
```

Rules:
- keys are stable hint keys encoded as strings
- values are lists of source identifiers
- empty object allowed in this subproject

#### `hint_confidence`

Example:

```json
{
  "local_capabilities.commit-extract": "high",
  "aliases.commit-extract.extract": "medium"
}
```

Rules:
- keys are stable hint keys encoded as strings
- values must be `high`, `medium`, or `low`
- empty object allowed in this subproject

#### `conflicts` item shape

```json
{
  "field": "ownership_hints.commit-extract",
  "sources": ["docs:ARCHITECTURE.md", "codebase_map:ARCHITECTURE.md"],
  "reason": "Conflicting owner descriptions"
}
```

Rules:
- `field`: required, non-empty string
- `sources`: required, non-empty list[str]
- `reason`: required, non-empty string

#### `source_snapshot`

| Field | Type | Required | Empty allowed | Semantics |
|-------|------|----------|---------------|-----------|
| `docs` | list[str] | yes | yes | Source doc file paths used |
| `codebase_map` | list[str] | yes | yes | `.planning/codebase/*` files used |

#### `semantic_context`

| Field | Type | Required | Empty allowed | Semantics |
|-------|------|----------|---------------|-----------|
| `local_capabilities` | list[str] | yes | yes | Current flat capabilities list for downstream semantic use |
| `ownership_hints` | list[object] | yes | yes | Current semantic-local ownership hints |
| `aliases` | list[object] | yes | yes | Current semantic-local alias view |
| `seed_concepts` | list[object] | yes | yes | Current semantic-local concept view |
| `confidence` | str | yes | no | One of `high|medium|low` |

#### `summary`

| Field | Type | Required | Empty allowed | Semantics |
|-------|------|----------|---------------|-----------|
| `bootstrap_status` | str | yes | no | Schema placeholder only in this subproject; one of `full|degraded|bypass` |
| `hint_count` | int | yes | no | Count of all shared hint entries |
| `source_counts` | object | yes | no | Count of source files by source class |

### Counting rules
- `hint_count` = `len(local_capabilities) + len(aliases) + len(ownership_hints) + len(seed_concepts)` inside `shared_hints`
- `source_counts.docs` = `len(source_snapshot.docs)`
- `source_counts.codebase_map` = `len(source_snapshot.codebase_map)`

### Provisional summary rule
In this subproject, `summary` fields are **schema anchors, not operational guarantees**.
That means:
- `bootstrap_status` must exist and be valid
- but no reliability-layer semantics are implied yet

### Stable key grammar
- `local_capabilities.<capability>`
- `aliases.<canonical>.<alias>`
- `ownership_hints.<scope>`
- `seed_concepts.<name>`

`source_provenance` and `hint_confidence` must use these exact key formats in this subproject.

---

## Backward Compatibility Rule

In this subproject:
- `repo-hints.json` **must continue to be emitted** with its current flat shape
- `repo-context.json` becomes the canonical layered contract artifact
- downstream compatibility is preserved through a single compatibility accessor path

### Compatibility scope for `repo-hints.json`
`repo-hints.json` compatibility in this subproject means:
- file still emitted
- same top-level keys as before
- same value types for the existing keys
- representative semantic values still present for current context-stage fixtures

Do **not** require byte-for-byte snapshot identity in this subproject.

### Compatibility accessor rule
All downstream semantic consumers touched in this subproject must read from:

```python
repo_context.get("semantic_context", repo_context)
```

Do not introduce multiple ad hoc readers of layered internals in this subproject.
If more than one downstream consumer expects the old flat shape, route them all through the same accessor behavior.

---

## Task 1: Write the contract tests first

**Files:**
- Create: `tests/test_shared_repo_context_contract.py`
- Create: `tests/fixtures/shared_repo_context/example_repo_context.json`

- [ ] **Step 1: Create the normative golden artifact**

Write `tests/fixtures/shared_repo_context/example_repo_context.json` with the exact layered structure expected by the new contract.

Include:
- at least 2 `local_capabilities`
- at least 1 alias object
- at least 1 ownership hint object
- at least 1 seed concept object
- non-empty `source_snapshot.docs` and `source_snapshot.codebase_map`
- empty-but-present `conflicts`
- `summary.bootstrap_status = "full"`
- `summary.hint_count` matching the counting rule above
- `summary.source_counts` matching the snapshot counts

- [ ] **Step 2: Write the failing contract test for top-level structure**

In `tests/test_shared_repo_context_contract.py`, write a test like:

```python
import json
from pathlib import Path


def load_fixture():
    fixture = Path("tests/fixtures/shared_repo_context/example_repo_context.json")
    return json.loads(fixture.read_text())


def test_repo_context_contract_has_layered_top_level_keys():
    data = load_fixture()
    assert set(data.keys()) == {"shared_hints", "semantic_context", "summary"}
```

- [ ] **Step 3: Write failing tests for required subkeys and nested item shapes**

Add tests asserting:
- `shared_hints` contains all required keys
- `semantic_context` contains all required keys
- `summary` contains all required keys
- every alias has `canonical`, `alias`, `kind`
- every ownership hint has `scope`, `owner`, `note`
- every seed concept has `name`, `description`
- every conflict has `field`, `sources`, `reason`

- [ ] **Step 4: Write failing tests for enum values and counting semantics**

Add tests asserting:
- `semantic_context["confidence"]` is one of `high|medium|low`
- `summary["bootstrap_status"]` is one of `full|degraded|bypass`
- `summary["hint_count"]` matches the defined counting rule
- `summary["source_counts"]` matches `source_snapshot`

- [ ] **Step 5: Run the contract tests**

Run:
```bash
pytest tests/test_shared_repo_context_contract.py -v
```

Expected: PASS. This validates the schema fixture and contract expectations only; it does **not** validate runtime emission yet.

- [ ] **Step 6: Optional checkpoint commit**

```bash
git add tests/test_shared_repo_context_contract.py tests/fixtures/shared_repo_context/example_repo_context.json
git commit -m "test: add shared repo context contract fixtures"
```

---

## Task 2: Update `commit-semantic` context stage to emit the layered contract

**Files:**
- Modify: `skills/commit-semantic/run.py`
- Test: `tests/e2e/test_commit_semantic.py`

- [ ] **Step 1: Read the current context-stage implementation carefully**

Focus on:
- `_run_context()` in `skills/commit-semantic/run.py`
- `_load_repo_context()` and downstream use in capability synthesis

Understand exactly which current fields must remain available through `semantic_context` to avoid breaking later stages.

- [ ] **Step 2: Write the failing e2e assertion update**

In `tests/e2e/test_commit_semantic.py`, update the context-stage test to expect:
- `repo-context.json` exists
- top-level keys are `shared_hints`, `semantic_context`, `summary`
- current semantic assertions now read from `semantic_context`
- `repo-hints.json` still exists in this subproject

Example target assertion shape:

```python
context = load_json(str(semantic_dir / "repo-context.json"))
assert context["semantic_context"]["local_capabilities"] == ["commit-extract", "commit-semantic", "demand"]
assert context["semantic_context"]["confidence"] == "high"
assert (semantic_dir / "repo-hints.json").exists()
```

- [ ] **Step 3: Implement the layered output in `_run_context()`**

In `skills/commit-semantic/run.py`, change the context-building logic so it writes:
- `shared_hints` using the current hint payload plus required placeholder structures
- `semantic_context` using the current repo-context payload
- `summary` using the defined counting rules and provisional placeholder status

Required defaults in this subproject:
- `source_provenance = {}` if not yet available
- `hint_confidence = {}` if not yet available
- `conflicts = []`
- `source_snapshot.docs = hints.get("doc_sources", [])`
- `source_snapshot.codebase_map = []`
- `summary.bootstrap_status = "full"`

- [ ] **Step 4: Preserve downstream compatibility through one accessor**

Update reader behavior so downstream capability synthesis uses only:

```python
repo_context.get("semantic_context", repo_context)
```

Apply this consistently anywhere in `skills/commit-semantic/run.py` that still expects the flat shape.

Do not redesign downstream capability synthesis in this subproject.

- [ ] **Step 5: Keep `repo-hints.json` compatibility explicit**

Leave `repo-hints.json` emission intact with its current shape.

This subproject must not silently remove it.

- [ ] **Step 6: Run targeted tests**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -k context -v
pytest tests/test_shared_repo_context_contract.py -v
```

Expected: PASS

- [ ] **Step 7: Run the broader commit-semantic e2e slice**

Run:
```bash
pytest tests/e2e/test_commit_semantic.py -v
```

Expected: PASS, including stages after context.

- [ ] **Step 8: Optional checkpoint commit**

```bash
git add skills/commit-semantic/run.py tests/e2e/test_commit_semantic.py
git commit -m "feat: adopt layered shared repo context contract"
```

---

## Task 3: Update skill docs to match the contract

**Files:**
- Modify: `skills/commit-semantic/SKILL.md`

- [ ] **Step 1: Update the context-stage description**

Document explicitly:
- `repo-context.json` is now the canonical layered contract artifact
- `repo-hints.json` remains compatibility-only in this subproject
- producer ownership has **not** migrated yet
- `shared_hints` is reusable context
- `semantic_context` is semantic-local interpreted context
- `summary` is provisional now and will gain stronger semantics later

- [ ] **Step 2: Update the output schema section**

Replace flat output wording with the layered context contract and explain that later subprojects will move producer ownership upstream to `commit-extract`.

- [ ] **Step 3: Run a focused read-through against code**

Verify the skill doc matches:
- actual artifact names
- actual stage behavior
- actual compatibility status
- current owner (`commit-semantic`) remains temporary producer

- [ ] **Step 4: Include doc acceptance check in plan completion**

Manually confirm the doc no longer claims:
- flat `repo-context.json`
- migrated ownership
- operational guarantees for summary fields

---

## Task 4: Verify subproject boundary discipline

**Files:**
- Modify: `docs/superpowers/plans/2026-03-24-shared-bootstrap-context-contract.md` (this plan only, if needed)

- [ ] **Step 1: Confirm no reliability features slipped in**

Before declaring this subproject done, verify no implementation work added:
- staleness checks
- fallback logic
- bypass flags
- prompt injection changes
- eval fixtures

If any of these slipped in, remove them or explicitly defer them.

- [ ] **Step 2: Confirm ownership did not silently migrate yet**

Verify:
- `commit-extract` is still not the producer in this subproject
- `commit-semantic` remains the temporary producer while emitting the new contract

This is intentional. Do not jump ahead.

- [ ] **Step 3: Final verification commands**

Run:
```bash
pytest tests/test_shared_repo_context_contract.py tests/e2e/test_commit_semantic.py -v
```

Expected: PASS

- [ ] **Step 4: Final commit**

```bash
git add skills/commit-semantic/run.py skills/commit-semantic/SKILL.md tests/test_shared_repo_context_contract.py tests/fixtures/shared_repo_context/example_repo_context.json tests/e2e/test_commit_semantic.py docs/superpowers/plans/2026-03-24-shared-bootstrap-context-contract.md
git commit -m "chore: finalize shared context contract subproject"
```

---

## Test Strategy Summary

### Unit / contract coverage
- `tests/test_shared_repo_context_contract.py`
  - Top-level contract
  - Required keys
  - Nested item shapes
  - Enum values
  - Counting semantics
  - Fixture-backed shape validation

### Integration coverage
- `tests/e2e/test_commit_semantic.py`
  - Context stage emits layered contract
  - `repo-hints.json` compatibility artifact still exists
  - Later stages still function when reading `semantic_context`

### Explicitly deferred to later subprojects
- `commit-extract` producer tests
- freshness / stale detection tests
- adaptive fallback tests
- focused helpful/stale/conflicting prior eval fixtures

---

## Acceptance Criteria
- `repo-context.json` is emitted with the exact top-level layered contract.
- Nested structure shapes are normatively defined and fixture-tested.
- `repo-hints.json` continues to be emitted unchanged for compatibility.
- `commit-semantic` later stages continue to function by reading `semantic_context` through a single compatibility accessor.
- `skills/commit-semantic/SKILL.md` documents the new contract accurately and does not falsely claim ownership migration.
- No freshness, fallback, bypass, prompt injection, or eval behavior is added in this subproject.

---

## Notes for implementers
- Keep the diff boring.
- Do not sneak in owner migration yet.
- Do not redesign `commit-semantic` capability synthesis.
- The goal of this subproject is contract stabilization, not semantic quality improvement.
- If the current implementation does not already separate hint payload from interpreted context cleanly, add a tiny deterministic helper function in `skills/commit-semantic/run.py` that constructs `shared_hints` and `semantic_context` from the current outputs. Do not invent new semantics.
