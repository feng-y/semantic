---
name: repo-structure
description: Build or refresh repo-level baseline facts from commit history artifacts, precomputed codebase analysis artifacts, and optional architecture documents. Use when the task is to extract structured repo facts, run the repo-structure pipeline, inspect stage status, or regenerate facts.vN.yaml for downstream semantic modeling.
---

# Repo Structure

`repo-structure` is a stage-driven extraction skill.

Its only goal is to convert three upstream evidence sources into a versioned factual baseline:

- commit history artifacts → `hotspot_map`
- precomputed codebase analysis artifacts → `codebase_map`
- optional architecture docs + repo evidence → `architect_augment`

These are validated and fused into:

- `data/repo-structure/baseline/facts.vN.yaml`

This file is the only source-of-truth produced by this skill.

## Use this skill when

Use this skill when the task is to:

- build or refresh repo-level baseline facts
- extract structured repo facts from git/code/docs signals
- run or debug the `repo-structure` pipeline
- inspect preflight status, stage status, versions, or snapshot lineage
- regenerate `facts.vN.yaml` for downstream semantic layers

## Do not use this skill when

Do **not** use this skill when the task is to:

- directly produce Domain Map / Concept Map / Rule Map
- analyze a product requirement or generate a Demand Card
- review a code diff or MR
- modify implementation code for a feature or bugfix
- perform downstream semantic consolidation (`domain-model` should consume baseline facts)

## Boundary

This skill **does**:

- read and verify upstream artifacts
- extract fact entries with evidence binding
- generate `hotspot_map`, `codebase_map`, and `architect_augment`
- validate, normalize, deduplicate, and detect conflicts
- arbitrate and freeze `facts.vN.yaml`

This skill **does not**:

- directly edit Domain / Concept / Rule Map
- infer runtime demand objects from raw user requests
- implicitly invoke upstream stages or other skills
- treat intermediate maps as final semantic assets
- replace `domain-model`

## Preconditions

Before running this skill:

- current directory must be the git repo root
- `.git/` must exist
- `data/commit-extract/` must already exist
- `.planning/codebase/STRUCTURE.md` must exist
- `.planning/codebase/ARCHITECTURE.md` must exist
- `.planning/codebase/STACK.md` must exist
- `.planning/codebase/CONCERNS.md` must exist

Optional input:

- `docs/ARCHITECTURE.md`

Important rules:

- `gsd` is an upstream analyzer; this skill consumes `.planning/codebase/` artifacts and does **not** invoke `gsd` internally
- `commit-extract` is an upstream artifact; this skill does **not** generate it internally
- dependencies must be checked before stage execution
- missing required dependencies fail fast
- do not silently backfill missing upstream inputs inside a stage

## Commands

Use these commands:

- `/repo-structure check`
- `/repo-structure run`
- `/repo-structure run --stage <stage>`
- `/repo-structure resume`
- `/repo-structure status`
- `/repo-structure reset`

Supported stages:

- `sample`
- `hotspot`
- `extract`
- `augment`
- `validate`
- `baseline`

## Preflight

Always run dependency checks before execution.

`/repo-structure check` should report:

- missing required artifacts
- invalid artifacts
- stale artifacts
- schema mismatches
- repo snapshot mismatches
- writable path issues

Default behavior is strict fail-fast.

`--continue` may only downgrade optional-input problems to warnings. It must not bypass required-input failures.

## Stage flow

Run the pipeline in this order:

1. `sample`
2. `hotspot`
3. `extract`
4. `augment`
5. `validate`
6. `baseline`

### sample

Purpose:

- build a sampling manifest from precomputed codebase artifacts

Behavior:

- use `STRUCTURE.md` as primary guidance
- use references from `ARCHITECTURE.md` and `CONCERNS.md`
- use repo fallback probing only when gsd artifacts are incomplete

Output:

- `data/repo-structure/sample/manifest.yaml`

### hotspot

Purpose:

- build commit-history facts from upstream commit artifacts

Behavior:

- consume `data/commit-extract/`
- generate hotspot facts from `commit-extract + commit-semantic`
- do not reduce this stage to raw git stats

Output:

- `data/repo-structure/maps/hotspot_map.vN.yaml`

### extract

Purpose:

- build codebase facts from precomputed codebase analysis artifacts

Behavior:

- deterministically split documents into sections
- create `DocSectionTask` units
- route work by section type
- extract atomic fact entries with evidence binding

Critical rule:

- extraction unit is a section task, **not** a whole file
- output unit is a fact entry, **not** a paragraph summary

Output:

- `data/repo-structure/maps/codebase_map.vN.yaml`

### augment

Purpose:

- strengthen or challenge architecture claims using repo evidence

Behavior:

- if `docs/ARCHITECTURE.md` exists, extract architecture claims
- collect candidate evidence deterministically with Python search/probe steps
- adjudicate claim/evidence matching with an LLM worker
- classify each claim as:
  - `evidence_backed`
  - `weakly_backed`
  - `gap`
  - `drift`

If architecture docs are missing:

- write an empty `architect_augment` artifact and continue

Output:

- `data/repo-structure/maps/architect_augment.vN.yaml`

### validate

Purpose:

- clean and normalize extracted facts before baseline freeze

Behavior:

- schema validation
- evidence completeness checks
- normalization
- deduplication
- conflict detection
- preserve unresolved conflicts for baseline arbitration

Output:

- `data/repo-structure/facts/validated.vN.yaml`
- `data/repo-structure/facts/conflicts.vN.yaml`

### baseline

Purpose:

- fuse validated facts into the final baseline snapshot

Behavior:

- merge the three source maps
- apply arbitration rules
- preserve lineage and source provenance
- freeze versioned baseline output

Output:

- `data/repo-structure/baseline/facts.vN.yaml`
- `data/repo-structure/baseline/facts.latest.yaml`
- `data/repo-structure/baseline/snapshot.yaml`

## Output contract

Primary output:

- `data/repo-structure/baseline/facts.vN.yaml`

Derived or intermediate outputs:

- `sample/manifest.yaml`
- `maps/hotspot_map.vN.yaml`
- `maps/codebase_map.vN.yaml`
- `maps/architect_augment.vN.yaml`
- `facts/validated.vN.yaml`
- `facts/conflicts.vN.yaml`
- `state.json`
- `snapshot.yaml`

Downstream rule:

- downstream semantic consumers should read baseline facts
- Domain Map / Concept Map / Rule Map are derived knowledge views and must not be hand-edited as a substitute for baseline repair

## Worker agents

### extract worker

Use when processing `DocSectionTask` units from gsd artifacts.

Worker responsibility:

- extract atomic fact entries
- bind evidence using section-specific locator rules
- avoid unsupported inference
- return structured YAML/JSON only

Do not:

- summarize the whole file
- generalize beyond the provided section
- invent implementation details

### augment worker

Use when judging architecture claims against candidate repo evidence.

Worker responsibility:

- compare claim text against provided evidence candidates
- prefer direct implementation evidence over comments
- assign `evidence_backed | weakly_backed | gap | drift`
- attach authoritative `stable_ref` and rationale

Do not:

- search the repo on its own without provided evidence candidates
- treat comments as stronger than direct implementation evidence
- silently upgrade weak evidence to strong evidence

## Arbitration rules

When the same fact appears multiple times, resolve in this order:

1. source priority: `architect > hotspot > codebase`
2. within same priority: `recurring > evidence_backed > isolated`
3. if the same statement comes from different repo snapshots, prefer the current snapshot
4. if arbitration is still unresolved, preserve both facts and record the conflict

## State and versions

This skill maintains:

- independent versions for:
  - `hotspot_map`
  - `codebase_map`
  - `architect_augment`
- a snapshot version recording their combination
- `state.json` for stage progress, output versions, and repo snapshot commit

Do not force all three maps to re-run together unless the user explicitly requests a full refresh.

## Gotchas

- Do **not** treat Domain / Concept / Rule Map as outputs of this skill
- Do **not** call `gsd` from inside this pipeline
- Do **not** treat `hotspot_map` as raw git statistics
- Do **not** batch extract by whole file; use deterministic section split first
- Do **not** output paragraph summaries in `extract`; output fact entries with evidence binding
- Do **not** let `augment` rely on architecture docs alone; all accepted claims must be evidence-backed or explicitly marked weak/gap/drift
- Do **not** silently backfill missing upstream artifacts inside a stage
- Do **not** edit derived semantic views to "fix" baseline issues; fix them in validation or baseline arbitration
- Do **not** hide unresolved conflicts; preserve them explicitly

## References to load when needed

Consult these files as needed:

- `references/pipeline-overview.md`
- `references/evidence-model.md`
- `references/arbitration-rules.md`
- `references/preflight-rules.md`
- `references/gotchas.md`

Worker prompt templates:

- `prompts/extract_codebase.md`
- `prompts/augment_architect.md`
