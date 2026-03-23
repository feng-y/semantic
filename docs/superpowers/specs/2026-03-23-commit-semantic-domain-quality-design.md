# Commit-Semantic Domain Quality Optimization Design

Date: 2026-03-23
Status: APPROVED
Scope: commit-semantic domain quality optimization after repo-level manual validation

## Problem Statement

Repo-level manual validation now succeeds end-to-end, but domain quality is still not good enough for stable downstream use.

Current observed output on the real repository:
- `domain_count = 7`
- `uncategorized_ratio = 0.1762`
- top domains include `tests`, `test`, `skill`, `review`, `claude`
- `uncategorized` is still ranked #2

This means the execution chain is working, but the semantic layer is still too dependent on heuristic token buckets rather than stable repository domains.

## Goals

This iteration optimizes three things together:

1. **Domain schema quality**
   - remove duplicate or near-duplicate domains like `test` / `tests`
   - improve domain naming so it reflects stable repo-level areas rather than commit-title noise
   - produce cleaner `domains.json` for downstream use

2. **Classification coverage**
   - reduce `uncategorized_ratio` below the current repo-level result
   - improve deterministic assignment without aggressively forcing weak matches

3. **Runtime priority clarity**
   - make LLM-based discover/classify the preferred path
   - keep heuristic fallback as explicit degraded mode only
   - expose mode information in outputs so manual review can distinguish high-quality vs fallback runs

## Non-Goals

This iteration does **not**:
- redesign aggregate or distill scoring formulas
- change commit-extract output schema
- integrate demand stage
- build a full human feedback / write-back correction loop

## Recommended Approach

Use a three-layer convergence strategy, but execute it in ordered sub-phases:

1. **Phase A — Stabilize the domain schema first**
2. **Phase B — Use the better schema to reduce `uncategorized`**
3. **Phase C — Make LLM the primary strategy and fallback explicit**
4. **Phase D — Expose runtime mode in exported artifacts**

Rationale:
- If domain definitions are noisy, lowering `uncategorized` just pushes more units into bad buckets.
- Schema cleanup increases the value of deterministic path/keyword matching.
- LLM-first policy should remain the target architecture, but fallback is still needed for local execution and CI.
- Runtime mode must be visible so fallback output is not mistaken for full semantic output.

## Alternatives Considered

### A. Three-layer convergence (recommended)
- Clean domain schema
- Improve deterministic classification quality and coverage
- Switch runtime priority to LLM-first, fallback-only

**Pros**
- Solves all three user goals in the right order
- Keeps local runnability while improving final architecture
- Minimizes the risk of pushing more units into unstable domains

**Cons**
- Broadest scope of the options
- Needs careful verification to avoid regressions

### B. LLM-first immediately
- Prioritize true LLM discover/classify now
- Defer schema cleanup to later

**Pros**
- Most aligned with the target architecture
- Avoids investing heavily in heuristics

**Cons**
- Real output quality may still be unstable if post-processing is weak
- Local fallback remains under-specified
- Does not directly solve duplicate domain names

### C. Heuristic-only quality pass
- Improve fallback discover/classify and stop there

**Pros**
- Fastest path to local quality improvement
- Easy to verify in CI and local runs

**Cons**
- Makes fallback the de facto primary architecture
- Drifts from the intended LLM-first design

## Design

## Canonical Domain Schema

Normalized domains must preserve the current `domain` field name for compatibility with the existing pipeline.
The canonical normalized domain object is:

```json
{
  "domain": "tests",
  "description": "Repository test and verification surface",
  "paths": ["tests/", "src/..."],
  "keywords": ["tests", "pytest", "verification"]
}
```

Required fields:
- `domain: str`
- `description: str`
- `paths: list[str]`
- `keywords: list[str]`

Merge output rules:
- merged domain keeps the winner `domain` string after normalization
- `description` prefers the first non-empty description from the highest-quality candidate
- `paths` are unioned and deduplicated, preserving shortest-prefix-first ordering
- `keywords` are unioned and deduplicated after lowercase normalization

Winner selection priority during merge:
1. domain with non-empty paths
2. domain with more normalized keywords
3. domain with non-noise normalized name
4. stable lexical order as final tiebreak

## Runtime State Contract

The implementation must use `HarnessState.metadata` as the source of truth for runtime mode.

Required metadata keys:
- `external_orchestration: bool`
- `orchestration_mode: "llm_preferred" | "local_fallback" | "mixed_degraded"`
- `discover_mode: "llm" | "fallback" | "cached_llm" | "cached_fallback"`
- `classify_mode: "llm" | "fallback" | "mixed" | "cached"`

Persistence contract:
- `domains.json` must persist discover provenance alongside `_fingerprint` and `domains`
- required persisted fields in `domains.json`:
  - `discover_mode`
  - `orchestration_mode_at_discover`
- on discover cache hit, the runner must restore `discover_mode` from cached provenance into `HarnessState.metadata`
- if classify is skipped due to a future cache/resume optimization, the same rule applies: persisted provenance must be restored before export
- export must report actual execution provenance, not default assumptions

Mode transitions:
- discover via LLM + classify via LLM => `orchestration_mode = "llm_preferred"`
- discover via fallback + classify via fallback => `orchestration_mode = "local_fallback"`
- any mixed combination, cache reuse of one mode plus execution of another mode, or any LLM stage that falls back after failure => `orchestration_mode = "mixed_degraded"`

Failure / degradation decision table:

| Stage | Failure case | Action | Exported mode |
|------|--------------|--------|---------------|
| discover | LLM output empty/invalid | retry once if orchestration exists, else fallback normalize+save | `mixed_degraded` if fallback used |
| discover | LLM unavailable | fallback normalize+save | `local_fallback` or `mixed_degraded` |
| classify | some batches fail | fallback-local classify failed batches, keep successful LLM batches | `mixed_degraded` |
| classify | all batches fail and no fallback match | leave unresolved units as `uncategorized` | `mixed_degraded` |
| classify | no LLM path available | deterministic/fallback classify only | `local_fallback` |

Export contract:
`summary.json` must include:
- `orchestration_mode`
- `discover_mode`
- `classify_mode`

The runner is responsible for setting these values before export. External orchestrators may set `external_orchestration=true`, but exported mode fields must still reflect actual execution, not intent.

### 1. Discover redesign

Discover will now have two conceptual layers:

#### 1.1 Preferred path: LLM discover

LLM discover remains responsible for producing the initial semantic domain list from:
- `units/all.jsonl` summary
- optional architecture document context

Expected LLM output remains:
- `domain`
- `description`
- `paths`
- `keywords`

But the post-processing contract becomes stricter:
- domain name must be normalized and singular/plural-safe
- paths must be meaningful for later commit-level assignment
- keywords must represent domain semantics, not just copied commit-title fragments

#### 1.2 Required post-normalization (applies to both LLM and fallback)

Every discovered domain list must go through normalization before being accepted.
The implementation contract is:

```python
normalize_domains(domains: list[dict]) -> list[dict]
```

Call order:
1. parse or generate raw domains
2. normalize domains
3. validate normalized domains
4. save `domains.json`

This normalization step must be applied in both paths:
- LLM path: `complete_discover()`
- fallback path: local discover writer

Fingerprint semantics:
- input fingerprint remains based on input artifacts (`units/all.jsonl` and optional architecture doc)
- normalization does not change fingerprint inputs
- normalization only affects saved domain output quality

Normalization rules:

1. **Name normalization**
   - lowercase
   - dash-case
   - singular/plural merge when normalized stems match exactly (`test` + `tests` => `tests`)

2. **Noise filtering**
   - reject or down-rank generic workflow verbs/nouns such as:
     - `add`, `update`, `fix`, `impl`, `phase`, `final`, `worktree`
   - reject pure process buckets unless they have strong repo support via paths or keyword overlap

3. **Duplicate and near-duplicate merging**
   - exact same normalized domain name => merge
   - near-duplicate merge only when either:
     - keyword Jaccard overlap >= 0.6, or
     - path-prefix overlap >= 0.5
   - merged domain keeps deduplicated keyword union and path union

4. **Minimum quality gate**
   - reject a domain if all of the following are true:
     - `paths == []`
     - fewer than 3 deduplicated keywords
     - normalized name is in the noise-token list
   - LLM output may bypass this only when description explicitly references a stable repo area, boundary, or subsystem

#### 1.3 Fallback discover role

Fallback discover should no longer try to produce a broad set of token-bucket domains.
It should instead produce a **small, conservative domain skeleton** using stronger signals:
- stable path fragments
- repeated repo nouns
- high-signal theme tokens after noise filtering

Fallback discover should prefer fewer, stronger domains over broad coverage.

### 2. Classify redesign

Classification should also separate preferred path from degraded path.

Classification granularity must be explicit:
- **commit-level assignment** is used when reliable `file_paths` exist and all changed files converge on one domain through deterministic path matching
- **unit-level scoring** is used only for mixed commits, missing-path commits, or low-confidence deterministic cases

Path-evidence rule after commit-level failure:
- if commit-level convergence fails because the commit spans multiple candidate domains, unit-level fallback scoring must **disable path-prefix scoring** for that commit
- in that case, unit-level fallback may use only:
  - theme token match
  - summary token match
  - section-name token match
  - domain-keyword match
- if those non-path signals are still ambiguous, the unit must go to LLM when available, otherwise remain `uncategorized`
- path-prefix scoring remains allowed only when commit-level path evidence already converged to a single domain or when a future implementation introduces per-unit path attribution

#### 2.1 Preferred path: LLM classify

LLM classify is preferred when:
- `is_mixed = true`
- file paths are absent
- path-based assignment spans multiple candidate domains
- deterministic scoring is low-confidence or tied

This preserves the original design intent: semantic classification is LLM-first for ambiguous cases.

#### 2.2 Deterministic classify upgrade

Deterministic assignment remains important for speed and local execution, but must become more structured.

Scoring priority:
1. path-prefix match
2. theme token match
3. summary token match
4. section-name token match
5. domain-keyword match

Scoring weights:
- path-prefix match = 5
- theme token match = 3
- summary token match = 2
- section-name token match = 2
- domain-keyword match = 1

Scoring rules:
- repeated token hits do not stack beyond one hit per signal type
- path-prefix match is evaluated once per candidate domain
- keyword overlap is deduplicated after lowercase normalization
- minimum deterministic assignment score = 4
- ambiguous if `top1 - top2 < 2`
- if score < 4 => do not assign deterministically
- if ambiguous => send to LLM when available, otherwise leave as `uncategorized`

This reduces accidental assignment while still lowering `uncategorized` where evidence is strong.

### 3. Runtime priority and degradation policy

Three runtime modes should be explicit:

#### 3.1 `llm_preferred`
Default mode.
- discover prefers LLM
- classify prefers LLM for ambiguous work
- fallback is used only when LLM path is unavailable or fails

#### 3.2 `local_fallback`
Explicit local mode.
- discover/classify use deterministic fallback only
- intended for local testing, CI, or offline execution

#### 3.3 `mixed_degraded`
Partial degradation mode.
- some stages used LLM, others used fallback
- used when one stage succeeds semantically and another falls back

### 4. Output visibility

`summary.json` should include explicit runtime mode markers so human review can evaluate quality in context.

Recommended additions:
- `orchestration_mode`
- `discover_mode`
- `classify_mode`

This prevents fallback results from being mistaken for fully semantic LLM-backed output.

## Validation Strategy

### Automated validation

1. **Domain normalization tests**
   - singular/plural merge (`test` + `tests`)
   - duplicate keyword/path merge
   - noise token rejection

2. **Classification confidence tests**
   - strong path match assigns deterministically
   - weak ambiguous match remains unresolved until LLM/fallback decision
   - `uncategorized` decreases only when evidence is sufficient

3. **Mode reporting tests**
   - summary reports correct discover/classify mode
   - fallback runs are clearly marked degraded

4. **Repo-level regression test**
   - end-to-end local run should no longer produce duplicate domains like `test/tests`
   - `uncategorized_ratio` should improve from the current baseline

### Required test matrix

The implementation plan must cover at least these fixture cases:
- LLM discover output containing duplicate domains like `test/tests`
- fallback discover output containing noisy token buckets
- path-based single-domain commit assignment
- path-based multi-domain commit ambiguity
- mixed/no-path unit classification tie
- git/path failure with degraded mode reporting preserved in `summary.json`
- summary schema assertions for:
  - `orchestration_mode`
  - `discover_mode`
  - `classify_mode`

### Manual validation

Run the real repository again and review:
- top 5 domains should look like stable repo areas, not token buckets
- `uncategorized` should not rank near the top if domain quality improved
- duplicate domains should disappear

## Success Criteria

Implementation planning must treat the current repo-level run used in this session as the baseline snapshot.
Baseline source:
- worktree: `/Users/yan./git/3p/sematic-harness/.worktrees/commit-semantic-domain`
- summary artifact: `data/commit-semantic/summary.json`
- observed baseline: `uncategorized_ratio = 0.1762`

Success criteria are mode-specific:

### Deterministic / CI gate (`local_fallback`)
1. No duplicate or near-duplicate top-level domains such as `test/tests`
2. Duplicate normalized domain names after post-processing = 0
3. Top 5 domains contain no banned noise tokens as their final normalized names
4. `summary.json` includes `orchestration_mode`, `discover_mode`, and `classify_mode`
5. Top 5 repo-level domains are more stable than the current baseline, meaning each top domain has at least one of:
   - non-empty path prefixes, or
   - at least 3 normalized keywords after deduplication

### Repo-level quality gate (`llm_preferred` or `mixed_degraded`)
6. `uncategorized_ratio` is lower than the baseline `0.1762` when re-run against the same baseline worktree snapshot
7. The repo-level result is reviewed manually, not treated as a hard deterministic CI gate, unless model/input conditions are explicitly frozen in a later iteration

## Risks

1. **Over-normalization risk**
   - aggressive merge rules may collapse legitimately distinct domains

2. **False-confidence risk**
   - lowering `uncategorized` too aggressively can hide uncertainty by forcing bad assignments

3. **Fallback drift risk**
   - if fallback becomes too feature-rich, it may replace the intended LLM-first architecture

Mitigation:
- keep normalization rules narrow and test-driven
- require confidence thresholds before deterministic assignment
- keep fallback explicitly marked as degraded mode

## Implementation Notes

Planned implementation should likely touch:
- `skills/commit-semantic/run.py`
- optionally `src/commit_semantic/domain_utils.py` if normalization logic needs a pure-function home
- targeted tests in `tests/e2e/test_commit_semantic.py` and/or related domain tests

No downstream demand changes are included in this spec.
