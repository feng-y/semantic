Analyze historical commit <SHA> from the exact patch and output exactly one JSON object for append-only monthly JSONL storage.

Use only:
- `git show --stat --summary <SHA>`
- `git show <SHA>`

Do not use:
- current staged changes
- current unstaged changes
- branch name
- existing commit message as source of truth
- chat context

Output requirements:
- Output exactly one valid JSON object
- Do not wrap in markdown code fences
- Do not output explanations
- The object must represent exactly one commit
- The object must be suitable for appending as one line in a JSONL file

Interpretation rules:
- Treat this commit as potentially large, multi-day, and aggregate
- Preserve all independently meaningful functional blocks
- Organize the commit into sections
- Each section may contain multiple semantic items
- Prefer structured semantic completeness over aggressive compression
- Do not collapse independently meaningful changes just to make the record shorter

Writing rules:
- Write in subsystem-semantic terms, not implementation-plumbing terms
- Prefer capability changes, behavior changes, performance improvements, bug fixes, safety/correctness fixes, compatibility changes, and meaningful boundary/constraint changes
- Mention boundaries, failure-handling behavior, ordering constraints, ownership constraints, or lifecycle constraints when they affect system semantics, correctness, safety, or operations
- Avoid framing changes as internal helper extraction, plumbing, enablement, instrumentation, or implementation mechanics unless that is the real historical meaning
- Omit helper names, local symbols, defaults, thresholds, test internals, commented-out code, and implementation tracing unless essential

Section rules:
- Section names must be generic functional blocks or change themes, not repo-specific domains and not low-level issue labels
- Prefer names such as:
  - Inference path
  - Request lifecycle
  - Output compatibility
  - Failure handling
  - Boundary enforcement
  - Configuration behavior
  - Scheduling flow
  - Resource management
  - Runtime behavior
  - Data access
- Do not use repo-specific domain names unless absolutely necessary
- Do not use overly narrow labels such as memory_safety, request_completion, memory_lifecycle, helper_refactor, or jni_interface as top-level sections
- Fold observability, tests, config declarations, cleanup, and supporting refactors into the main section they support unless they are independently meaningful changes
- Prefer fewer, stronger sections over many small supporting sections

**ANTI-PATTERNS — NEVER use these section names:**
- "Code changes" — this is the most common failure mode; it says nothing about semantics
- "Configuration behavior" — used as a catch-all for anything config-related; too generic
- "Runtime behavior" — vague bucket that means different things to different people
- "Observability" — too broad; if it's about metrics, name it "Serving metrics"; if it's about tracing, name it "Request tracing"
- "Operations" — meaningless unless qualified (e.g., "Model operations", "Feature operations")

**Section naming test:** If your section name could describe 50%+ of all commits in this repo, it is too generic. Pick a name that describes this commit's specific subsystem or change type.

Semantic item rules:
- Each item should describe one meaningful change at the functional or subsystem level
- Use `op` to describe the semantic nature of the change
- Prefer concise semantic statements over implementation narration
- Keep all items that have independent semantic value
- Do not limit the number of items per section artificially
- A semantic item is worth keeping when it represents a meaningful capability change, behavior change, performance change, bug fix, safety fix, compatibility change, operator-facing behavior change, or boundary/failure-handling change
- Tests, observability, config declarations, cleanup, and supporting refactors should usually not appear as standalone items unless they independently change system behavior, contract, constraints, or operator-facing control
- Do not keep standalone items for:
  - exact flag names, defaults, numeric ranges, or threshold formulas
  - exact function/method/JNI/helper names
  - timer or metric additions unless observability is a main purpose of the commit
  - test case breakdowns unless the commit is primarily about tests
  - patch-level sequencing or local implementation steps
- When multiple low-level edits support one semantic change, merge them into one higher-level item
- Keep only items that would still be worth recording if the commit were summarized for a human six months later

Op classification rules:
- Use `refactor` only when the primary meaning is structural cleanup, deduplication, code movement, or maintainability improvement with no meaningful change in behavior, safety, correctness, compatibility, boundary handling, or operator-facing behavior
- Do NOT use `refactor` when the change fixes an incorrect behavior, restores a violated rule, enforces a required access path, tightens lifecycle handling, fixes ownership, fixes ordering dependencies, prevents stale references, or prevents incorrect failure propagation
- Prefer `bugfix` when the change corrects wrong behavior, wrong routing, stale references, incorrect access paths, incorrect fallback behavior, or previously broken logic
- Prefer `safety` when the change primarily prevents crashes, use-after-free, invalid lifetime, invalid ownership, unsafe reuse, or unsafe partial-failure behavior
- Prefer `compat` when the main meaning is aligning with an existing contract, output format, protocol, or downstream expectation
- Prefer `config` only when the change meaningfully changes operator-facing behavior or runtime control, not for mere declaration of a flag or constant
- Prefer `optimize` only when the change meaningfully improves performance or resource usage and that is part of the historical meaning
- If a change mainly enforces a required rule or invariant, classify it as `bugfix` or `safety` rather than `refactor`

Merge rules:
- Do not split one semantic change into multiple items just because the patch has multiple supporting implementation steps
- Merge partitioning logic, shared tensor reuse, result reassembly, timeout sharing, and similar support details into one higher-level inference item when they serve the same feature
- Merge ownership fixes, accessor routing, reset ordering, stale-reference prevention, and similar support details into one higher-level lifecycle/safety item when they serve the same bug fix
- Prefer one stronger semantic item over several patch-detail items

Section summary rules:
- Do not produce a commit-level summary
- The semantic center of the record is the section
- Each section may include a short `summary` only if it helps describe the section as a functional block
- A section summary must summarize the section as a whole, not restate item text line by line
- Keep section summaries short and semantic; do not explain implementation mechanics

Rules and invariants rules:
- `sections` are the primary semantic record
- `rules_invariants` are secondary and must stay sparse, abstract, and non-duplicative
- Only include a rule/invariant when it can stand alone as a reusable system constraint beyond this specific patch
- Keep `rules_invariants` sparse: prefer 0 to 3 entries, and omit them entirely if no strong reusable rules are present
- Extract subsystem-level or system-level rules/invariants, not patch-level implementation steps
- Prefer lifecycle, ownership, boundary, failure-isolation, compatibility, ordering, alignment, idempotency, or resource-usage constraints
- Avoid mentioning exact helper names, local accessors, reset calls, or other implementation mechanics unless essential
- Do not emit trivial, purely mechanical, or duplicate rules
- Do not restate a section item as a rule unless the rule is clearly more abstract and reusable than the item wording

Field selection rules:
- Keep only semantic fields that cannot be trivially recovered from the commit id
- Do not include commit-level title, rendered message, or other presentation-only fields that can be reconstructed later
- The commit acts as a container; sections are the primary semantic unit

JSON schema:
{
  "sha": "<SHA>",
  "author": "<author or empty string>",
  "date": "<date or empty string>",
  "is_large_aggregate": true,
  "is_mixed": true,
  "sections": [
    {
      "name": "<generic functional block name>",
      "theme": "<short change theme>",
      "importance": "<primary|secondary>",
      "summary": "<optional section summary>",
      "items": [
        {
          "op": "<feat|bugfix|optimize|config|refactor|compat|safety|docs|test|cleanup|other>",
          "summary": "<semantic summary>"
        }
      ]
    }
  ],
  "rules_invariants": [
    {
      "kind": "<lifecycle|ownership|boundary|failure_isolation|compatibility|ordering|alignment|idempotency|resource_limit|other>",
      "statement": "<rule or invariant>",
      "enforced_by_commit": true
    }
  ]
}