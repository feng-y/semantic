# Commit-Extract Eval Definitions

These evals define prompt quality for `skills/commit-extract/prompt.md`.

All evals are **binary yes/no** and are applied consistently across the fixed 13-commit DaVinci dataset.

## Core evals

### 1. `system_object_clarity`
**Question:** Does the output use section names that point to a real subsystem, capability, or semantic object rather than a generic bucket?

**Pass:**
- Section names identify a concrete subsystem, serving surface, schema, lifecycle area, or semantic object
- Names are specific enough that they do not plausibly fit half the repo

**Fail:**
- Section names are generic buckets like `Code changes`, `Configuration behavior`, `Runtime behavior`, `Observability`, or other vague labels

---

### 2. `behavior_vs_config`
**Question:** Do section items describe capability, behavior, contract, or constraint changes rather than patch narration or config listing?

**Pass:**
- Items explain what changed semantically
- Config and docs appear as supporting evidence unless they independently change behavior or operator-visible control

**Fail:**
- Items mostly narrate file/config changes
- The output reads like a patch summary instead of a semantic extract

---

### 3. `semantic_density_gate`
**Question:** Does the output avoid over-extracting from low-semantic docs/config-only commits?

**Pass:**
- Docs/config-only commits stay sparse
- Low-semantic commits are not forced into multiple pseudo-semantic sections

**Fail:**
- Weak commits get inflated semantic structure unsupported by the patch

---

### 4. `prose_avoidance`
**Question:** Does the output avoid editorial, release-note style narration?

**Pass:**
- Wording is factual, semantic, and direct

**Fail:**
- Wording drifts into prose like `clarifies`, `sharpens`, `improves` without grounding in concrete semantic meaning

---

### 5. `section_naming_accuracy`
**Question:** Do section names match the actual semantic content inside those sections?

**Pass:**
- Section names and contained items align closely

**Fail:**
- Section names are misleading, overly broad, or semantically mismatched with their items

---

## Rule-focused evals (split from `invariant_quality`)

### 6. `rule_presence_when_warranted`
**Question:** When a commit clearly changes lifecycle, compatibility, boundary enforcement, ownership, ordering, alignment, idempotency, resource limits, or failure isolation, does the output include 1-3 `rules_invariants`?

**Pass:**
- Relevant commits include at least 1 reusable rule and at most 3
- High-semantic commits that establish reusable constraints do not omit rules entirely

**Fail:**
- Commits that clearly warrant rules emit none
- Or emit an excessive number of rules (4+)

**Notes:**
- Not every commit should have rules
- This eval is only about commits where rules are actually warranted

---

### 7. `rule_abstraction_level`
**Question:** Are `rules_invariants` expressed as subsystem/system constraints rather than patch-local details?

**Pass:**
- Rules describe reusable constraints such as lifecycle, compatibility, ownership, boundary, ordering, alignment, idempotency, or failure isolation
- Rules do not depend on exact helpers, file names, flags, field names, or patch-local mechanics

**Fail:**
- Rules mention concrete helpers, files, fields, slots, local mechanics, or patch steps
- Rules are too close to implementation detail to be reusable later

---

### 8. `rule_non_duplication`
**Question:** Are `rules_invariants` more abstract than section items instead of paraphrasing them?

**Pass:**
- Rules capture what must remain true beyond this patch
- Rules add a reusable layer of meaning beyond the item summaries

**Fail:**
- Rules mostly restate section items in slightly different wording
- Rules duplicate item content rather than abstracting it

---

### 9. `rule_selectivity`
**Question:** Does the output avoid inventing weak rules for docs-only, config-only, or low-semantic commits?

**Pass:**
- Weak/docs/config-only commits have no rules, or at most one very strong reusable rule

**Fail:**
- Low-semantic commits contain multiple weak or forced rules
- Rules appear to exist only to satisfy scoring pressure

---

## Current evaluation model

The old single eval `invariant_quality` is deprecated for future iterations.

Use these four narrower rule evals instead:
- `rule_presence_when_warranted`
- `rule_abstraction_level`
- `rule_non_duplication`
- `rule_selectivity`

This gives a more actionable diagnosis:
- missing rules
- weak abstraction
- duplicated rules
- bad selectivity
