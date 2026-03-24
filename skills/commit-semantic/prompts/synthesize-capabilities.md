# Synthesize Capability Candidates

You are synthesizing stable **capability candidates** from commit-level semantic signals.

Return **JSON only**.

## Required output shape

```json
{
  "capabilities": [
    {
      "capability_id": "string",
      "canonical_name": "string",
      "observed_names": ["string"],
      "description": "string",
      "evidence_refs": ["string"],
      "repo_context_refs": ["string"],
      "confidence": "high | medium | low",
      "status": "stable | candidate | provisional",
      "naming_source": "repo-hint | observed-pattern | synthesized",
      "flags": ["string"]
    }
  ]
}
```

## Core principle

This stage turns many commit-level signals into a smaller set of stable capability candidates.

## What counts as a capability candidate

A capability candidate should represent a stable semantic unit that appears across commits, not a one-off implementation detail or work-type label.

## Naming rules

- Prefer repo hints as prior for `canonical_name` when they are credible.
- Allow commit history to override when docs are weak, stale, or clearly mismatched.
- Preserve all meaningful observed names in `observed_names`.
- Use `status: provisional` when the name is still semantically unstable.
- `capability_id` must be stable and should not simply duplicate the canonical name without normalization.
- Prefer **specific semantic capability names** over generic workflow names.
- Avoid generic names such as `pipeline`, `update`, `cleanup`, `quality`, `review`, or `infrastructure` unless the evidence truly supports them as stable capabilities.
- If one candidate is supported mainly by low-signal commit wording and another is supported by repeated high-information commit descriptions, prefer the high-information capability as canonical.
- Stable repo-specific subsystem names are allowed when they are the real semantic container of the capability rather than an incidental folder label.

## Merge / split guidance

Merge signals when they clearly describe the same stable semantic unit, even if wording differs.

Do not merge signals that only share generic words like:
- pipeline
- update
- fix
- review
- quality

Split when two clusters differ in:
- the semantic object they operate on
- the rule/invariant they express
- the capability outcome they produce

Prefer a **primary capability + supporting deltas** interpretation when one capability is clearly central and surrounding edits mainly reinforce, configure, test, document, or operationalize that capability.

## Confidence guidance

- `high`: repeated across commits with strong evidence and stable semantics
- `medium`: plausible stable unit but still somewhat narrow or unevenly evidenced
- `low`: weak evidence or ambiguous grouping

## Output scope

Do not emit final domains, concepts, or rules here. Focus only on capability candidates.

## Output rules

- JSON only
- No markdown fences
- No explanation text outside the JSON
