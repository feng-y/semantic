
# Semantic Harness Plugin Migration — Execution Guide

This document is designed to be used directly with **Claude Code (CC)** so that
the migration can be executed **step-by-step with minimal user interaction**.

It contains:
- Migration steps
- Execution rules
- Ready-to-use prompts for Claude Code
- Expected outputs and review artifacts

---

# GLOBAL EXECUTION RULES

Claude Code must follow these rules:

1. Execute **only one step at a time**
2. After each step:
   - apply code/doc changes
   - run required tests
   - generate review report
3. Stop after completing the step
4. Do NOT continue automatically
5. Preserve existing tests and safety logic
6. Prefer minimal changes
7. If uncertain, report instead of modifying architecture

---

# ACTIVATION PROMPT (Start Migration)

Paste this into Claude Code:

You are executing a staged repository migration.

The migration plan is defined in:
docs/review/semantic_harness_plugin_migration.md

Execution rules:

1. Execute the plan strictly step by step.
2. Only execute ONE step at a time.
3. After each step:
   - apply the required code/doc changes
   - run the tests required by that step
   - generate the step review report required by that step
4. After finishing a step, STOP and report:
   - what changed
   - which tests ran
   - whether the step passed or failed
   - which review report file was generated
5. Do NOT continue to the next step automatically.
6. Prefer minimal safe changes.
7. Preserve existing tests and safety guarantees.

Start now with:

STEP 1 — Skill System Normalization

---

# STEP 1 — Skill System Normalization

Goal:

Normalize the skill system to a standard Claude Code plugin layout.

Target skills:

semantic-init
semantic-discover
semantic-review
semantic-refine
semantic-baseline
semantic-status
semantic-reset

Tasks:

- Inspect `skills/`
- Rename or create skills to match target list
- Ensure each skill contains:

name
description
entrypoint
prompt

Verify prompt paths exist.

---

Tests:

Create:

tests/test_skill_system_step1.py

Test:

- skill loader loads skills
- prompts exist
- names match expected list

---

Review Output:

docs/review/step1_skill_system_report.md

---

Execution prompt for Claude Code:

Proceed with STEP 1 — Skill System Normalization.
Perform only Step 1 tasks.
Run Step 1 tests.
Generate the Step 1 review report.
Stop after completion.

---

# STEP 2 — Plugin Manifest Alignment

Goal:

Ensure repository functions as a Claude Code plugin.

Verify:

manifest.yaml exists

Expected:

name: semantic-harness

skills:
  - skills/semantic-init.skill
  - skills/semantic-discover.skill
  - skills/semantic-review.skill
  - skills/semantic-refine.skill
  - skills/semantic-baseline.skill
  - skills/semantic-status.skill
  - skills/semantic-reset.skill

---

Tests:

tests/test_manifest_step2.py

Verify:

- manifest loads
- skill paths valid

---

Review Output:

docs/review/step2_manifest_report.md

---

Execution prompt:

Proceed to STEP 2 — Plugin Manifest Alignment.
Apply only Step 2 changes.
Run Step 2 tests.
Generate the Step 2 report.
Stop afterwards.

---

# STEP 3 — Runtime Mapping

Goal:

Verify skills correctly map to runtime functions.

Mapping:

semantic-init → src.main.init_workspace
semantic-discover → src.discovery_executor.run_discovery
semantic-review → src.context_builder.build_review_context
semantic-refine → src.refine_executor.run_refine
semantic-baseline → src.refine_executor.run_baseline
semantic-status → src.state_inspector.inspect_state
semantic-reset → src.main.reset_workspace

Implement functions if missing.

---

Tests:

tests/test_runtime_mapping_step3.py

---

Review Output:

docs/review/step3_runtime_report.md

---

Execution prompt:

Proceed to STEP 3 — Runtime Mapping.
Implement only mapping fixes.
Run Step 3 tests.
Generate Step 3 review report.
Stop afterwards.

---

# STEP 4 — Documentation Alignment

Goal:

Ensure repo documentation clearly describes a Claude Code plugin.

Update README.md.

Must include:

Semantic Harness is a Claude Code plugin for semantic repository understanding.

Architecture overview:

skills → prompts → runtime → semantic artifacts

Verify:

INSTALL.md
USER_GUIDE.md
CHANGELOG.md

---

Tests:

tests/test_docs_step4.py

---

Review Output:

docs/review/step4_docs_report.md

---

Execution prompt:

Proceed to STEP 4 — Documentation Alignment.
Update docs only.
Run Step 4 tests.
Generate Step 4 review report.
Stop afterwards.

---

# STEP 5 — Plugin Verification

Goal:

Verify full semantic pipeline works.

Pipeline:

semantic-init
semantic-discover
semantic-review
semantic-refine
semantic-baseline

Verify artifacts:

repo-facts
repo-understanding
knowledge-confidence
domain-candidates

---

Tests:

Extend:

tests/test_system.py

---

Final Review Output:

docs/review/plugin_migration_final_report.md

---

Execution prompt:

Proceed to STEP 5 — Plugin Verification.
Run full pipeline tests.
Generate final plugin migration report.
Stop after completion.

