# Changelog: commit-extract Autoresearch

## Experiment 0 — baseline

**Score:** 67/78 (85.9%)
**Change:** skills/commit-extract/prompt.md — original (no changes)
**Reasoning:** Establish baseline with the actual production prompt (not docs/generate_commit.md)
**Result:** Strong baseline. Key observations:
- Section naming already excellent (13/13) — "Configuration behavior", "Runtime behavior" absent
- prose_avoidance (12/13) — one false positive on 45c20e4 ("Repository contract" + "Request lifecycle safeguards")
- invariant_quality is the weakest at 5/13 (38%) — main opportunity for improvement
- One commit (fb3c317fe834) had JSON parse error due to output length truncation — excluded from scoring
**Failing outputs:** invariant_quality (8/13 failures), one prose false positive, one JSON truncation

## Experiment 1 — DISCARD

**Score:** 62/78 (79.5%) — baseline was 67/78 (85.9%), **-5 points**
**Change:** Added explicit rule-extraction guidance: "when rules are warranted", "when rules are not warranted", and rule abstraction/quality tests.
**Reasoning:** `invariant_quality` was the weakest eval (5/13), so the hypothesis was that stronger rule guidance would increase reusable `rules_invariants` without harming selectivity.
**Result:** The experiment regressed overall. `invariant_quality` fell from 5/13 to 4/13, `behavior_vs_config` fell from 12/13 to 7/13, and multiple extractions became unstable (several 504 gateway errors, one `NoneType` failure, multiple empty-section outputs).
**Why discarded:** The mutation did not improve the target eval and materially worsened total score and extraction stability. The additional rule guidance likely made the prompt heavier and more brittle instead of improving abstraction quality.
**Failing outputs:** Empty-section / error outputs on several commits (`686e0b5e`, `c599c1db`, `45c20e42`, `24bde3a0`, `81623076`, `7123b0fd`). The mutation is not safe to keep.

## Next direction
- Do **not** push harder on "more rules"
- Instead, split `invariant_quality` into narrower evals (`rule_presence_when_warranted`, `rule_abstraction_level`, `rule_non_duplication`, `rule_selectivity`) before the next iteration
- Future mutations should be smaller and should avoid increasing prompt verbosity in a fragile way
