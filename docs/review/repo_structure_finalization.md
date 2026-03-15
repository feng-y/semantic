# Repo Structure Finalization

This document is an executable finalization plan for Claude Code.

Goal:

Finalize the repository structure so that:

- externally it is clearly a **Claude Code plugin / skill repo**
- internally it remains a **semantic pipeline runtime**
- old and new skill systems do not coexist ambiguously
- repository layout is easier to understand for a new user
- documentation, manifest, skills, prompts, runtime, tests, and review artifacts are coherent

This task is a **structure finalization pass**, not a semantic pipeline redesign.

---

# Core Principle

The repository must communicate this model clearly:

```text
External = Claude Code plugin / skills
Internal = semantic runtime / semantic artifacts
```

Claude Code should perform only **minimal safe structural cleanup**.

---

# Part 1 — Current State Audit

Audit the repository and classify directories/files into these layers:

## Plugin-facing layer

- `manifest.yaml`
- `skills/`
- `prompts/`

## Runtime layer

- `src/`

## Semantic state layer

- `docs/semantic/discovery/`
- `docs/semantic/review/`
- `docs/semantic/baseline/`

## Contract layer

- `docs/semantic/schemas/`
- `protocols/`

## Documentation / review layer

- `README.md`
- `INSTALL.md`
- `USER_GUIDE.md`
- `CHANGELOG.md`
- `docs/review/`
- `docs/semantic-design/`

Output:

```text
Current State Audit

plugin_layer_clear: YES / NO
runtime_layer_clear: YES / NO
semantic_state_layer_clear: YES / NO
contract_layer_clear: YES / NO
docs_layer_clear: YES / NO
```

---

# Part 2 — Skill System Finalization

The repository currently contains overlapping old/new skill names.

Target public skill set:

- `semantic-init.skill`
- `semantic-discover.skill`
- `semantic-review.skill`
- `semantic-refine.skill`
- `semantic-baseline.skill`
- `semantic-status.skill`
- `semantic-reset.skill`

Tasks:

1. Review all files under `skills/`
2. Identify legacy or overlapping skills such as older discovery / refinement / umbrella skills
3. Choose one of these safe strategies:

### Preferred strategy

Move legacy skills to:

```text
skills/legacy/
```

### Alternative strategy

If clearly unused and not referenced by manifest/tests/docs, remove them.

4. Ensure `manifest.yaml` points only to the final public skill set
5. Ensure README / docs describe only the final public skill set

Do NOT keep both old and new skills presented as equal public interfaces.

Output:

```text
Skill Finalization

public_skills_finalized: YES / NO
legacy_skills_isolated: YES / NO
manifest_aligned: YES / NO
changes_applied:
- ...
```

---

# Part 3 — Root Directory Cleanup

Review root-level markdown/task files.

Move planning / review / migration files into:

```text
docs/review/
```

Examples that should not remain floating at repo root if they are workflow/review artifacts:

- plugin readiness plans
- migration plans
- execution guides
- hardening task files

Allowed root-level files should remain limited to:

- `README.md`
- `INSTALL.md`
- `USER_GUIDE.md`
- `CHANGELOG.md`
- `IMPLEMENTATION_ORDER.md` (if still intentionally public)
- `manifest.yaml`
- `pyproject.toml`

Use minimal safe moves only.

Output:

```text
Root Cleanup

root_clean: YES / NO
files_moved:
- ...
deferred_root_items:
- ...
```

---

# Part 4 — Semantic State vs Documentation Clarity

The repository currently stores semantic runtime state under:

```text
docs/semantic/
```

This is acceptable for v1, but it can be confusing because it mixes documentation-style paths with generated state.

Do NOT perform a risky path migration unless absolutely necessary.

Instead, do the following:

1. Make the distinction explicit in `README.md`
2. Make the distinction explicit in `USER_GUIDE.md`
3. Optionally add a short note file:

```text
docs/semantic/README.md
```

Explain that:

- `docs/semantic/discovery/`, `review/`, and `baseline/` are generated semantic state
- `docs/semantic/schemas/` are contracts
- `docs/semantic-design/` contains human-written design docs

Output:

```text
Semantic State Clarity

semantic_state_explained: YES / NO
docs_vs_state_boundary_clear: YES / NO
changes_applied:
- ...
```

---

# Part 5 — Review Folder Index

The `docs/review/` folder contains multiple reports and execution plans.

Create:

```text
docs/review/README.md
```

This file should classify contents into:

- execution plans
- step reports
- safety audits
- migration/finalization reports

It should help a new contributor understand:

- which files are active plans
- which files are completed reports
- which files are final audits

Output:

```text
Review Index

review_index_created: YES / NO
review_folder_navigable: YES / NO
```

---

# Part 6 — README Finalization

Update `README.md` so that it clearly presents the repository as:

```text
Claude Code plugin / skill repo
```

README must clearly explain:

1. public plugin-facing layer:
   - `manifest.yaml`
   - `skills/`
   - `prompts/`

2. internal runtime:
   - `src/`

3. semantic state:
   - `docs/semantic/`

4. design / review docs:
   - `docs/semantic-design/`
   - `docs/review/`

5. final public skill set

README must not present legacy skills as public interface.

Output:

```text
README Finalization

plugin_positioning_clear: YES / NO
skill_interface_clear: YES / NO
runtime_explained: YES / NO
semantic_state_explained: YES / NO
```

---

# Part 7 — Verification

After all changes, verify:

1. `manifest.yaml` resolves all public skills
2. public skills load correctly
3. prompts still resolve
4. discovery pipeline still runs
5. refine pipeline still runs
6. baseline synthesis still runs
7. docs links resolve
8. README matches actual repository structure
9. no runtime imports break because of moved review files

Suggested tests:

- existing test suite via `pytest`
- any skill-system / manifest tests already present
- lightweight checks for moved review files not referenced by runtime

Output:

```text
Verification

manifest_resolution: PASS / ISSUE
skills_loading: PASS / ISSUE
prompt_resolution: PASS / ISSUE
discovery_pipeline: PASS / ISSUE
refine_pipeline: PASS / ISSUE
baseline_pipeline: PASS / ISSUE
docs_link_integrity: PASS / ISSUE
readme_repo_match: PASS / ISSUE
```

---

# Part 8 — Final Review Report

Generate:

```text
docs/review/repo_structure_finalization_report.md
```

Report structure:

```text
Repo Structure Finalization Report

Current State Audit: PASS / ISSUE
Skill Finalization: PASS / ISSUE
Root Cleanup: PASS / ISSUE
Semantic State Clarity: PASS / ISSUE
Review Index: PASS / ISSUE
README Finalization: PASS / ISSUE
Verification: PASS / ISSUE

Changes Applied:
- ...

Non-Blocking Recommendations:
- ...

Overall Verdict:
REPO STRUCTURE FINALIZED
or
ADDITIONAL STRUCTURE CLEANUP REQUIRED
```

---

# Important Constraints

- Do NOT redesign the semantic pipeline
- Do NOT change semantic invariants
- Do NOT perform a risky `docs/semantic/` → `artifacts/` migration in this step
- Do NOT remove legacy skills unless clearly unreferenced and safe
- Prefer isolation / clarification over destructive cleanup
