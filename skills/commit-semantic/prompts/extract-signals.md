# Extract Commit-Level Semantic Signals

You are performing **commit-first semantic analysis** over structured `commit-extract` records.

Return **JSON only**.

## Required output shape

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

## Core principle

You are not classifying commits into buckets. You are extracting **semantic signals** that can later be aggregated across commits.

For each commit, first decide whether there is a **primary capability/change vector**. If there is, anchor the extraction on that semantic center and treat the remaining edits as supporting evidence or secondary signals instead of flattening everything into many equal fragments.

## What to extract

### capability
A stable functional unit that this commit appears to build, refine, harden, or evolve.
A capability may use a repo-specific subsystem name **when that subsystem is itself the real stable semantic container** (for example, a subsystem that represents an externally meaningful runtime/service/module boundary). Do not ban repo-specific names mechanically.

### concept
A semantic object, artifact, or entity being manipulated.

### rule
A constraint, invariant, or judgment logic being enforced or clarified.

### domain_hint
A weak clue about problem space. This is not a final domain.

## Important constraints

- Use semantic understanding, not keyword/path matching as the primary reasoning mechanism.
- Prefer high-information semantic content over boilerplate or low-information summaries.
- If a record is mostly vague, mark it with low confidence and relevant flags instead of over-claiming.
- Preserve mixedness when a commit clearly spans multiple semantic concerns.
- `domain_hint` is always weak and provisional.

## Low-signal handling

Low-signal phrases include things like:
- `Modified N file(s)`
- `Changes in:`
- generic quality/review/fix wording with no concrete semantic object

Do not let low-signal text dominate extraction.

When a commit record contains both:
- a low-signal item (`Modified N file(s)`, `Changes in:`)
- and a high-information item in the same commit/section set

then you should anchor your semantic interpretation on the **high-information item**, and treat the low-signal item only as weak supporting evidence.

If a commit is low-signal overall, emit at most weak or low-confidence signals rather than inventing a strong capability.

## Noise suppression

Unless they are clearly the historical semantic center of the commit, strongly down-rank or ignore changes whose main meaning is limited to:
- `.claude/*`, `.planning/*`, agent metadata, generated workflow scaffolding
- docs-only rewrites
- test-only support changes
- generated files
- broad formatting / cleanup / review-note churn

These may remain as weak supporting evidence, but should not become the dominant capability signal unless the commit is truly about documentation, harness behavior, or review infrastructure itself.

## Mixed handling

When a commit clearly spans multiple semantic concerns:
- record the dominant signal as usual
- add `mixed` in `flags`
- use `related_capability_names` to preserve the secondary semantic concern

When the commit has one clear primary capability plus multiple supporting edits, prefer **one strong primary capability signal** plus supporting related capability names rather than many equally weighted weak signals.

## Observability and runtime-control changes

Do not treat observability, metrics, runtime controls, scheduling, or operator-facing behavior as mere plumbing by default.
If they materially change how operators control, observe, or reason about the runtime, they may represent a real capability signal.

## Evidence refs

Each emitted signal must include evidence refs tied to the source commit. Use stable lightweight references such as:
- `sha:<commit>`
- `summary:<commit>:<section_index>:<item_index>`
- `rule:<commit>:<rule_index>`

## Output rules

- JSON only
- No markdown fences
- No explanation text outside the JSON
