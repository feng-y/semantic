# Repo-Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `repo-structure` skill — a 6-stage pipeline that produces a versioned fact baseline (`facts.vN.yaml`) from three independent source pipelines: commit history (via commit-extract/commit-semantic), codebase dossier (7-file gsd output), and architecture docs (optional).

**Architecture:** Python ETL pipeline extending `SkillRunner`. LLM analysis via Team Agent pattern (extract + augment use worker prompts). Three parallel source pipelines fused at `baseline`. Output is the sole source-of-truth; Domain/Concept/Rule Maps are derived views.

**Tech Stack:** Python 3.10+, pyyaml, gitpython, yaml schemas, LLM worker prompts

---

## File Structure

### New files to create

```
skills/repo-structure/
├── SKILL.md                              # Agent context template + commands
├── run.py                                # RepoStructureRunner (SkillRunner subclass)
├── preflight.py                          # Dependency + freshness checker
├── schemas/
│   ├── fact_entry.schema.yaml            # Per-fact schema (see spec)
│   ├── baseline_facts.schema.yaml        # facts.vN.yaml wrapper schema
│   └── state.schema.yaml                 # state.yaml schema
├── prompts/
│   ├── extract_codebase.md               # Extract worker prompt (section-routed)
│   └── augment_architect.md              # Augment worker prompt (two-phase)
└── references/
    ├── evidence-model.md                 # Locator types, stable_ref, fact vs claim
    ├── preflight-rules.md                # Preflight contract (from spec)
    ├── arbitration-rules.md              # Baseline arbitration (from spec)
    ├── pipeline-overview.md              # Operational overview (from spec)
    └── gotchas.md                       # 17 failure modes (from spec)

tests/
└── test_repo_structure.py                # E2E + unit tests
```

### Existing files to modify

```
src/dispatcher.py                         # Add /repo-structure routing
skills/commit-semantic/run.py              # Reuse existing hotspot output
skills/commit-extract/run.py               # Strict upstream dependency
```

### Reference spec files (read-only, already exist)

```
docs/superpowers/specs/2026-03-22-repo-structure-domain-model-design.md  # Core design
docs/superpowers/specs/2026-03-22-extract_codebase.md                     # Extract worker prompt
docs/superpowers/specs/2026-03-22-augment_architect.md                   # Augment worker prompt
docs/superpowers/specs/2026-03-22-fact_entry.schema.yaml.md             # Fact entry schema
docs/superpowers/specs/2026-03-22-baseline_facts.schema.md             # Baseline schema
docs/superpowers/specs/2026-03-22-state.schema.json.md                  # State schema
docs/superpowers/specs/2026-03-22-evidence-model.md                    # Evidence model
docs/superpowers/specs/2026-03-22-pipeline-overview.md                  # Pipeline overview
docs/superpowers/specs/2026-03-22-gotchas.md                           # Gotchas
docs/superpowers/specs/2026-03-29-arbitration-rules.md                  # Arbitration rules
docs/superpowers/specs/2026-03-22-preflight-rules.md                    # Preflight rules
skills/repo-structure/references/gotchas.md                             # Same as spec
```

---

## Three Source Pipelines (Fused at Baseline)

```
Pipeline A — commit history:
  data/commit-extract/ (upstream: commit-extract)
      → data/commit-semantic/patterns/ (upstream: commit-semantic)
      → hotspot_map.vN.yaml  (hotspot stage)

Pipeline B — codebase dossier (7 files):
  .planning/codebase/{STRUCTURE,ARCHITECTURE,CONCERNS,CONVENTIONS,
                       INTEGRATIONS,STACK,TESTING}.md  (upstream: gsd)
      → sample/manifest.yaml
      → codebase_map.vN.yaml  (extract stage)

Pipeline C — architecture docs (optional):
  docs/ARCHITECTURE.md  (upstream: architect)
      → architect_augment.vN.yaml  (augment stage)

All three → validate → baseline → facts.vN.yaml
```

---

## Task 1: Schema Files

Create the three YAML schemas from the spec documents.

**Files:**
- Create: `skills/repo-structure/schemas/fact_entry.schema.yaml`
- Create: `skills/repo-structure/schemas/baseline_facts.schema.yaml`
- Create: `skills/repo-structure/schemas/state.schema.yaml`

- [ ] **Step 1: Create `schemas/` directory and `fact_entry.schema.yaml`**

Copy the fact_entry schema from `docs/superpowers/specs/2026-03-22-fact_entry.schema.yaml.md`:

```yaml
# skills/repo-structure/schemas/fact_entry.schema.yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
schema_name: repo_structure_fact_entry
schema_version: v1
type: object
additionalProperties: false
required:
  - fact_id
  - fact_type
  - statement
  - source
  - repo_snapshot_commit
  - evidence
properties:
  fact_id:
    type: string
    description: Stable UUID for this fact
  fact_type:
    type: string
    enum: [module_role, dependency_rule, boundary_constraint, pattern_usage, convention, invariant, hotspot_signal]
    description: Category of this fact
  domain:
    type: string
    description: Problem domain this fact belongs to
  category:
    type: string
    enum: [domain, concept, rule, invariant]
  statement:
    type: string
    description: Human-readable fact statement
  confidence:
    type: string
    enum: [confirmed, uncertain, contradicted]
    description: Evidence confidence level
  status:
    type: string
    enum: [active, conflicted, filtered]
    description: Fact lifecycle status
  repo_snapshot_commit:
    type: string
    description: Git HEAD at time of extraction
  source:
    type: string
    enum: [hotspot, codebase, architect]
    description: Which pipeline produced this fact
  evidence:
    type: array
    items:
      type: object
      additionalProperties: false
      required: [source_type, locator_type, locator, stable_ref]
      properties:
        source_type:
          type: string
          enum: [codebase, hotspot, architect]
        file_path:
          type: string
        locator_type:
          type: string
          enum: [file_path, symbol, config_key, section_ref, test_case, ast_pattern]
        locator:
          type: string
          description: Concrete value for the locator_type
        stable_ref:
          type: string
          description: Stable reference (symbol_signature_hash or file_blob_sha)
        rationale:
          type: string
          description: Why this evidence is relevant
  conflicts_with:
    type: array
    items:
      type: string
    description: IDs of facts this conflicts with
  resolution_reason:
    type: string
    description: Why this fact was chosen over a conflict
  metadata:
    type: object
    properties:
      generated_at:
        type: string
        format: date-time
      mapper_version:
        type: string
```

- [ ] **Step 2: Create `schemas/baseline_facts.schema.yaml`**

Copy from `docs/superpowers/specs/2026-03-22-baseline_facts.schema.md`:

```yaml
# skills/repo-structure/schemas/baseline_facts.schema.yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
schema_name: repo_structure_baseline_facts
schema_version: v1
type: object
additionalProperties: false
required: [metadata, facts, conflicts]
properties:
  metadata:
    type: object
    additionalProperties: false
    required: [version, repo_snapshot_commit, sources, generated_at]
    properties:
      version:
        type: string
        pattern: "^v[0-9]+$"
      repo_snapshot_commit:
        type: string
      sources:
        type: object
        properties:
          hotspot_map:
            type: string
          codebase_map:
            type: string
          architect_augment:
            type: string
      generated_at:
        type: string
        format: date-time
  facts:
    type: array
    items:
      $ref: "fact_entry.schema.yaml"
  conflicts:
    type: array
    items:
      type: object
      additionalProperties: false
      required: [fact_ids, conflict_type, resolution_status]
      properties:
        fact_ids:
          type: array
          items:
            type: string
        conflict_type:
          type: string
          enum: [contradictory_statement, snapshot_drift, source_priority_tie, evidence_strength_tie, unresolved_merge]
        explanation:
          type: string
        resolution_status:
          type: string
          enum: [preserved, resolved, dropped]
  lineage:
    type: object
    description: Maps fact_id to source artifact + version
```

- [ ] **Step 3: Create `schemas/state.schema.yaml`**

Copy from `docs/superpowers/specs/2026-03-22-state.schema.json.md` (converted to YAML form):

```yaml
# skills/repo-structure/schemas/state.schema.yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
schema_name: repo_structure_state
schema_version: v1
type: object
additionalProperties: false
required: [repo_snapshot, pipeline, stages, artifacts]
properties:
  repo_snapshot:
    type: object
    additionalProperties: false
    required: [head_commit, captured_at]
    properties:
      head_commit:
        type: string
      captured_at:
        type: string
        format: date-time
      branch:
        type: [string, "null"]
      is_dirty:
        type: [boolean, "null"]
  pipeline:
    type: object
    additionalProperties: false
    required: [skill_name, state_version, last_command, last_updated_at]
    properties:
      skill_name:
        type: string
        const: "repo-structure"
      state_version:
        type: string
      last_command:
        type: string
      last_updated_at:
        type: string
        format: date-time
      resume_from_stage:
        type: [string, "null"]
        enum: [sample, hotspot, extract, augment, validate, baseline, null]
      overall_status:
        type: string
        enum: [idle, running, success, failed, partial]
  stages:
    type: object
    additionalProperties: false
    required: [sample, hotspot, extract, augment, validate, baseline]
    properties:
      sample:
        $ref: "#/$defs/stageState"
      hotspot:
        $ref: "#/$defs/stageState"
      extract:
        $ref: "#/$defs/stageState"
      augment:
        $ref: "#/$defs/stageState"
      validate:
        $ref: "#/$defs/stageState"
      baseline:
        $ref: "#/$defs/stageState"
  artifacts:
    type: object
    additionalProperties: false
    required: [inputs, outputs]
    properties:
      inputs:
        type: object
        additionalProperties: false
        required: [commit_extract, codebase_dossier, architecture_doc]
        properties:
          commit_extract:
            $ref: "#/$defs/artifactState"
          codebase_dossier:
            type: object
            additionalProperties: false
            required: [STRUCTURE_md, ARCHITECTURE_md, CONCERNS_md, CONVENTIONS_md, INTEGRATIONS_md, STACK_md, TESTING_md]
            properties:
              STRUCTURE_md: { $ref: "#/$defs/artifactState" }
              ARCHITECTURE_md: { $ref: "#/$defs/artifactState" }
              CONCERNS_md: { $ref: "#/$defs/artifactState" }
              CONVENTIONS_md: { $ref: "#/$defs/artifactState" }
              INTEGRATIONS_md: { $ref: "#/$defs/artifactState" }
              STACK_md: { $ref: "#/$defs/artifactState" }
              TESTING_md: { $ref: "#/$defs/artifactState" }
          architecture_doc:
            $ref: "#/$defs/artifactState"
      outputs:
        type: object
        additionalProperties: false
        required: [sample_manifest, hotspot_map, codebase_map, architect_augment, validated_facts, conflicts, baseline_facts, baseline_snapshot]
        properties:
          sample_manifest: { $ref: "#/$defs/artifactState" }
          hotspot_map: { $ref: "#/$defs/artifactState" }
          codebase_map: { $ref: "#/$defs/artifactState" }
          architect_augment: { $ref: "#/$defs/artifactState" }
          validated_facts: { $ref: "#/$defs/artifactState" }
          conflicts: { $ref: "#/$defs/artifactState" }
          baseline_facts: { $ref: "#/$defs/artifactState" }
          baseline_snapshot: { $ref: "#/$defs/artifactState" }
  notes:
    type: [string, "null"]
$defs:
  stageState:
    type: object
    additionalProperties: false
    required: [status, last_run_at]
    properties:
      status:
        type: string
        enum: [not_run, running, success, failed, skipped]
      last_run_at:
        type: [string, "null"]
        format: date-time
      finished_at:
        type: [string, "null"]
      version:
        type: [string, "null"]
      repo_snapshot_commit:
        type: [string, "null"]
      error_code:
        type: [string, "null"]
      error_message:
        type: [string, "null"]
      warnings:
        type: array
        items:
          type: string
  artifactState:
    type: object
    additionalProperties: false
    required: [path, exists, status]
    properties:
      path:
        type: string
      exists:
        type: boolean
      status:
        type: string
        enum: [missing, ready, stale, invalid, optional_missing]
      version:
        type: [string, "null"]
      repo_snapshot_commit:
        type: [string, "null"]
      size_bytes:
        type: [integer, "null"]
        minimum: 0
      last_checked_at:
        type: [string, "null"]
      producer:
        type: [string, "null"]
      issues:
        type: array
        items:
          type: string
```

- [ ] **Step 4: Validate schemas exist**

Run: `ls skills/repo-structure/schemas/`
Expected: `fact_entry.schema.yaml baseline_facts.schema.yaml state.schema.yaml`

- [ ] **Step 5: Commit**

```bash
git add skills/repo-structure/schemas/
git commit -m "feat(repo-structure): add YAML schemas for fact_entry, baseline_facts, and state"
```

---

## Task 2: Preflight Module

Create the preflight checker that validates dependencies before any stage runs.

**Files:**
- Create: `skills/repo-structure/preflight.py`

- [ ] **Step 1: Write the preflight test**

```python
# tests/test_repo_structure.py
from __future__ import annotations
from pathlib import Path
import tempfile, yaml

def test_preflight_detects_missing_commit_extract(tmp_path, monkeypatch):
    """Preflight fails when commit-extract output is missing."""
    import skills.repo_structure.preflight as preflight

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    result = preflight.check(repo_root=tmp_path)
    assert result["ok"] is False
    assert any(i["producer"] == "commit-extract" for i in result.get("missing", []))


def test_preflight_detects_missing_gsd_dossier(tmp_path, monkeypatch):
    """Preflight fails when any of the 7 gsd files are missing."""
    import skills.repo_structure.preflight as preflight

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)

    result = preflight.check(repo_root=tmp_path)
    assert result["ok"] is False
    missing = result.get("missing", [])
    assert len(missing) >= 7  # All 7 gsd files


def test_preflight_warns_on_missing_architecture_doc(tmp_path, monkeypatch):
    """Preflight warns (not fails) when docs/ARCHITECTURE.md is absent."""
    import skills.repo_structure.preflight as preflight

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)
    for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                  "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text("# fake")

    result = preflight.check(repo_root=tmp_path)
    # Architecture doc is optional — should be in warnings, not missing
    assert result["ok"] is True
    arch_warnings = [w for w in result.get("warnings", []) if "ARCHITECTURE" in w.get("subject", "")]
    assert len(arch_warnings) >= 1


def test_preflight_ok_when_all_required_present(tmp_path, monkeypatch):
    """Preflight passes when all required inputs exist."""
    import skills.repo_structure.preflight as preflight

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)
    for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                  "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text("# fake")

    result = preflight.check(repo_root=tmp_path)
    assert result["ok"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_repo_structure.py::test_preflight_detects_missing_commit_extract tests/test_repo_structure.py::test_preflight_detects_missing_gsd_dossier tests/test_repo_structure.py::test_preflight_warns_on_missing_architecture_doc tests/test_repo_structure.py::test_preflight_ok_when_all_required_present -v`
Expected: 4 FAILs (module not found)

- [ ] **Step 3: Write the preflight module**

```python
# skills/repo_structure/preflight.py
"""Preflight checks for repo-structure pipeline.

Performs dependency validation, freshness checks, and snapshot matching
before any stage executes. Follows the contract in:
  docs/superpowers/specs/2026-03-22-preflight-rules.md

Classification levels:
  - missing: required dependency does not exist  → fail
  - invalid: dependency exists but unusable         → fail
  - warning: usable but suboptimal                  → warn
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class PreflightIssue:
    code: str
    subject: str
    message: str
    producer: str | None = None
    suggestion: str | None = None


@dataclass
class PreflightResult:
    ok: bool = True
    repo_head: str = ""
    missing: list[PreflightIssue] = field(default_factory=list)
    invalid: list[PreflightIssue] = field(default_factory=list)
    warnings: list[PreflightIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "repo_head": self.repo_head,
            "missing": [
                {"code": i.code, "subject": i.subject, "message": i.message,
                 "producer": i.producer, "suggestion": i.suggestion}
                for i in self.missing
            ],
            "invalid": [
                {"code": i.code, "subject": i.subject, "message": i.message,
                 "producer": i.producer, "suggestion": i.suggestion}
                for i in self.invalid
            ],
            "warnings": [
                {"code": i.code, "subject": i.subject, "message": i.message,
                 "producer": i.producer, "suggestion": i.suggestion}
                for i in self.warnings
            ],
        }


REQUIRED_GSD_FILES = [
    "STRUCTURE.md",
    "ARCHITECTURE.md",
    "CONCERNS.md",
    "CONVENTIONS.md",
    "INTEGRATIONS.md",
    "STACK.md",
    "TESTING.md",
]


def check(repo_root: Path | str = ".") -> PreflightResult:
    """Run all preflight checks. Returns result with missing/invalid/warnings lists."""
    root = Path(repo_root).resolve()
    result = PreflightResult()

    # 1. Repo root
    if not root.exists():
        result.ok = False
        result.missing.append(PreflightIssue(
            "MISSING_REPO_ROOT", "repo_root",
            f"Path does not exist: {root}"))
        return result

    # 2. Git repo
    if not (root / ".git").exists():
        result.ok = False
        result.missing.append(PreflightIssue(
            "MISSING_GIT_REPO", ".git",
            "Not a git repository", suggestion="cd to git repo root"))
        return result

    # 3. Current snapshot (HEAD commit)
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, check=True
        )
        result.repo_head = head.stdout.strip()
    except subprocess.CalledProcessError:
        result.ok = False
        result.invalid.append(PreflightIssue(
            "INVALID_HEAD", "git HEAD",
            "Cannot resolve HEAD commit"))
        return result

    # 4. Writable output path
    out_dir = root / "data" / "repo-structure"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        result.ok = False
        result.invalid.append(PreflightIssue(
            "OUTPUT_NOT_WRITABLE", str(out_dir),
            f"Cannot create output directory: {e}"))

    # 5. Required: commit-extract
    commit_extract = root / "data" / "commit-extract"
    if not commit_extract.exists():
        result.ok = False
        result.missing.append(PreflightIssue(
            "MISSING_INPUT", "data/commit-extract/",
            "Upstream commit-extract output not found",
            producer="commit-extract",
            suggestion="/commit-extract run"))
    elif not any(commit_extract.iterdir()):
        result.ok = False
        result.invalid.append(PreflightIssue(
            "EMPTY_ARTIFACT", "data/commit-extract/",
            "commit-extract directory is empty",
            producer="commit-extract"))

    # 6. Required: 7-file gsd dossier
    gsd_dir = root / ".planning" / "codebase"
    for fname in REQUIRED_GSD_FILES:
        fpath = gsd_dir / fname
        if not fpath.exists():
            result.ok = False
            result.missing.append(PreflightIssue(
                "MISSING_INPUT", str(fpath.relative_to(root)),
                f"gsd file not found",
                producer="gsd::map-codebase",
                suggestion="Run gsd map-codebase first"))
        elif fpath.stat().st_size == 0:
            result.ok = False
            result.invalid.append(PreflightIssue(
                "EMPTY_ARTIFACT", str(fpath.relative_to(root)),
                f"gsd file is empty",
                producer="gsd::map-codebase"))

    # 7. Optional: architecture doc
    arch_doc = root / "docs" / "ARCHITECTURE.md"
    if not arch_doc.exists():
        result.warnings.append(PreflightIssue(
            "OPTIONAL_INPUT_MISSING", "docs/ARCHITECTURE.md",
            "Optional architecture doc not found; augment stage will emit empty output",
            producer="architect"))
    elif arch_doc.stat().st_size == 0:
        result.warnings.append(PreflightIssue(
            "EMPTY_ARTIFACT", "docs/ARCHITECTURE.md",
            "Architecture doc is empty; augment stage may produce weak results"))

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_repo_structure.py::test_preflight_detects_missing_commit_extract tests/test_repo_structure.py::test_preflight_detects_missing_gsd_dossier tests/test_repo_structure.py::test_preflight_warns_on_missing_architecture_doc tests/test_repo_structure.py::test_preflight_ok_when_all_required_present -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/repo_structure/preflight.py tests/test_repo_structure.py
git commit -m "feat(repo-structure): add preflight dependency checker"
```

---

## Task 3: Runner Skeleton with Preflight Integration

Implement the `RepoStructureRunner` class that extends `SkillRunner`, adds the `check` command, and integrates preflight into `run`.

**Files:**
- Create: `skills/repo-structure/run.py`
- Modify: `skills/repo-structure/__init__.py` (empty init)

- [ ] **Step 1: Write the failing test for check command**

```python
# tests/test_repo_structure.py (add to existing file)

def test_run_check_command_fails_without_dependencies(tmp_path, monkeypatch):
    """check command returns non-zero when required inputs are missing."""
    import subprocess
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    # Module import needs the skill on path
    import sys
    skill_root = Path(__file__).parent.parent / "skills" / "repo_structure"
    sys.path.insert(0, str(skill_root.parent.parent))

    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, '{skill_root.parent}'); "
         f"from skills.repo_structure.run import RepoStructureRunner; "
         f"r = RepoStructureRunner(); exit(r.handle_check())"],
        capture_output=True, text=True
    )
    assert r.returncode != 0  # Should fail due to missing dependencies


def test_handle_check_returns_zero_when_ok(tmp_path, monkeypatch):
    """check command returns 0 when all required inputs are present."""
    import sys
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)
    for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                  "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text("# fake")

    skill_root = Path(__file__).parent.parent / "skills" / "repo_structure"
    sys.path.insert(0, str(skill_root.parent.parent))

    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, '{skill_root.parent}'); "
         f"from skills.repo_structure.run import RepoStructureRunner; "
         f"r = RepoStructureRunner(); exit(r.handle_check())"],
        capture_output=True, text=True
    )
    assert r.returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_repo_structure.py::test_run_check_command_fails_without_dependencies tests/test_repo_structure.py::test_handle_check_returns_zero_when_ok -v`
Expected: 2 FAILs (module not found)

- [ ] **Step 3: Write `__init__.py`**

```python
# skills/repo_structure/__init__.py
"""repo-structure skill package."""
```

- [ ] **Step 4: Write the `run.py` skeleton with preflight**

```python
# skills/repo_structure/run.py
"""repo-structure skill — extract structured facts from codebase + git history.

Stages:
  1. sample    - Build sampling manifest from gsd dossier
  2. hotspot  - Consume commit-extract/commit-semantic → hotspot_map
  3. extract  - LLM workers extract facts from 7-file dossier (section-routed)
  4. augment  - LLM workers adjudicate architecture claims vs repo evidence
  5. validate - Schema + deduplication + conflict detection
  6. baseline - Source-aware arbitration → facts.vN.yaml

Output:
  data/repo-structure/baseline/facts.vN.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.skill_runner import SkillRunner, run_skill
from src.harness_state import HarnessState, load_state, save_state
from .preflight import check as preflight_check


OUTPUT_BASE = Path("data/repo-structure")
BATCH_SIZE = 20


class RepoStructureRunner(SkillRunner):
    """Runner for repo-structure pipeline."""

    STAGES = ["sample", "hotspot", "extract", "augment", "validate", "baseline"]
    PIPELINE = "repo-structure"

    def __init__(self):
        super().__init__()
        self.gsd_root: str | None = None

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        method_name = f"_run_{stage}"
        method = getattr(self, method_name, None)
        if method is None:
            print(f"  Stage '{stage}' not yet implemented")
            return True  # Skip for now, mark complete
        return method(state)

    # -------------------------------------------------------------------------
    # Preflight
    # -------------------------------------------------------------------------

    def handle_check(self) -> int:
        """Run preflight checks and print structured report."""
        result = preflight_check()
        self._print_preflight_report(result)
        return 0 if result.ok else 1

    def _print_preflight_report(self, result) -> None:
        """Print preflight result in human-readable format."""
        if result.ok and not result.warnings:
            print("[repo-structure] preflight OK — all required inputs present")
            return

        print(f"[repo-structure] preflight: repo HEAD = {result.repo_head[:8]}")

        if result.missing:
            print("\n  MISSING (required):")
            for m in result.missing:
                print(f"    [{m.code}] {m.subject}: {m.message}")
                if m.producer:
                    print(f"               producer: {m.producer}")
                if m.suggestion:
                    print(f"               suggestion: {m.suggestion}")

        if result.invalid:
            print("\n  INVALID:")
            for m in result.invalid:
                print(f"    [{m.code}] {m.subject}: {m.message}")

        if result.warnings:
            print("\n  WARNINGS:")
            for w in result.warnings:
                print(f"    [{w.code}] {w.subject}: {w.message}")

        if result.missing or result.invalid:
            print("\n[repo-structure] preflight FAILED")
        else:
            print("\n[repo-structure] preflight OK (with warnings)")

    # -------------------------------------------------------------------------
    # Stage implementations (stubs — filled in Tasks 4-7)
    # -------------------------------------------------------------------------

    def _run_sample(self, state: HarnessState) -> bool:
        """Stage 1: Build sampling manifest from gsd dossier."""
        # TODO(Task 4): implement sample
        print("  [TODO] sample stage not yet implemented")
        return True

    def _run_hotspot(self, state: HarnessState) -> bool:
        """Stage 2: Consume commit-extract + commit-semantic → hotspot_map."""
        # TODO(Task 5): implement hotspot
        print("  [TODO] hotspot stage not yet implemented")
        return True

    def _run_extract(self, state: HarnessState) -> bool:
        """Stage 3: LLM workers extract facts from 7-file dossier."""
        # TODO(Task 5): implement extract
        print("  [TODO] extract stage not yet implemented")
        return True

    def _run_augment(self, state: HarnessState) -> bool:
        """Stage 4: LLM workers adjudicate arch claims vs repo evidence."""
        # TODO(Task 5): implement augment
        print("  [TODO] augment stage not yet implemented")
        return True

    def _run_validate(self, state: HarnessState) -> bool:
        """Stage 5: Schema checks, deduplication, conflict detection."""
        # TODO(Task 6): implement validate
        print("  [TODO] validate stage not yet implemented")
        return True

    def _run_baseline(self, state: HarnessState) -> bool:
        """Stage 6: Arbitration → facts.vN.yaml."""
        # TODO(Task 7): implement baseline
        print("  [TODO] baseline stage not yet implemented")
        return True

    # -------------------------------------------------------------------------
    # Override run to inject preflight
    # -------------------------------------------------------------------------

    def handle_run(self, remaining: list[str] | None = None) -> int:
        """Override to parse gsd-root arg and run preflight before execution."""
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--gsd-root", default=None)
        args, extra = parser.parse_known_args(argv)
        self.gsd_root = args.gsd_root

        # Run preflight first
        print("[repo-structure] Running preflight checks...")
        result = preflight_check()
        self._print_preflight_report(result)
        if not result.ok:
            print("\n[repo-structure] Aborting due to preflight failure.")
            return 1

        return super().handle_run(extra if extra else None)

    def main(self, argv: list[str] | None = None) -> int:
        """Extended main to support 'check' command."""
        import sys as _sys
        if argv is None:
            raw = _sys.argv[1:]
        else:
            raw = argv
        if len(raw) == 1 and isinstance(raw[0], str) and " " in raw[0]:
            raw = raw[0].split()

        parser = argparse.ArgumentParser(description="repo-structure skill")
        parser.add_argument("intent", nargs="?", default="run")
        args, extra = parser.parse_known_args(raw)

        if args.intent == "check":
            return self.handle_check()

        # Fall through to standard run/step/resume handlers
        handlers = {
            "status": self.handle_status,
            "reset": self.handle_reset,
            "step": self.handle_step,
            "resume": self.handle_resume,
            "run": lambda: self.handle_run(extra if extra else []),
        }
        handler = handlers.get(args.intent, handlers["run"])
        return handler()


if __name__ == "__main__":
    run_skill(RepoStructureRunner)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_repo_structure.py::test_run_check_command_fails_without_dependencies tests/test_repo_structure.py::test_handle_check_returns_zero_when_ok -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add skills/repo-structure/__init__.py skills/repo-structure/run.py
git commit -m "feat(repo-structure): add RepoStructureRunner skeleton with preflight integration"
```

---

## Task 4: Sample Stage

Implement the `sample` stage — reads the 7-file gsd dossier, builds a `DocSectionTask` manifest, and enriches with repo fallback probing.

**Files:**
- Modify: `skills/repo-structure/run.py` (add `_run_sample` body)
- Create: `tests/test_repo_structure.py` (add sample tests)

- [ ] **Step 1: Write the sample stage test**

```python
# tests/test_repo_structure.py (append)

def test_sample_produces_manifest(tmp_path, monkeypatch):
    """sample stage writes a manifest.yaml with section entries."""
    import sys
    from pathlib import Path
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)
    for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                  "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text("# fake content")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()
    success = runner._run_sample(state)
    assert success

    manifest = tmp_path / "data/repo-structure/sample/manifest.yaml"
    assert manifest.exists()
    data = __import__("yaml").safe_load(manifest.read_text())
    assert "sections" in data
    assert len(data["sections"]) >= 7  # At least one per gsd file


def test_sample_sections_cover_all_7_files(tmp_path, monkeypatch):
    """Each of the 7 gsd files gets at least one DocSectionTask entry."""
    import sys
    import yaml
    from pathlib import Path
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)
    for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                  "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text(f"# {fname}")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()
    runner._run_sample(state)

    manifest = yaml.safe_load(
        (tmp_path / "data/repo-structure/sample/manifest.yaml").read_text()
    )
    covered_files = {s["source_file"] for s in manifest["sections"]}
    expected = {f".planning/codebase/{fname}" for fname in [
        "STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
        "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]}
    assert expected.issubset(covered_files), f"Missing: {expected - covered_files}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_repo_structure.py::test_sample_produces_manifest tests/test_repo_structure.py::test_sample_sections_cover_all_7_files -v`
Expected: 2 FAIL (manifest doesn't exist yet)

- [ ] **Step 3: Implement sample stage**

Add to `skills/repo-structure/run.py`:

```python
    # At top of file, add import
    import yaml
    from dataclasses import dataclass, field
    from typing import Literal

    @dataclass
    class DocSectionTask:
        """A section unit for extract routing."""
        task_id: str
        source_file: str          # e.g. ".planning/codebase/STRUCTURE.md"
        section_title: str         # e.g. "Directory Layout"
        section_type: str          # e.g. "directory_listing", "architecture_layers"
        locator_type: str          # Expected locator type for this section
        content: str = ""          # Section text content (filled on demand)
        priority: int = 1          # 1=normal, 2=high
        routing_note: str = ""     # Why this section gets this locator_type

    # REQUIRED_GSD_FILES imported from preflight module (shared constant)
    from .preflight import REQUIRED_GSD_FILES

    # Section-to-locator mapping (per spec: section routing, not file batching)
    SECTION_LOCATOR_MAP = {
        # STRUCTURE.md
        ("STRUCTURE.md", "Directory Layout"): ("file_path", 2, "file_path"),
        ("STRUCTURE.md", "Key File Locations"): ("symbol", 2, "symbol"),
        ("STRUCTURE.md", "Naming Conventions"): ("file_path", 1, "file_path"),
        # ARCHITECTURE.md
        ("ARCHITECTURE.md", "Pattern Overview"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "Layers"): ("ast_pattern", 2, "ast_pattern"),
        ("ARCHITECTURE.md", "Data Flow"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "Key Abstractions"): ("symbol", 2, "symbol"),
        ("ARCHITECTURE.md", "Entry Points"): ("symbol", 2, "symbol"),
        ("ARCHITECTURE.md", "Error Handling"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "Cross-Cutting"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "State Management"): ("section_ref", 1, "section_ref"),
        # CONCERNS.md
        ("CONCERNS.md", "Tech Debt"): ("file_path", 2, "file_path"),
        ("CONCERNS.md", "Fragile Areas"): ("test_case", 2, "file_path+test_case"),
        ("CONCERNS.md", "Security"): ("file_path", 2, "file_path"),
        ("CONCERNS.md", "Performance"): ("file_path", 1, "file_path"),
        ("CONCERNS.md", "Test Coverage"): ("test_case", 1, "test_case"),
        # CONVENTIONS.md
        ("CONVENTIONS.md", None): ("section_ref", 1, "section_ref"),
        # INTEGRATIONS.md
        ("INTEGRATIONS.md", None): ("config_key", 1, "config_key"),
        # STACK.md
        ("STACK.md", "Technology Stack"): ("config_key", 1, "config_key"),
        ("STACK.md", "Runtime"): ("config_key", 1, "config_key"),
        # TESTING.md
        ("TESTING.md", None): ("test_case", 2, "test_case"),
    }

    def _run_sample(self, state: HarnessState) -> bool:
        """Build DocSectionTask manifest from 7-file gsd dossier."""
        print("  -> Building DocSectionTask manifest from gsd dossier")
        root = Path.cwd()
        gsd_dir = root / ".planning" / "codebase"

        tasks: list[DocSectionTask] = []
        task_id_counter = 0

        for fname in self.REQUIRED_GSD_FILES:
            fpath = gsd_dir / fname
            if not fpath.exists():
                print(f"  WARNING: {fpath} not found, skipping")
                continue

            text = fpath.read_text(encoding="utf-8")
            # Deterministic section split: split on ## headings
            sections = self._split_sections(text)

            for section_title, section_content in sections:
                task_id_counter += 1
                # Look up locator mapping
                key = (fname, section_title if section_title != fname else None)
                fallback_key = (fname, None)
                mapped = self.SECTION_LOCATOR_MAP.get(key) or self.SECTION_LOCATOR_MAP.get(fallback_key)

                if mapped:
                    locator_type, priority, routing_note = mapped
                else:
                    locator_type = "section_ref"
                    priority = 1
                    routing_note = "default routing"

                # Determine section_type from title
                section_type = section_title.lower().replace(" ", "_") if section_title else fname.lower().replace(".md", "")

                tasks.append(DocSectionTask(
                    task_id=f"doc-{task_id_counter:03d}",
                    source_file=f".planning/codebase/{fname}",
                    section_title=section_title or "(full file)",
                    section_type=section_type,
                    locator_type=locator_type,
                    priority=priority,
                    routing_note=routing_note,
                    content=section_content.strip(),
                ))

        # Write manifest
        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
        manifest_dir = OUTPUT_BASE / "sample"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.yaml"

        manifest_data = {
            "metadata": {
                "version": "v1",
                "total_sections": len(tasks),
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "gsd_root": str(gsd_dir),
            },
            "sections": [
                {
                    "task_id": t.task_id,
                    "source_file": t.source_file,
                    "section_title": t.section_title,
                    "section_type": t.section_type,
                    "locator_type": t.locator_type,
                    "routing_note": t.routing_note,
                    "priority": t.priority,
                    "content": t.content,  # Full content for extract workers
                }
                for t in tasks
            ],
        }

        __import__("yaml").dump(
            manifest_data,
            manifest_path.open("w", encoding="utf-8"),
            allow_unicode=True,
            default_flow_style=False,
        )
        print(f"  Wrote {len(tasks)} DocSectionTask entries -> {manifest_path}")
        self.add_artifact(state, str(manifest_path))
        return True

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split a markdown file into sections by ## headings."""
        import re
        sections = []
        # Split on ## headings (not # which is title)
        parts = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # First line is the heading
            lines = part.splitlines()
            if lines and lines[0].startswith("## "):
                title = lines[0][3:].strip()
                content = "\n".join(lines[1:]).strip()
            else:
                title = part.split("\n")[0][:50]
                content = part
            sections.append((title, content))
        return sections
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_repo_structure.py::test_sample_produces_manifest tests/test_repo_structure.py::test_sample_sections_cover_all_7_files -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/repo-structure/run.py tests/test_repo_structure.py
git commit -m "feat(repo-structure): implement sample stage with DocSectionTask manifest"
```

---

## Task 5: Extract + Augment Worker Prompts

Create the LLM worker prompt templates for extract and augment stages. These are loaded by `run.py` and used when spawning worker agents.

**Files:**
- Create: `skills/repo-structure/prompts/extract_codebase.md`
- Create: `skills/repo-structure/prompts/augment_architect.md`

- [ ] **Step 1: Write `extract_codebase.md` prompt**

Content from `docs/superpowers/specs/2026-03-22-extract_codebase.md`:

```markdown
# Extract Worker — Codebase Fact Extraction

You are an extract worker. Your job is to read a **section of a gsd codebase dossier** and produce atomic, evidence-bound fact entries.

## Input

You receive one `DocSectionTask` at a time:

```yaml
task_id: "doc-001"
source_file: ".planning/codebase/ARCHITECTURE.md"
section_title: "Key Abstractions"
section_type: "key_abstractions"
locator_type: "symbol"
routing_note: "symbol"
priority: 2
content: |
  ## Key Abstractions
  ...
```

## Your Task

Extract **atomic fact entries** from this section.

Each fact must be:
- Explicitly supported by the section text
- Attached to a concrete `locator` using the provided `locator_type`
- Grounded in the provided section (do not infer implementation details not stated)

## Output Format

Output **YAML list** of fact entries:

```yaml
facts:
  - fact_id: "<uuid-v4>"
    fact_type: module_role | dependency_rule | boundary_constraint | pattern_usage | convention | invariant | hotspot_signal
    domain: "<problem domain, inferred from content>"
    statement: "<human-readable fact>"
    confidence: confirmed | uncertain | contradicted
    status: active | conflicted | filtered
    repo_snapshot_commit: "<CURRENT_HEAD>"
    source: codebase
    evidence:
      - source_type: codebase
        file_path: "<from source_file>"
        locator_type: "<from task.locator_type>"
        locator: "<concrete value matching locator_type>"
        stable_ref: "<symbol_signature_hash or file_blob_sha>"
        rationale: "<why this evidence supports the statement>"
```

## Section-to-Locator Routing Policy

| Section | `locator_type` | Example `locator` |
|---------|---------------|-------------------|
| STRUCTURE.md / Directory Layout | `file_path` | `src/hermes/operator_registry.py` |
| STRUCTURE.md / Key File Locations | `symbol` | `REGISTER_OPERATOR_BY_OPS` |
| ARCHITECTURE.md / Layers | `ast_pattern` | `class.*\(.*\)` (layer pattern) |
| ARCHITECTURE.md / Key Abstractions | `symbol` | `OperatorRegistry` |
| ARCHITECTURE.md / Entry Points | `symbol` | `dispatch_event` |
| CONCERNS.md / Tech Debt | `file_path` | `src/legacy/parser_v1.py` |
| CONCERNS.md / Fragile Areas | `file_path+test_case` | `src/parser.py`, `test_parser_edge_cases` |
| CONCERNS.md / Security | `file_path` | `src/auth/token_handler.py` |
| STACK.md / Technology Stack | `config_key` | `max_workers`, `timeout_seconds` |
| TESTING.md | `test_case` | `test_integration_flow` |
| CONVENTIONS.md | `section_ref` | `CONVENTIONS.md#naming` |
| INTEGRATIONS.md | `config_key` | `DATABASE_URL`, `API_KEY` |

## Rules

1. **Output unit is fact entry, NOT prose summary.** No paragraphs summarizing the whole section.
2. **Prefer concrete facts** over generic statements. "The `OperatorRegistry` class provides registration for operators" is good. "The codebase has good architecture" is not.
3. **Use the exact `locator_type`** from the task. Do not invent new types.
4. **Generate stable_ref** using: `symbol_signature_hash(symbol)` for symbols, or `blob_sha(content)` for file-based refs. If you cannot compute, use the literal string value as fallback.
5. **Confidence**: `confirmed` if the section text explicitly states the fact. `uncertain` if it is implied or likely. `contradicted` only if the section itself notes a discrepancy.
6. **Do not hallucinate** implementation details not in the section text.
7. **Atomic**: one fact = one subject + one predicate + one object (or equivalent). Split compound statements.

## Process

1. Read the section content carefully
2. Identify fact-bearing sentences/statements
3. For each fact, determine: subject, predicate, object
4. Assign fact_type based on category
5. Attach evidence with correct locator_type and locator
6. Output as YAML
```

- [ ] **Step 2: Write `augment_architect.md` prompt**

Content from `docs/superpowers/specs/2026-03-22-augment_architect.md`:

```markdown
# Augment Worker — Architecture Claim Adjudication

You are an augment worker. Your job is to judge whether architecture claims from `docs/ARCHITECTURE.md` are supported by the provided repo evidence candidates.

## Two-Phase Process

### Phase 1 (Python — already done)

Python tooling has already collected candidate evidence:

```json
{
  "claim_id": "arch-001",
  "claim_text": "The system enforces layer isolation: service orchestration must not depend on lower-layer primitives.",
  "stable_refs": ["src/layers/primitives.py"],
  "search_results": [
    {"type": "symbol", "ref": "PrimitiveOps", "found": true, "file": "src/layers/primitives.py"},
    {"type": "symbol", "ref": "Orchestrator", "found": true, "file": "src/orchestrate.py"}
  ],
  "test_evidence": [],
  "comment_evidence": [],
  "misses": []
}
```

### Phase 2 (You — this prompt)

You receive: claim + candidate_evidence.json → adjudicate.

## Your Task

Judge whether each claim is:

| Status | Meaning |
|--------|---------|
| `evidence_backed` | Direct stable evidence exists in the repo |
| `weakly_backed` | Only indirect or partial evidence |
| `gap` | No stable supporting evidence found |
| `drift` | Repo contradicts the claim |

## Rules

1. **Prefer direct implementation evidence over comments.** Comments are weaker evidence.
2. **Mark as `gap`** if no stable evidence exists — do not assume the claim is true.
3. **Mark as `drift`** if repo evidence shows the claim is violated.
4. **Attach `stable_ref`** from the most authoritative matched evidence.
5. **`gap` and `drift` are not failures.** They are governance signals. Report them faithfully.
6. **Be conservative.** If evidence is ambiguous, prefer `weakly_backed` over `evidence_backed`.

## Output Format

```yaml
adjudications:
  - claim_id: "<from input>"
    claim_text: "<exact text>"
    status: evidence_backed | weakly_backed | gap | drift
    matched_evidence:
      - stable_ref: "<symbol_signature_hash or file_blob_sha>"
        rationale: "<why this evidence matches the claim>"
        strength: strong | medium | weak
    unmatched_claims:
      - "<aspect of claim not supported by evidence>"
    notes: "<any additional observations>"
    recommendation: accept | modify | supplement | reject
```

## Process

1. Read the claim text carefully
2. Review each candidate evidence item
3. Assess whether evidence directly supports the claim
4. Determine the appropriate status
5. Attach the strongest supporting stable_ref
6. Make a recommendation
```

- [ ] **Step 3: Commit**

```bash
git add skills/repo-structure/prompts/extract_codebase.md skills/repo-structure/prompts/augment_architect.md
git commit -m "feat(repo-structure): add extract and augment LLM worker prompts"
```

---

## Task 6: Extract + Augment Stages

Implement the `_run_extract` and `_run_augment` methods in `run.py`. Both use worker prompts from Task 5. Extract is section-routed (not file-batched). Augment is two-phase (Python collection + LLM adjudication).

**Files:**
- Modify: `skills/repo-structure/run.py`

- [ ] **Step 1: Write extract stage test**

```python
# tests/test_repo_structure.py (append)

def test_extract_produces_codebase_map(tmp_path, monkeypatch):
    """extract stage writes codebase_map.vN.yaml with fact entries."""
    import sys, yaml
    from pathlib import Path
    import tempfile

    # Set up minimal environment
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)

    # Write minimal gsd files with extractable facts
    (gsd_dir / "ARCHITECTURE.md").write_text(
        "## Key Abstractions\n\nThe `OperatorRegistry` class provides registration "
        "for operators using the `REGISTER_OPERATOR_BY_OPS` decorator.\n"
    )
    for fname in ["STRUCTURE.md", "CONCERNS.md", "CONVENTIONS.md",
                  "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text(f"## Section\n\nMinimal content for {fname}.\n")

    # Create sample manifest first
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()

    # Run sample first (extract depends on manifest)
    runner._run_sample(state)

    # Now run extract (mock LLM — worker_regenerate is used for fact extraction)
    success = runner._run_extract(state)
    assert success

    maps_dir = tmp_path / "data/repo-structure/maps"
    assert maps_dir.exists()
    maps = list(maps_dir.glob("codebase_map.v*.yaml"))
    assert len(maps) >= 1, f"Expected at least 1 codebase_map, found {list(maps_dir.glob('*'))}"

    data = yaml.safe_load(maps[0].read_text())
    assert "facts" in data, f"Missing 'facts' key in {maps[0]}"
    assert "metadata" in data, f"Missing 'metadata' key in {maps[0]}"
    assert len(data["facts"]) > 0, f"Expected non-empty facts but got {len(data['facts'])} facts"

    # Verify fact structure: each fact has evidence with locator
    for fact in data["facts"]:
        assert "fact_id" in fact
        assert "fact_type" in fact
        assert "evidence" in fact
        assert len(fact["evidence"]) > 0, f"Fact {fact.get('fact_id')} has no evidence"
        ev = fact["evidence"][0]
        assert "locator_type" in ev, f"Evidence missing locator_type in {fact['fact_id']}"
        assert "locator" in ev, f"Evidence missing locator in {fact['fact_id']}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repo_structure.py::test_extract_produces_codebase_map -v`
Expected: FAIL (extract stage not implemented)

- [ ] **Step 3: Implement extract stage**

Add to `run.py`:

```python
    # Add to imports at top
    import uuid

    # Add DocSectionTask dataclass (if not already present from Task 4)

    def _run_extract(self, state: HarnessState) -> bool:
        """Extract facts from 7-file dossier using section-routed worker prompts."""
        print("  -> Running extract stage")

        # Load sample manifest
        manifest_path = OUTPUT_BASE / "sample" / "manifest.yaml"
        if not manifest_path.exists():
            print(f"  ERROR: sample manifest not found at {manifest_path}")
            print(f"  Run 'repo-structure --stage sample' first")
            return False

        manifest = yaml.safe_load(manifest_path.read_text())
        sections = manifest.get("sections", [])

        # Batch sections into worker batches
        batches = self._batch_sections(sections, BATCH_SIZE)
        print(f"  Processing {len(sections)} sections in {len(batches)} batch(es)")

        # Load worker prompt
        prompt_path = Path(__file__).parent / "prompts" / "extract_codebase.md"
        prompt_template = prompt_path.read_text() if prompt_path.exists() else ""

        all_facts: list[dict] = []
        for batch_idx, batch in enumerate(batches):
            print(f"  Batch {batch_idx + 1}/{len(batches)} ({len(batch)} sections)...")
            facts = self._spawn_extract_worker(batch, prompt_template)
            all_facts.extend(facts)

        # Write codebase_map
        version = self._next_version("codebase_map")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"codebase_map.{version}.yaml"

        head = self._get_repo_head()
        data = {
            "metadata": {
                "version": version,
                "total_facts": len(all_facts),
                "repo_snapshot_commit": head,
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "prompt": "extract_codebase.md",
            },
            "facts": all_facts,
        }
        yaml.dump(data, out_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)
        print(f"  Wrote {len(all_facts)} facts -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _batch_sections(self, sections: list[dict], batch_size: int) -> list[list[dict]]:
        """Split sections into batches."""
        return [sections[i:i+batch_size] for i in range(0, len(sections), batch_size)]

    def _spawn_extract_worker(self, batch: list[dict], prompt_template: str) -> list[dict]:
        """Spawn extract worker for a batch of DocSectionTasks.

        When COMMIT_SEMANTIC_USE_TASK_AGENTS=1, spawns a real Task agent.
        Otherwise uses local heuristic extraction (for CLI/testing).
        """
        import os as _os
        use_task = _os.environ.get("COMMIT_SEMANTIC_USE_TASK_AGENTS", "").lower() in ("1", "true", "yes")

        if use_task:
            # Real Task agent — implemented via SKILL.md orchestration
            # This is a no-op here; the main agent handles Task calls
            return []

        # Local fallback: heuristic extraction per section
        facts: list[dict] = []
        head = self._get_repo_head()

        for section in batch:
            section_facts = self._extract_facts_from_section(section, head)
            facts.extend(section_facts)

        return facts

    def _extract_facts_from_section(self, section: dict, head: str) -> list[dict]:
        """Heuristic fact extraction from a single DocSectionTask section.

        Mirrors what an LLM would extract given the extract_codebase.md prompt.
        """
        locator_type = section.get("locator_type", "section_ref")
        source_file = section.get("source_file", "")
        content = section.get("content", "")
        section_type = section.get("section_type", "")

        if not content or len(content.strip()) < 20:
            return []

        facts: list[dict] = []
        import re

        # Extract symbol references (function/class names)
        symbols = re.findall(r'`([A-Z][a-zA-Z0-9_]+)`', content)
        symbols += re.findall(r'class\s+([A-Z][a-zA-Z0-9_]+)', content)
        symbols += re.findall(r'def\s+([a-z][a-zA-Z0-9_]+)', content)
        symbols = list(dict.fromkeys(symbols))  # Dedupe preserving order

        # Extract file paths
        file_paths = re.findall(r'`([a-z_/]+\.py)`', content)
        file_paths += re.findall(r'(?:src|tests|lib)/[a-z_/]+\.py', content)
        file_paths = list(dict.fromkeys(file_paths))

        # Extract config keys
        config_keys = re.findall(r'`([a-z_][a-zA-Z0-9_]*)`', content)
        config_keys = [k for k in config_keys if k not in symbols]
        config_keys = list(dict.fromkeys(config_keys))

        # Build facts based on locator_type
        if locator_type == "symbol" and symbols:
            for sym in symbols[:5]:  # Limit per section
                facts.append({
                    "fact_id": str(uuid.uuid4()),
                    "fact_type": "module_role",
                    "domain": section_type,
                    "statement": f"{sym} is defined in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "symbol",
                        "locator": sym,
                        "stable_ref": f"symbol:{sym}",
                        "rationale": f"Extracted from {section.get('section_title', 'unknown section')}",
                    }],
                })

        elif locator_type == "file_path" and file_paths:
            for fp in file_paths[:5]:
                facts.append({
                    "fact_id": str(uuid.uuid4()),
                    "fact_type": "pattern_usage",
                    "domain": section_type,
                    "statement": f"{fp} is referenced in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "file_path",
                        "locator": fp,
                        "stable_ref": f"file:{fp}",
                        "rationale": f"Referenced in {section.get('section_title', 'section')}",
                    }],
                })

        elif locator_type == "config_key" and config_keys:
            for ck in config_keys[:5]:
                facts.append({
                    "fact_id": str(uuid.uuid4()),
                    "fact_type": "dependency_rule",
                    "domain": section_type,
                    "statement": f"Configuration key '{ck}' is used in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "config_key",
                        "locator": ck,
                        "stable_ref": f"config:{ck}",
                        "rationale": f"Mentioned in {section.get('section_title', 'section')}",
                    }],
                })

        elif locator_type == "section_ref":
            # Generic section-level fact
            title = section.get("section_title", "section")
            facts.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "convention",
                "domain": section_type,
                "statement": f"{source_file} contains a '{title}' section",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": head,
                "source": "codebase",
                "evidence": [{
                    "source_type": "codebase",
                    "file_path": source_file,
                    "locator_type": "section_ref",
                    "locator": f"{source_file}#{title.lower().replace(' ', '-')}",
                    "stable_ref": f"section:{source_file}:{title}",
                    "rationale": f"Section '{title}' exists in {source_file}",
                }],
            })

                elif locator_type == "ast_pattern":
            # AST pattern locator — extract class/function patterns from architecture descriptions
            ast_patterns = re.findall(r'class\s+(\w+)', content)
            ast_patterns += re.findall(r'function\s+(\w+)', content)
            for pattern in ast_patterns[:5]:
                facts.append({
                    "fact_id": str(uuid.uuid4()),
                    "fact_type": "pattern_usage",
                    "domain": section_type,
                    "statement": f"Layer pattern '{pattern}' is defined in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "ast_pattern",
                        "locator": pattern,
                        "stable_ref": f"pattern:{pattern}",
                        "rationale": f"Pattern found in {section.get('section_title', 'section')}",
                    }],
                })

        elif "test_case" in locator_type:
            # Extract test function names
            test_names = re.findall(r'(?:def |test_)([a-z_][a-zA-Z0-9_]*)', content)
            test_names = [t for t in test_names if "test" in t.lower()]
            for tn in test_names[:5]:
                facts.append({
                    "fact_id": str(uuid.uuid4()),
                    "fact_type": "invariant",
                    "domain": section_type,
                    "statement": f"Test case '{tn}' validates behavior in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "test_case",
                        "locator": tn,
                        "stable_ref": f"test:{tn}",
                        "rationale": f"Test found in {section.get('section_title', 'section')}",
                    }],
                })

        return facts

    def _run_augment(self, state: HarnessState) -> bool:
        """Two-phase architecture augmentation: Python collection + LLM adjudication."""
        print("  -> Running augment stage")

        arch_doc = Path("docs/ARCHITECTURE.md")
        if not arch_doc.exists():
            print("  WARNING: docs/ARCHITECTURE.md not found — emitting empty augment")
            # Write empty placeholder
            version = self._next_version("architect_augment")
            maps_dir = OUTPUT_BASE / "maps"
            maps_dir.mkdir(parents=True, exist_ok=True)
            out_path = maps_dir / f"architect_augment.{version}.yaml"
            head = self._get_repo_head()
            yaml.dump({
                "metadata": {"version": version, "repo_snapshot_commit": head,
                             "generated_at": __import__("datetime").datetime.now().isoformat(),
                             "status": "skipped_no_arch_doc"},
                "adjudications": [],
            }, out_path.open("w", encoding="utf-8"),
                      allow_unicode=True, default_flow_style=False)
            self.add_artifact(state, str(out_path))
            return True

        # Phase 1: Python evidence collection (deterministic grep/search)
        print("  Phase 1: collecting candidate evidence...")
        evidence = self._collect_evidence_candidates(arch_doc)

        # Phase 2: LLM adjudication (worker prompt)
        print("  Phase 2: adjudicating claims...")
        prompt_path = Path(__file__).parent / "prompts" / "augment_architect.md"
        prompt_template = prompt_path.read_text() if prompt_path.exists() else ""

        adjudicated = self._spawn_augment_worker(evidence, prompt_template)

        version = self._next_version("architect_augment")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"architect_augment.{version}.yaml"
        head = self._get_repo_head()
        yaml.dump({
            "metadata": {"version": version, "repo_snapshot_commit": head,
                         "generated_at": __import__("datetime").datetime.now().isoformat(),
                         "status": "complete"},
            "adjudications": adjudicated,
        }, out_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)
        print(f"  Wrote {len(adjudicated)} adjudicated claims -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _collect_evidence_candidates(self, arch_doc: Path) -> dict:
        """Phase 1: Collect candidate evidence for architecture claims."""
        import subprocess, json, re
        root = Path.cwd()

        # Extract claims from arch doc (## headings = claim boundaries)
        text = arch_doc.read_text(encoding="utf-8")
        claims = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)

        candidate_evidence: list[dict] = []
        claim_id_counter = 0

        for section in claims:
            section = section.strip()
            if not section or len(section) < 30:
                continue
            lines = section.splitlines()
            title = lines[0][3:].strip() if lines and lines[0].startswith("## ") else "unknown"
            content = "\n".join(lines[1:]).strip()

            claim_id_counter += 1
            claim_id = f"arch-{claim_id_counter:03d}"

            # Extract symbols from claim text
            symbols = re.findall(r'`([A-Z][a-zA-Z0-9_]+)`', content)
            symbols += re.findall(r'`([a-z_][a-zA-Z0-9_]+)`', content)
            symbols = list(dict.fromkeys(symbols))[:5]

            # Grep for each symbol in the repo
            search_results = []
            for sym in symbols:
                try:
                    r = subprocess.run(
                        ["rg", "-n", "--type", "py", sym, str(root / "src")],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode == 0:
                        matches = r.stdout.strip().splitlines()[:3]
                        search_results.append({
                            "type": "symbol", "ref": sym, "found": True,
                            "matches": matches
                        })
                except Exception:
                    pass

            candidate_evidence.append({
                "claim_id": claim_id,
                "claim_text": content[:500],
                "claim_title": title,
                "stable_refs": symbols,
                "search_results": search_results,
            })

        return {"claims": candidate_evidence, "total": len(candidate_evidence)}

    def _spawn_augment_worker(self, evidence: dict, prompt_template: str) -> list[dict]:
        """Spawn augment worker for claim adjudication.

        When COMMIT_SEMANTIC_USE_TASK_AGENTS=1, spawns a real Task agent.
        Otherwise uses local heuristic adjudication.
        """
        import os as _os
        use_task = _os.environ.get("COMMIT_SEMANTIC_USE_TASK_AGENTS", "").lower() in ("1", "true", "yes")

        if use_task:
            return []  # Real agent handled via SKILL.md

        # Local fallback: heuristic adjudication
        adjudicated = []
        for claim in evidence.get("claims", []):
            search_results = claim.get("search_results", [])
            num_found = sum(1 for r in search_results if r.get("found"))

            if num_found >= 2:
                status = "evidence_backed"
            elif num_found == 1:
                status = "weakly_backed"
            elif search_results:
                status = "gap"
            else:
                status = "gap"

            # Check for drift: if claim says "must" but evidence shows violation
            claim_text = claim.get("claim_text", "")
            has_must = "must" in claim_text.lower() or "shall" in claim_text.lower()
            has_negation = "not" in claim_text.lower() or "never" in claim_text.lower()
            if has_must and not has_negation and num_found == 0:
                status = "drift"

            stable_refs = []
            for r in search_results:
                if r.get("found"):
                    stable_refs.append({
                        "stable_ref": f"symbol:{r['ref']}",
                        "rationale": f"Found '{r['ref']}' in {r['matches'][0] if r['matches'] else 'repo'}",
                        "strength": "strong" if num_found >= 2 else "medium",
                    })

            adjudicated.append({
                "claim_id": claim["claim_id"],
                "claim_text": claim["claim_text"][:300],
                "status": status,
                "matched_evidence": stable_refs,
                "unmatched_claims": [],
                "notes": f"{num_found} evidence matches found",
                "recommendation": "accept" if status == "evidence_backed" else "supplement",
            })

        return adjudicated

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_repo_head(self) -> str:
        """Get current HEAD commit."""
        import subprocess
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=True)
            return r.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _next_version(self, artifact_name: str) -> str:
        """Get next version number for an artifact."""
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(maps_dir.glob(f"{artifact_name}.v*.yaml"))
        if not existing:
            return "v0"
        last = existing[-1].stem.split(".")[-1]  # "codebase_map.v2" -> "v2"
        num = int(last[1:]) + 1
        return f"v{num}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repo_structure.py::test_extract_produces_codebase_map -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/repo-structure/run.py tests/test_repo_structure.py
git commit -m "feat(repo-structure): implement extract and augment stages with two-phase augmentation"
```

---

## Task 7: Hotspot Stage

Implement the `hotspot` stage — consumes `commit-extract` + `commit-semantic` output to produce `hotspot_map.vN.yaml`.

**Files:**
- Modify: `skills/repo-structure/run.py`

- [ ] **Step 1: Write hotspot stage test**

```python
# tests/test_repo_structure.py (append)

def test_hotspot_consumes_commit_semantic(tmp_path, monkeypatch):
    """hotspot stage reads commit-extract + commit-semantic and writes hotspot_map."""
    import sys, yaml
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    (tmp_path / "data/commit-semantic/patterns").mkdir(parents=True)

    # Write minimal commit-extract artifact
    import yaml as _yaml
    (tmp_path / "data/commit-extract/2025-01.yaml").write_text(
        _yaml.dump({"metadata": {"month": "2025-01"}, "commits": []})
    )
    # Write minimal commit-semantic pattern
    (tmp_path / "data/commit-semantic/patterns/canonical.yaml").write_text(
        _yaml.dump({"patterns": []})
    )

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()
    success = runner._run_hotspot(state)
    assert success

    maps_dir = tmp_path / "data/repo-structure/maps"
    assert maps_dir.exists()
    hotspot_maps = list(maps_dir.glob("hotspot_map.v*.yaml"))
    assert len(hotspot_maps) >= 1, f"Expected hotspot_map, found: {list(maps_dir.glob('*'))}"

    data = yaml.safe_load(hotspot_maps[0].read_text())
    assert "metadata" in data
    assert "facts" in data or "hotspots" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repo_structure.py::test_hotspot_consumes_commit_semantic -v`
Expected: FAIL (hotspot not implemented)

- [ ] **Step 3: Implement hotspot stage**

Add to `run.py`:

```python
    def _run_hotspot(self, state: HarnessState) -> bool:
        """Consume commit-extract + commit-semantic → hotspot_map."""
        print("  -> Running hotspot stage")

        # Load commit-extract monthly files
        commit_extract_dir = Path("data/commit-extract")
        if not commit_extract_dir.exists():
            print(f"  ERROR: commit-extract output not found at {commit_extract_dir}")
            return False

        monthly_files = sorted(commit_extract_dir.glob("????-??.yaml"))
        print(f"  Found {len(monthly_files)} monthly commit files")

        # Load commit-semantic patterns
        patterns_dir = Path("data/commit-semantic/patterns")
        patterns: list[dict] = []
        if patterns_dir.exists():
            for pf in patterns_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(pf.read_text())
                    if "patterns" in data:
                        patterns.extend(data["patterns"])
                except Exception as e:
                    print(f"  WARNING: could not load {pf}: {e}")

        # Aggregate hotspot signals
        hotspots = self._aggregate_hotspots(monthly_files, patterns)

        version = self._next_version("hotspot_map")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"hotspot_map.{version}.yaml"
        head = self._get_repo_head()

        yaml.dump({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "monthly_files": [str(f.relative_to(Path.cwd())) for f in monthly_files],
                "total_patterns": len(patterns),
            },
            "facts": hotspots,
        }, out_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)

        print(f"  Wrote {len(hotspots)} hotspot facts -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _aggregate_hotspots(self, monthly_files: list[Path], patterns: list[dict]) -> list[dict]:
        """Aggregate commit-extract data and commit-semantic patterns into hotspot facts."""
        from collections import defaultdict
        import yaml

        # Count commits per module/file across all months
        module_commit_count: dict[str, int] = defaultdict(int)
        module_files: dict[str, set[str]] = defaultdict(set)

        for mf in monthly_files:
            try:
                data = yaml.safe_load(mf.read_text())
                for commit in data.get("commits", []):
                    for f in commit.get("files", []):
                        # Extract module from file path
                        module = str(f).split("/")[0] if "/" in str(f) else "root"
                        module_commit_count[module] += 1
                        module_files[module].add(str(f))
            except Exception:
                pass

        hotspots: list[dict] = []

        # Top-N hotspot modules by commit frequency
        top_modules = sorted(module_commit_count.items(), key=lambda x: -x[1])[:10]
        for rank, (module, count) in enumerate(top_modules):
            if count < 2:
                continue
            hotspots.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "hotspot_signal",
                "domain": "hotspot",
                "statement": f"Module '{module}' appears in {count} commits — high change frequency",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": self._get_repo_head(),
                "source": "hotspot",
                "evidence": [{
                    "source_type": "hotspot",
                    "file_path": f"data/commit-extract/*.yaml",
                    "locator_type": "file_path",
                    "locator": module,
                    "stable_ref": f"module:{module}",
                    "rationale": f"Module '{module}' touched in {count} commits across {mf.parent.name for mf in monthly_files}",
                }],
                "hotspot_rank": rank + 1,
                "commit_count": count,
                "files": sorted(module_files[module]),
            })

        # Add pattern-based hotspots from commit-semantic
        for pattern in patterns[:10]:
            hotspots.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "hotspot_signal",
                "domain": "semantic_pattern",
                "statement": f"Recurring pattern: {pattern.get('description', pattern.get('pattern_id', 'unknown'))}",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": self._get_repo_head(),
                "source": "hotspot",
                "evidence": [{
                    "source_type": "hotspot",
                    "file_path": "data/commit-semantic/patterns/",
                    "locator_type": "section_ref",
                    "locator": pattern.get("pattern_id", ""),
                    "stable_ref": f"pattern:{pattern.get('pattern_id', 'unknown')}",
                    "rationale": "From commit-semantic pattern extraction",
                }],
            })

        return hotspots
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repo_structure.py::test_hotspot_consumes_commit_semantic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/repo-structure/run.py tests/test_repo_structure.py
git commit -m "feat(repo-structure): implement hotspot stage from commit-extract/commit-semantic"
```

---

## Task 8: Validate + Baseline Stages

Implement the final two stages: `validate` (schema checks, deduplication, conflict detection) and `baseline` (source-aware arbitration → `facts.vN.yaml`).

**Files:**
- Modify: `skills/repo-structure/run.py`

- [ ] **Step 1: Write validate + baseline tests**

```python
# tests/test_repo_structure.py (append)

def test_validate_merges_three_maps(tmp_path, monkeypatch):
    """validate stage reads all 3 maps and writes validated + conflicts."""
    import sys, yaml
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    maps_dir = tmp_path / "data/repo-structure/maps"
    maps_dir.mkdir(parents=True)

    # Write minimal maps
    for map_name, facts in [
        ("hotspot_map.v0", [{"fact_id": "h1", "fact_type": "hotspot_signal",
                              "statement": "module X changes often",
                              "confidence": "confirmed", "status": "active",
                              "repo_snapshot_commit": "abc", "source": "hotspot",
                              "evidence": []}]),
        ("codebase_map.v0", [{"fact_id": "c1", "fact_type": "module_role",
                               "statement": "src/X/ is a core module",
                               "confidence": "confirmed", "status": "active",
                               "repo_snapshot_commit": "abc", "source": "codebase",
                               "evidence": []}]),
        ("architect_augment.v0", [{"claim_id": "a1", "status": "evidence_backed",
                                    "matched_evidence": []}]),
    ]:
        yaml.dump({"metadata": {"version": "v0"}, "facts": facts,
                   "adjudications": facts if "augment" in map_name else []},
                   (maps_dir / f"{map_name}.yaml").open("w"))

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()
    success = runner._run_validate(state)
    assert success

    facts_dir = tmp_path / "data/repo-structure/facts"
    assert facts_dir.exists()
    assert (facts_dir / "validated.v0.yaml").exists()


def test_baseline_produces_versioned_facts(tmp_path, monkeypatch):
    """baseline stage writes facts.vN.yaml as sole source-of-truth."""
    import sys, yaml
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    maps_dir = tmp_path / "data/repo-structure/maps"
    maps_dir.mkdir(parents=True)
    facts_dir = tmp_path / "data/repo-structure/facts"
    facts_dir.mkdir(parents=True)

    # Write minimal validated facts
    yaml.dump({
        "metadata": {"version": "v0"},
        "facts": [{"fact_id": "f1", "fact_type": "module_role",
                   "statement": "Test fact", "confidence": "confirmed",
                   "status": "active", "repo_snapshot_commit": "abc",
                   "source": "codebase", "evidence": []}],
        "conflicts": [],
    }, (facts_dir / "validated.v0.yaml").open("w"))

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()
    success = runner._run_baseline(state)
    assert success

    baseline_dir = tmp_path / "data/repo-structure/baseline"
    baseline_files = sorted(baseline_dir.glob("facts.v*.yaml"))
    assert len(baseline_files) >= 1

    data = yaml.safe_load(baseline_files[0].read_text())
    assert "facts" in data
    assert "metadata" in data
    assert "conflicts" in data
    assert data["metadata"]["version"].startswith("v")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_repo_structure.py::test_validate_merges_three_maps tests/test_repo_structure.py::test_baseline_produces_versioned_facts -v`
Expected: 2 FAIL (stages not implemented)

- [ ] **Step 3: Implement validate stage**

Add to `run.py`:

```python
    def _run_validate(self, state: HarnessState) -> bool:
        """Validate: schema check, deduplicate, detect conflicts from 3 maps."""
        print("  -> Running validate stage")

        maps_dir = OUTPUT_BASE / "maps"
        if not maps_dir.exists():
            print(f"  ERROR: maps directory not found: {maps_dir}")
            return False

        # Load all three source maps
        hotspot_map = self._load_latest_map(maps_dir, "hotspot_map")
        codebase_map = self._load_latest_map(maps_dir, "codebase_map")
        architect_aug = self._load_latest_map(maps_dir, "architect_augment")

        all_facts: list[dict] = []
        all_facts.extend(codebase_map.get("facts", []))
        all_facts.extend(hotspot_map.get("facts", []))
        # Architect augment facts derived from adjudicated claims
        for adj in architect_aug.get("adjudications", []):
            if adj.get("status") in ("evidence_backed", "weakly_backed"):
                all_facts.append({
                    "fact_id": adj.get("claim_id", str(uuid.uuid4())),
                    "fact_type": "boundary_constraint",
                    "domain": "architecture",
                    "statement": adj.get("claim_text", "")[:200],
                    "confidence": "confirmed" if adj.get("status") == "evidence_backed" else "uncertain",
                    "status": "active",
                    "repo_snapshot_commit": architect_aug.get("metadata", {}).get("repo_snapshot_commit", ""),
                    "source": "architect",
                    "evidence": adj.get("matched_evidence", []),
                })

        # Step 1: Schema validation (basic checks)
        validated, invalid = self._schema_validate(all_facts)
        print(f"  Schema: {len(validated)} valid, {len(invalid)} invalid")

        # Step 2: Deduplication
        deduplicated, duplicates = self._deduplicate(validated)
        print(f"  Deduplication: {len(deduplicated)} unique, {len(duplicates)} duplicates removed")

        # Step 3: Conflict detection
        conflicts = self._detect_conflicts(deduplicated)
        print(f"  Conflict detection: {len(conflicts)} conflicts preserved")

        version = self._next_version("validated")
        facts_dir = OUTPUT_BASE / "facts"
        facts_dir.mkdir(parents=True, exist_ok=True)
        validated_path = facts_dir / f"validated.{version}.yaml"
        conflicts_path = facts_dir / f"conflicts.{version}.yaml"
        head = self._get_repo_head()

        yaml.dump({
            "metadata": {"version": version, "repo_snapshot_commit": head,
                         "generated_at": __import__("datetime").datetime.now().isoformat(),
                         "total_validated": len(deduplicated),
                         "total_conflicts": len(conflicts)},
            "facts": deduplicated,
        }, validated_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)

        yaml.dump({
            "metadata": {"version": version, "repo_snapshot_commit": head,
                         "generated_at": __import__("datetime").datetime.now().isoformat()},
            "conflicts": conflicts,
        }, conflicts_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)

        print(f"  Wrote {len(deduplicated)} validated facts -> {validated_path}")
        print(f"  Wrote {len(conflicts)} conflicts -> {conflicts_path}")
        self.add_artifact(state, str(validated_path))
        self.add_artifact(state, str(conflicts_path))
        return True

    def _load_latest_map(self, maps_dir: Path, prefix: str) -> dict:
        """Load the latest version of a map artifact."""
        maps = sorted(maps_dir.glob(f"{prefix}.v*.yaml"), reverse=True)
        if maps:
            return yaml.safe_load(maps[0].read_text())
        return {"metadata": {}, "facts": []}

    VALID_FACT_TYPES = {
        "module_role", "dependency_rule", "boundary_constraint",
        "pattern_usage", "convention", "invariant", "hotspot_signal",
    }

    def _schema_validate(self, facts: list[dict]) -> tuple[list[dict], list[dict]]:
        """Schema validation: required fields + fact_type enum + evidence shape."""
        required_fields = {"fact_id", "fact_type", "statement", "source",
                         "repo_snapshot_commit", "evidence"}
        valid, invalid = [], []
        for f in facts:
            missing = required_fields - set(f.keys())
            if missing:
                invalid.append({**f, "_missing_fields": list(missing)})
                continue
            # Validate fact_type enum
            if f.get("fact_type") not in self.VALID_FACT_TYPES:
                invalid.append({**f, "_invalid_fact_type": f.get("fact_type")})
                continue
            # Validate evidence structure
            evidence = f.get("evidence", [])
            if not isinstance(evidence, list):
                invalid.append({**f, "_invalid_evidence": "not a list"})
                continue
            for ev in evidence:
                if not isinstance(ev, dict):
                    invalid.append({**f, "_invalid_evidence": "evidence item not a dict"})
                    break
                if "locator_type" not in ev or "locator" not in ev:
                    invalid.append({**f, "_invalid_evidence": "missing locator_type or locator"})
                    break
            else:
                valid.append(f)
        return valid, invalid

    def _deduplicate(self, facts: list[dict]) -> tuple[list[dict], list[dict]]:
        """Deduplicate facts by fact_id, keeping first occurrence."""
        seen: set[str] = set()
        unique, duplicates = [], []
        for f in facts:
            fid = f.get("fact_id", "")
            if fid in seen:
                duplicates.append(f)
            else:
                seen.add(fid)
                unique.append(f)
        return unique, duplicates

    def _detect_conflicts(self, facts: list[dict]) -> list[dict]:
        """Detect contradictory facts based on fact_type + overlapping subjects."""
        from collections import defaultdict
        conflicts: list[dict] = []

        # Group by fact_type + domain
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for f in facts:
            key = (f.get("fact_type", ""), f.get("domain", ""))
            groups[key].append(f)

        for group_key, group_facts in groups.items():
            if len(group_facts) < 2:
                continue
            # Check for contradictory confidence or status
            statuses = {gf.get("status") for gf in group_facts}
            if "active" in statuses and "filtered" in statuses:
                conflicts.append({
                    "fact_ids": [gf["fact_id"] for gf in group_facts],
                    "conflict_type": "contradictory_statement",
                    "explanation": f"Multiple facts with same type={group_key[0]} and domain={group_key[1]} "
                                   f"have conflicting status: {statuses}",
                    "resolution_status": "preserved",
                })

        return conflicts
```

- [ ] **Step 4: Implement baseline stage**

Add to `run.py`:

```python
    def _run_baseline(self, state: HarnessState) -> bool:
        """Baseline: source-aware arbitration → facts.vN.yaml freeze."""
        print("  -> Running baseline stage")

        facts_dir = OUTPUT_BASE / "facts"
        if not facts_dir.exists():
            print(f"  ERROR: facts directory not found: {facts_dir}")
            return False

        validated_path = sorted(facts_dir.glob("validated.v*.yaml"), reverse=True)
        conflicts_path = sorted(facts_dir.glob("conflicts.v*.yaml"), reverse=True)

        if not validated_path:
            print("  ERROR: no validated facts found")
            return False

        validated_data = yaml.safe_load(validated_path[0].read_text())
        conflicts_data = yaml.safe_load(conflicts_path[0].read_text()) if conflicts_path else {"conflicts": []}

        facts = validated_data.get("facts", [])
        conflicts = conflicts_data.get("conflicts", [])

        # Source priority: architect > hotspot > codebase (per arbitration rules)
        # Strength: recurring > evidence_backed > isolated
        baseline_facts, dropped = self._arbitrate(facts)

        print(f"  Arbitration: {len(baseline_facts)} accepted, {len(dropped)} dropped")

        version = self._next_version("baseline_facts")
        baseline_dir = OUTPUT_BASE / "baseline"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        facts_out = baseline_dir / f"facts.{version}.yaml"

        head = self._get_repo_head()
        snapshot_ver = f"sf-{__import__('datetime').date.today().strftime('%Y-%m-%d')}.{version[1:]}"

        yaml.dump({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "snapshot_version": snapshot_ver,
                "sources": {
                    "hotspot_map": self._find_latest_version("hotspot_map"),
                    "codebase_map": self._find_latest_version("codebase_map"),
                    "architect_augment": self._find_latest_version("architect_augment"),
                },
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "arbitration": {
                    "total_candidates": len(facts),
                    "accepted": len(baseline_facts),
                    "dropped": len(dropped),
                    "conflicts_preserved": len(conflicts),
                    "source_priority": "architect > hotspot > codebase",
                },
            },
            "facts": baseline_facts,
            "conflicts": conflicts,
            "lineage": {f["fact_id"]: {"source": f["source"]} for f in baseline_facts},
        }, facts_out.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)

        # Also write facts.latest.yaml
        latest = baseline_dir / "facts.latest.yaml"
        import shutil
        shutil.copy(facts_out, latest)

        # Write snapshot.yaml
        snapshot_path = baseline_dir / "snapshot.yaml"
        yaml.dump({
            "snapshot_version": snapshot_ver,
            "repo_snapshot_commit": head,
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "sources": {
                "hotspot_map": self._find_latest_version("hotspot_map"),
                "codebase_map": self._find_latest_version("codebase_map"),
                "architect_augment": self._find_latest_version("architect_augment"),
            },
        }, snapshot_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)

        print(f"  Wrote baseline facts -> {facts_out}")
        print(f"  facts.latest.yaml -> {latest}")
        print(f"  snapshot.yaml -> {snapshot_path}")
        self.add_artifact(state, str(facts_out))
        self.add_artifact(state, str(latest))
        self.add_artifact(state, str(snapshot_path))
        return True

    def _arbitrate(self, facts: list[dict]) -> tuple[list[dict], list[dict]]:
        """Apply source-aware arbitration rules (all 4 axes).

        Priority order:
        1. Source: architect > hotspot > codebase
        2. Evidence strength: recurring > evidence_backed > isolated
        3. Snapshot: current > older
        4. Preserve conflicts rather than hide them
        """
        from collections import defaultdict

        current_head = self._get_repo_head()

        def arbitration_key(fact: dict) -> tuple:
            """Sort key: (source_rank, evidence_strength_rank, is_current_snapshot)."""
            source_rank = source_order.get(fact.get("source", ""), 99)
            # Strength: hotspot_signal=recurring > confidence=confirmed > uncertain
            ev = fact.get("evidence", [])
            is_hotspot_signal = fact.get("fact_type") == "hotspot_signal"
            if is_hotspot_signal:
                strength_rank = 0  # recurring
            elif fact.get("confidence") == "confirmed":
                strength_rank = 1  # evidence_backed
            else:
                strength_rank = 2  # isolated / uncertain
            # Snapshot: current (matches HEAD) wins
            is_current = 0 if fact.get("repo_snapshot_commit") == current_head else 1
            return (source_rank, strength_rank, is_current)

        # Group by semantic equivalence (rough: same fact_type + similar statement)
        groups: dict[str, list[dict]] = defaultdict(list)
        for f in facts:
            key = (f.get("fact_type", ""), f.get("statement", "")[:80])
            groups[str(key)].append(f)

        baseline: list[dict] = []
        dropped: list[dict] = []

        for group_key, group_facts in groups.items():
            if len(group_facts) == 1:
                baseline.append(group_facts[0])
                continue

            # Sort by all 4 axes
            source_order = {"architect": 0, "hotspot": 1, "codebase": 2}
            group_facts.sort(key=arbitration_key)

            winner = group_facts[0]
            losers = group_facts[1:]

            # Preserve conflict if loser is semantically different (low word overlap)
            for loser in losers:
                winner_words = set(winner.get("statement", "").lower().split())
                loser_words = set(loser.get("statement", "").lower().split())
                overlap = (
                    len(winner_words & loser_words) /
                    max(len(winner_words), len(loser_words))
                    if winner_words and loser_words else 0
                )
                if overlap < 0.3:
                    # Different meaning — accept both as conflict
                    baseline.append(winner)
                    baseline.append(loser)
                    break
            else:
                # All losers are dominated — accept winner, drop others
                baseline.append(winner)
                for loser in losers:
                    dropped.append({
                        **loser,
                        "_reason": f"dominated by {winner.get('fact_id')} "
                                   f"source={winner.get('source')} "
                                   f"snapshot={winner.get('repo_snapshot_commit')}",
                    })

        return baseline, dropped

    def _find_latest_version(self, prefix: str) -> str:
        """Find latest version string for a map prefix."""
        maps_dir = OUTPUT_BASE / "maps"
        if not maps_dir.exists():
            return "unknown"
        maps = sorted(maps_dir.glob(f"{prefix}.v*.yaml"), reverse=True)
        if maps:
            return maps[0].stem.split(".")[-1]
        return "unknown"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_repo_structure.py::test_validate_merges_three_maps tests/test_repo_structure.py::test_baseline_produces_versioned_facts -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add skills/repo-structure/run.py tests/test_repo_structure.py
git commit -m "feat(repo-structure): implement validate and baseline stages with source-aware arbitration"
```

---

## Task 9: Reference Documents

Copy reference documents from the spec directory into the skill directory.

**Files:**
- Create: `skills/repo-structure/references/evidence-model.md`
- Create: `skills/repo-structure/references/preflight-rules.md`
- Create: `skills/repo-structure/references/arbitration-rules.md`
- Create: `skills/repo-structure/references/pipeline-overview.md`
- Create: `skills/repo-structure/references/gotchas.md`

- [ ] **Step 1: Copy all reference files**

Run:
```bash
for src in docs/superpowers/specs/2026-03-22-evidence-model.md \
           docs/superpowers/specs/2026-03-22-preflight-rules.md \
           docs/superpowers/specs/2026-03-29-arbitration-rules.md \
           docs/superpowers/specs/2026-03-22-pipeline-overview.md \
           docs/superpowers/specs/2026-03-22-gotchas.md; do
  dst="skills/repo-structure/references/$(basename $src)"
  cp "$src" "$dst"
done
ls skills/repo-structure/references/
```

Expected: 5 files listed

- [ ] **Step 2: Commit**

```bash
git add skills/repo-structure/references/
git commit -m "docs(repo-structure): add reference documents from spec"
```

---

## Task 10: SKILL.md and Dispatcher Integration

Create the `SKILL.md` and wire `/repo-structure` into the CLI dispatcher.

**Files:**
- Create: `skills/repo-structure/SKILL.md`
- Modify: `src/dispatcher.py`

- [ ] **Step 1: Write the SKILL.md**

```markdown
---
name: repo-structure
description: Extract structured facts from codebase + git history into versioned baseline
---

# Repo Structure

Extract structured semantic facts from a codebase and its git history.

## Usage

```
/repo-structure run              # Full pipeline (preflight → all 6 stages)
/repo-structure check            # Validate dependencies without running
/repo-structure step             # Run one stage at a time
/repo-structure resume           # Continue from last checkpoint
/repo-structure status           # Show current state
/repo-structure reset            # Reset state (preserve artifacts)
/repo-structure --stage <stage>  # Run from specific stage
```

## Preconditions

Required inputs (fail-fast if missing):
- `data/commit-extract/` — upstream from `/commit-extract run`
- `.planning/codebase/{STRUCTURE,ARCHITECTURE,CONCERNS,CONVENTIONS,INTEGRATIONS,STACK,TESTING}.md` — upstream from `gsd map-codebase`

Optional inputs (warning only):
- `docs/ARCHITECTURE.md` — if absent, augment stage emits empty output

## Stages

| Stage | Input | Output |
|-------|-------|--------|
| `sample` | 7-file gsd dossier | `data/repo-structure/sample/manifest.yaml` |
| `hotspot` | `data/commit-extract/` + `data/commit-semantic/patterns/` | `data/repo-structure/maps/hotspot_map.vN.yaml` |
| `extract` | `sample/manifest.yaml` + 7-file dossier | `data/repo-structure/maps/codebase_map.vN.yaml` |
| `augment` | `docs/ARCHITECTURE.md` + repo evidence | `data/repo-structure/maps/architect_augment.vN.yaml` |
| `validate` | 3 maps | `data/repo-structure/facts/validated.vN.yaml` + `conflicts.vN.yaml` |
| `baseline` | `validated.vN.yaml` + `conflicts.vN.yaml` | `data/repo-structure/baseline/facts.vN.yaml` |

## Output

**Sole source-of-truth:**
- `data/repo-structure/baseline/facts.vN.yaml`

Derived views (not editable directly):
- `data/repo-structure/baseline/facts.latest.yaml`
- `data/repo-structure/baseline/snapshot.yaml`
- `data/repo-structure/maps/hotspot_map.vN.yaml`
- `data/repo-structure/maps/codebase_map.vN.yaml`
- `data/repo-structure/maps/architect_augment.vN.yaml`

## Evidence Model

Every fact carries evidence with:
- `locator_type`: `file_path | symbol | config_key | section_ref | test_case | ast_pattern`
- `locator`: concrete value matching the locator_type
- `stable_ref`: stable identifier (symbol_signature_hash or file_blob_sha)
- `rationale`: why this evidence supports the statement

Evidence priority (baseline arbitration):
1. Source: architect > hotspot > codebase
2. Strength: recurring > evidence_backed > isolated
3. Snapshot: current > older

## Key Rules

- **Preflight first**: always validate dependencies before execution
- **Three maps are independent**: each can re-run without forcing others
- **facts.vN.yaml is sole source-of-truth**: derived maps must not be directly edited
- **hotspot is NOT raw git stats**: must use commit-extract + commit-semantic
- **Extract is section-routed**: each gsd section has fixed locator_type mapping, not file-level batching
- **Augment is two-phase**: Python evidence collection + LLM adjudication
- **Preserve conflicts**: unresolved disagreements → conflicts.yaml, not silent merge
- **No bootstrap**: do not generate commit-extract or gsd artifacts from inside this pipeline

## Worker Prompts

- `prompts/extract_codebase.md` — section-routed fact extraction
- `prompts/augment_architect.md` — claim adjudication

## References

- `references/pipeline-overview.md` — operational overview
- `references/preflight-rules.md` — dependency contract
- `references/arbitration-rules.md` — baseline arbitration logic
- `references/evidence-model.md` — evidence contract
- `references/gotchas.md` — 17 failure modes

## Architecture

Python ETL pipeline extending `SkillRunner`. LLM analysis via Team Agent pattern (extract + augment). Three independent source pipelines fused at `baseline`.

```
git commits → commit-extract → commit-semantic → hotspot_map
code tree   → gsd → 7-file dossier → sample → extract → codebase_map
arch docs   → augment → architect_augment
                                          ↓
                            validate → baseline → facts.vN.yaml
```

## Implementation

Run via CLI:
```bash
python -m skills.repo_structure.run
python -m skills.repo_structure.run check
python -m skills.repo_structure.run --stage extract
```
```

- [ ] **Step 2: Add `/repo-structure` to dispatcher**

Modify `src/dispatcher.py` to add routing:

```python
# In src/dispatcher.py, add near top:
try:
    from skills.repo_structure.run import RepoStructureRunner
    _REPO_STRUCTURE_RUNNER = RepoStructureRunner()
except ImportError:
    _REPO_STRUCTURE_RUNNER = None

# In the dispatch() function, add before the final return:
if command == "repo-structure":
    if _REPO_STRUCTURE_RUNNER is None:
        return {"command": command, "status": "error",
                "error": "repo-structure skill not installed"}
    import sys
    return {"command": command, "status": "ok",
            "exit_code": _REPO_STRUCTURE_RUNNER.main(sys.argv[2:] if len(sys.argv) > 2 else [])}
```

- [ ] **Step 3: Test dispatcher integration**

Run: `cd /Users/yan./git/3p/sematic-harness && python -m skills.repo_structure.run check 2>&1 | head -20`
Expected: preflight output (may fail on missing deps, that's expected)

- [ ] **Step 4: Commit**

```bash
git add skills/repo-structure/SKILL.md src/dispatcher.py
git commit -m "feat(repo-structure): add SKILL.md and dispatcher integration"
```

---

## Task 11: End-to-End Test

Run the complete pipeline on a minimal fixture.

**Files:**
- Modify: `tests/test_repo_structure.py`

- [ ] **Step 1: Write full E2E test**

```python
# tests/test_repo_structure.py (append)

def test_full_pipeline_produces_baseline(tmp_path, monkeypatch):
    """Run full pipeline: sample → hotspot → extract → augment → validate → baseline."""
    import sys, yaml
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    # Set up all required inputs
    (tmp_path / "data/commit-extract").mkdir(parents=True)
    (tmp_path / "data/commit-semantic/patterns").mkdir(parents=True)
    gsd_dir = tmp_path / ".planning/codebase"
    gsd_dir.mkdir(parents=True)

    for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                  "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
        (gsd_dir / fname).write_text(f"## Section\nTest content for {fname}.\n")

    # commit-extract artifact
    yaml.dump({"metadata": {"month": "2025-01"}, "commits": [
        {"commit_id": "abc", "files": ["src/hermes/registry.py"]}
    ]}, (tmp_path / "data/commit-extract/2025-01.yaml").open("w"))

    # commit-semantic patterns
    yaml.dump({"patterns": [{"pattern_id": "p1", "description": "Test pattern"}]},
              (tmp_path / "data/commit-semantic/patterns/canonical.yaml").open("w"))

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.harness_state import HarnessState
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    from skills.repo_structure.run import RepoStructureRunner

    runner = RepoStructureRunner()
    state = HarnessState()

    # Run all stages
    stages = ["sample", "hotspot", "extract", "augment", "validate", "baseline"]
    for stage in stages:
        print(f"\n--- Running {stage} ---")
        success = runner.run_stage(stage, state)
        assert success, f"Stage {stage} failed"

    # Verify baseline
    baseline_dir = tmp_path / "data/repo-structure/baseline"
    assert baseline_dir.exists()
    baseline_files = sorted(baseline_dir.glob("facts.v*.yaml"))
    assert len(baseline_files) >= 1, f"No baseline facts found in {baseline_dir}"

    data = yaml.safe_load(baseline_files[0].read_text())
    assert "facts" in data
    assert "metadata" in data
    assert "conflicts" in data
    assert "version" in data["metadata"]
    assert data["metadata"]["version"].startswith("v")
    print(f"\nBaseline produced: {baseline_files[0].name}")
    print(f"  Facts: {len(data['facts'])}")
    print(f"  Conflicts: {len(data['conflicts'])}")
```

- [ ] **Step 2: Run E2E test**

Run: `pytest tests/test_repo_structure.py::test_full_pipeline_produces_baseline -v -s`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_repo_structure.py
git commit -m "test(repo-structure): add full E2E pipeline test"
```

---

## Completion Gates

After all tasks:

```bash
# 1. All tests pass
pytest tests/test_repo_structure.py -v

# 2. Baseline artifact is valid YAML
python -c "import yaml; yaml.safe_load(open('data/repo-structure/baseline/facts.v0.yaml'))"

# 3. All facts have evidence
python -c "
import yaml
with open('data/repo-structure/baseline/facts.v0.yaml') as f:
    data = yaml.safe_load(f)
missing = [fid for fid, fac in {f['fact_id']: f for f in data['facts']}.items()
           if not fac.get('evidence')]
print(f'Facts without evidence: {len(missing)}')
assert len(missing) == 0, f'Facts {missing} lack evidence'
"

# 4. Skills are importable
python -c "from skills.repo_structure.run import RepoStructureRunner; print('OK')"

# 5. Check command works
python -m skills.repo_structure.run check 2>&1 | head -5
```

---

## Files Summary

**Create (16 new files):**
```
skills/repo-structure/SKILL.md
skills/repo-structure/__init__.py
skills/repo-structure/run.py
skills/repo-structure/preflight.py
skills/repo-structure/schemas/fact_entry.schema.yaml
skills/repo-structure/schemas/baseline_facts.schema.yaml
skills/repo-structure/schemas/state.schema.yaml
skills/repo-structure/prompts/extract_codebase.md
skills/repo-structure/prompts/augment_architect.md
skills/repo-structure/references/evidence-model.md
skills/repo-structure/references/preflight-rules.md
skills/repo-structure/references/arbitration-rules.md
skills/repo-structure/references/pipeline-overview.md
skills/repo-structure/references/gotchas.md
tests/test_repo_structure.py
```

**Modify (1 file):**
```
src/dispatcher.py
```

**Total commits:** 8 (one per task, plus reference docs)
