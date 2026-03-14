# Implementation Order for Claude Code

This file defines the recommended implementation order for Claude Code.
Follow this order strictly. Do not redesign the architecture.

## Step 1 — Read and Summarize
Read these files first:

- README.md
- manifest.yaml
- docs/semantic-design/*.md
- protocols/*.md
- docs/semantic/schemas/*.md

Produce a short summary of:
1. command model
2. skill model
3. artifact layout
4. schema rules
5. refine loop
6. sampling policy
7. versioning policy

Do not implement yet.

---

## Step 2 — Build Minimal Runtime Skeleton
Implement a minimal runtime skeleton with:

- command dispatcher
- skill loader
- prompt loader
- artifact writer
- repository state inspector

Do not implement advanced intelligence yet.

---

## Step 3 — Implement init
Implement `init` first.

Requirements:
- create required directories
- create missing default files
- do not overwrite existing user content

Required structure:

docs/semantic/
  schemas/
  discovery/
  review/
  baseline/

docs/semantic/review/
  architect-feedback.md
  semantic-change-log.md

docs/semantic/discovery/
  sampling-report.md

---

## Step 4 — Implement repo-semantic-discovery.skill
Implement `skills/repo-semantic-discovery.skill` exactly in declared step order.

Requirements:
- follow step order exactly
- write every artifact
- apply versioning policy
- do not skip validation
- honor sampling mode and timeout

Discovery flow:
1. repo-sampling.prompt
2. repo-facts.prompt
3. evidence-extraction.prompt
4. validate-artifact.prompt
5. domain-candidates.prompt
6. repo-understanding.prompt
7. validate-artifact.prompt
8. knowledge-confidence.prompt
9. review-summary.prompt
10. apply artifact versioning

---

## Step 5 — Implement semantic-refinement.skill
Implement `skills/semantic-refinement.skill`.

Requirements:
- always read latest versioned discovery artifacts
- patch sections instead of rewriting whole files
- preserve architect edits
- preserve evidence
- generate semantic-change-log.md
- only synthesize baseline after explicit acceptance

Refine flow:
1. semantic-refine.patch.prompt
2. semantic-change-log.prompt
3. validate-artifact.prompt
4. apply artifact versioning
5. baseline-synthesis.prompt if accepted

---

## Step 6 — Implement semantic-harness.skill
Implement the orchestrator last.

Requirements:
- inspect current semantic state
- choose discover or refine
- do not run autonomous multi-round loops
- report current state and next recommended step

Routing logic:
- if no versioned discovery artifacts exist: run discovery skill
- elif no accepted baseline exists: run refinement skill
- else: report semantic baseline exists and wait for new architect feedback

---

## Step 7 — Implement Validation Behavior
Implement validation according to:

- protocols/artifact-validation.md
- prompts/validation/validate-artifact.prompt

Validation must check:
- required fields
- evidence presence
- confidence presence where required
- stable field names

Invalid artifact must not replace last valid artifact.

---

## Step 8 — Implement Sampling Behavior
Implement sampling policy according to:

- protocols/sampling-policy.md
- prompts/discover/repo-sampling.prompt

Sampling modes:
- auto
- confirm

Timeout behavior:
- in auto mode, timeout switches to confirm mode
- emit sampling-report.md before continuing

---

## Step 9 — Implement Versioning Behavior
Implement artifact versioning according to:

- protocols/artifact-versioning.md

Policy:
- keep latest 3 working versions by default
- keep accepted baseline versions
- do not delete explicitly checkpointed or accepted versions

Versioning applies to:
- discovery artifacts
- review artifacts

---

## Step 10 — Run Validation Scenarios
After implementation, run these scenarios:

### Scenario A — init
- verify directory creation
- verify no overwrite

### Scenario B — discover
- verify sampling-report.md generated
- verify versioned discovery artifacts generated
- verify review-summary.md generated

### Scenario C — refine
- provide architect feedback
- verify patch update
- verify semantic-change-log.md generated
- verify baseline synthesis after acceptance

For each scenario, report:
- executed steps
- written files
- validation failures if any

---

## Step 11 — Final Report
At the end, produce a report with:

- fully implemented items
- partially implemented items
- unresolved gaps vs spec
- recommended next follow-up
