# Semantic Runner Design

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Contract Definition
**Role**: This document is canonical for semantic runner behavior. All runner implementations must follow these contracts.

---

## Overview

The SEMANTIC runner orchestrates execution of semantic stages through two modes:
- **next**: Execute next incomplete stage
- **all**: Execute all stages from current position to completion

---

## Modes

### Next Mode

**Purpose**: Execute the next incomplete stage only.

**Behavior**:
1. Read `run-state.yaml`
2. Determine next incomplete stage
3. Execute that stage
4. Update `run-state.yaml`
5. Stop

**Use Case**: Incremental development, debugging, manual control.

**Example**:
```bash
python -m semantic.run next
```

**Output**:
```
Stage: step2_candidates
Status: running
...
Stage: step2_candidates
Status: completed
Next: step3_recommend
```

### All Mode

**Purpose**: Execute all stages from current position to completion.

**Behavior**:
1. Read `run-state.yaml`
2. Determine starting stage
3. Execute stages sequentially
4. Update `run-state.yaml` after each stage
5. Stop on blocking error or completion

**Use Case**: Full pipeline execution, CI/CD, automated runs.

**Example**:
```bash
python -m semantic.run all
```

**Output**:
```
Stage: step1_signals
Status: completed

Stage: step2_candidates
Status: completed

Stage: step3_recommend
Status: completed

Stage: step4_review
Status: waiting_for_human

Pipeline stopped: human review required
```

---

## State File

### Location

**File**: `run-state.yaml`

**Path**: `docs/semantic-foundation/semantic/run-state.yaml`

### Structure

```yaml
run_state:
  current_stage: "step1_signals|step2_candidates|step3_recommend|step4_review|step5_finalize"
  stage_status:
    step1_signals: "pending|running|completed|failed|skipped"
    step2_candidates: "pending|running|completed|failed|skipped"
    step3_recommend: "pending|running|completed|failed|skipped"
    step4_review: "pending|running|completed|failed|waiting_for_human"
    step5_finalize: "pending|running|completed|failed|blocked"

  last_completed_stage: string
  last_run_at: string
  error_log: [string]

  blocking_issues:
    - stage: string
      issue: string
      severity: "fatal|blocking|warning"

  verify_first_status:
    unresolved_count: integer
    blocking_finalize: boolean

metadata:
  run_id: string
  started_at: string
  completed_at: string
  mode: "next|all"
```

### State Transitions

**Pending** → **Running**: Stage execution starts
**Running** → **Completed**: Stage execution succeeds
**Running** → **Failed**: Stage execution fails
**Completed** → **Skipped**: Stage skipped (already done)
**Pending** → **Waiting_for_human**: Human review required
**Pending** → **Blocked**: Blocked by unresolved issues

---

## Blocking Rules

### Fatal Errors

**Definition**: Errors that stop execution immediately.

**Examples**:
- Missing required input files
- Malformed YAML
- Python exceptions
- File I/O errors

**Behavior**:
- Stop execution
- Set stage status to `failed`
- Log error to `error_log`
- Exit with non-zero code

**Recovery**: Fix error, re-run stage.

### Blocking Errors

**Definition**: Errors that prevent progression but allow current stage to complete.

**Examples**:
- No candidates generated (Step2)
- All scores below threshold (Step3)
- Evidence validation failed (Step4)
- Unresolved issues block finalize (Step5)

**Behavior**:
- Complete current stage
- Set next stage status to `blocked`
- Log blocking issue to `blocking_issues`
- Stop execution (in `all` mode)

**Recovery**: Address blocking issue, re-run from blocked stage.

### Warnings

**Definition**: Issues that don't stop execution but should be noted.

**Examples**:
- Low confidence signals (Step1)
- Few candidates generated (Step2)
- Low scores (Step3)
- Missing evidence refs (Step4)

**Behavior**:
- Continue execution
- Log warning to `error_log`
- Include warning in stage output

**Recovery**: Optional, can proceed.

---

## Finalize Guard

### Verify First Rule

**Rule**: Step5 (Finalize) is BLOCKED if Step4 (Review) has unresolved issues.

**Purpose**: Prevent finalizing semantic models with unvalidated evidence or unresolved review issues.

### Unresolved Issues

**Definition**: Issues flagged in Step4 that require resolution before finalize.

**Examples**:
- Evidence validation failed
- Architect requested modifications
- Missing evidence refs
- Conflicting decisions

**Check**:
```yaml
verify_first_status:
  unresolved_count: 3
  blocking_finalize: true
```

**Behavior**:
- Step5 checks `verify_first_status.blocking_finalize`
- If `true`, Step5 is BLOCKED
- If `false`, Step5 proceeds

### Resolution

**To unblock Step5**:
1. Address unresolved issues in Step4
2. Re-run Step4 with fixes
3. Verify `unresolved_count` = 0
4. Set `blocking_finalize` = false
5. Run Step5

---

## Workspace

### Location

**Path**: `docs/semantic-foundation/semantic/`

**Purpose**: Store all semantic outputs in one location.

**Note**: This is the semantic layer workspace. Do not confuse with `docs/semantic/` which contains old FACT runtime artifacts (transitional naming).

### Structure

```
docs/semantic-foundation/semantic/
├── signals.yaml
├── signals.md (view)
├── candidates.yaml
├── candidates.md (view)
├── recommendations.yaml
├── recommendations.md (view)
├── review-decisions.yaml
├── evidence-checks.yaml
├── review-note.md (view)
├── domain-map.yaml
├── concept-map.yaml
├── rule-map.yaml
├── demand-model-map.yaml
├── change-log.yaml
├── run-state.yaml
├── domain-map.md (view)
├── concept-map.md (view)
├── rule-map.md (view)
└── demand-model-map.md (view)
```

### File Roles

| File | Role | Stage |
|------|------|-------|
| `signals.yaml` | Canonical output | Step1 |
| `candidates.yaml` | Canonical output | Step2 |
| `recommendations.yaml` | Canonical output | Step3 |
| `review-decisions.yaml` | Canonical output | Step4 |
| `evidence-checks.yaml` | Canonical output | Step4 |
| `domain-map.yaml` | Canonical output | Step5 |
| `concept-map.yaml` | Canonical output | Step5 |
| `rule-map.yaml` | Canonical output | Step5 |
| `demand-model-map.yaml` | Canonical output | Step5 |
| `change-log.yaml` | Canonical output | Step5 |
| `run-state.yaml` | Runner state | All |
| `*.md` | View outputs | Step5 |

---

## Stage Progression Rules

### Rule 1: Sequential Execution

**Stages must execute in order**:
1. Step1 → Step2 → Step3 → Step4 → Step5

**Cannot skip stages** (except if already completed).

### Rule 2: Dependency Check

**Each stage checks for required inputs**:
- Step2 requires `signals.yaml` from Step1
- Step3 requires `candidates.yaml` from Step2
- Step4 requires `recommendations.yaml` from Step3
- Step5 requires `review-decisions.yaml` and `evidence-checks.yaml` from Step4

**If input missing**: FATAL error, stop execution.

### Rule 3: Idempotency

**Re-running a completed stage**:
- Overwrites previous output
- Updates `run-state.yaml`
- Does not affect subsequent stages (they must be re-run)

### Rule 4: Human Review Gate

**Step4 may require human review**:
- Set stage status to `waiting_for_human`
- Stop execution in `all` mode
- Resume after human provides `review-decisions.yaml`

### Rule 5: Finalize Guard

**Step5 is blocked if**:
- `verify_first_status.blocking_finalize` = true
- Unresolved issues exist in Step4

**Must resolve issues before Step5 can proceed**.

---

## Error Handling

### Fatal Errors

**Action**: Stop immediately, log error, exit non-zero.

**Examples**:
- Missing input file
- Malformed YAML
- Python exception

### Blocking Errors

**Action**: Complete current stage, block next stage, stop execution.

**Examples**:
- No candidates generated
- All scores below threshold
- Evidence validation failed

### Warnings

**Action**: Log warning, continue execution.

**Examples**:
- Low confidence
- Few candidates
- Missing optional fields

---

## Runner CLI

### Commands

```bash
# Execute next incomplete stage
python -m semantic.run next

# Execute all stages from current position
python -m semantic.run all

# Check current status
python -m semantic.run status

# Reset run state
python -m semantic.run reset
```

### Status Command

**Output**:
```
Current Stage: step3_recommend
Status: completed

Stage Status:
  step1_signals: completed
  step2_candidates: completed
  step3_recommend: completed
  step4_review: pending
  step5_finalize: pending

Blocking Issues: None

Next Action: Run step4_review
```

### Reset Command

**Action**: Reset `run-state.yaml` to initial state.

**Warning**: Does not delete output files, only resets state.

---

## Summary

**SEMANTIC runner**:
- Orchestrates 5-stage execution
- Supports `next` and `all` modes
- Maintains `run-state.yaml`
- Enforces blocking rules
- Guards finalize with verify_first
- Stores outputs in semantic workspace

**Key principles**:
- Sequential execution
- Dependency checking
- Idempotent stages
- Human review gate
- Finalize guard
