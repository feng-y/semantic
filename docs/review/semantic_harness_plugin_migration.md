
# Semantic Harness Plugin Migration

This task migrates the repository into a **standard Claude Code plugin architecture**.

Execution must follow **incremental steps**.

Each step must include:

1. modification
2. test
3. review report

Do NOT perform all changes at once.

---

# MIGRATION PLAN

Step 1 — Skill System Normalization  
Step 2 — Plugin Manifest Alignment  
Step 3 — Runtime Mapping  
Step 4 — Documentation Alignment  
Step 5 — Plugin Verification  

Each step must generate:

docs/review/stepX_report.md

---

# STEP 1 — Skill System Normalization

Goal:

Normalize skills into standard Claude Code skill structure.

Target skills:

semantic-init  
semantic-discover  
semantic-review  
semantic-refine  
semantic-baseline  
semantic-status  
semantic-reset  

Tasks:

1 Inspect `skills/` directory

List existing skills.

2 Rename or create skills to match target list.

3 Validate each skill contains:

name  
description  
entrypoint  
prompt  

4 Verify prompt paths exist.

5 Load skills using skill_loader.

---

## Tests

Create:

tests/test_skill_system_step1.py

Test:

- skill loader loads all skills
- skill names match target
- prompt paths exist

---

## Review Output

Generate:

docs/review/step1_skill_system_report.md

Include:

skills_found  
skills_expected  
missing_skills  
invalid_skills  

---

# STEP 2 — Plugin Manifest Alignment

Goal:

Ensure repository works as Claude Code plugin.

Tasks:

Verify:

manifest.yaml exists

Expected format:

name: semantic-harness

skills:
  - skills/semantic-init.skill
  - skills/semantic-discover.skill
  - skills/semantic-review.skill
  - skills/semantic-refine.skill
  - skills/semantic-baseline.skill
  - skills/semantic-status.skill
  - skills/semantic-reset.skill

Validate:

skill paths exist

---

## Tests

Create:

tests/test_manifest_step2.py

Test:

manifest loads  
skills listed exist

---

## Review Output

docs/review/step2_manifest_report.md

---

# STEP 3 — Runtime Mapping

Goal:

Ensure skills map to runtime functions.

Mapping:

semantic-init
→ src.main.init_workspace

semantic-discover
→ src.discovery_executor.run_discovery

semantic-review
→ src.context_builder.build_review_context

semantic-refine
→ src.refine_executor.run_refine

semantic-baseline
→ src.refine_executor.run_baseline

semantic-status
→ src.state_inspector.inspect_state

semantic-reset
→ src.main.reset_workspace

If missing:

implement runtime function.

---

## Tests

Create:

tests/test_runtime_mapping_step3.py

Test:

import module  
function exists

---

## Review Output

docs/review/step3_runtime_report.md

---

# STEP 4 — Documentation Alignment

Goal:

Ensure repo is clearly documented as Claude Code plugin.

Update README.md.

README must include:

Project description

"Semantic Harness is a Claude Code plugin for semantic repository understanding."

Skill list

Architecture overview:

skills
↓
prompts
↓
runtime
↓
semantic artifacts

Verify:

INSTALL.md  
USER_GUIDE.md  
CHANGELOG.md  

---

## Tests

Create:

tests/test_docs_step4.py

Verify files exist.

---

## Review Output

docs/review/step4_docs_report.md

---

# STEP 5 — Plugin Verification

Goal:

Verify full plugin pipeline.

Pipeline:

semantic-init
↓
semantic-discover
↓
semantic-review
↓
semantic-refine
↓
semantic-baseline

Verify artifacts:

repo-facts  
repo-understanding  
knowledge-confidence  
domain-candidates  

Baseline generation works.

---

## Tests

Extend:

tests/test_system.py

Verify pipeline execution.

---

## Final Review

Generate:

docs/review/plugin_migration_final_report.md

Report:

Skill System
PASS / FAIL

Manifest
PASS / FAIL

Runtime Mapping
PASS / FAIL

Docs
PASS / FAIL

Pipeline Execution
PASS / FAIL

Final Verdict:

PLUGIN READY
or
CHANGES REQUIRED
