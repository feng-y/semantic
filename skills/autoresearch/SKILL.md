---
name: autoresearch
description: Iteratively optimize a prompt or skill using a fixed dataset, binary evals, single-mutation experiments, and keep/discard decisions. Use when improving a prompt, continuing prior prompt tuning work, building a reusable eval-driven research loop, or turning repeated manual prompt iteration into a stable workflow. Especially useful for extraction, classification, summarization, semantic structuring, and any task where "good output" can be defined as structured yes/no checks.
triggers:
  - autoresearch
  - prompt optimization
  - optimize this prompt
  - continue autoresearch
  - eval-driven prompt tuning
  - improve this skill with evals
---

# Autoresearch

Autoresearch is a disciplined optimization loop for prompts and skills.

The goal is **not** to keep rewriting a prompt until it "feels better." The goal is to make quality improvement measurable, repeatable, and resumable.

Use this skill when you want Claude to improve a prompt or skill through controlled experiments instead of ad hoc edits.

## What this skill does

Autoresearch turns prompt tuning into a stable loop:

1. Load the current research workspace
2. Read the dataset, evals, and prior experiment history
3. Identify the weakest eval or most important failure mode
4. Propose **one** hypothesis for improvement
5. Apply **one** targeted mutation
6. Re-run the same dataset against the same evals
7. Decide **keep** or **discard**
8. Update state and logs so the work can continue later

This skill is for **iterative optimization**, not greenfield brainstorming.

## Core principles

### 1. Fixed dataset
Do not keep changing the test set mid-run. A stable dataset is what makes scores comparable across iterations.

### 2. Binary evals only
Prefer yes/no checks. Avoid fuzzy 1-10 scoring. Autoresearch needs stable signals.

### 3. One mutation per iteration
Do not change five things at once. If a score moves, you should know why.

### 4. Keep or discard
If the mutation improves results, keep it. If it does not, revert it.

### 5. State must be externalized
Do not rely on conversation memory. Store context in workspace files so any future run can continue from disk.

## Workspace structure

Every autoresearch target should have its own workspace directory:

```text
autoresearch-<topic>/
├── config.md
├── STATE.md
├── results.tsv
├── changelog.md
├── datasets/
│   └── dataset.json
├── evals/
│   └── evals.md
├── mutations/
│   ├── exp-001.md
│   ├── exp-002.md
│   └── ...
└── artifacts/
    ├── baseline/
    ├── exp-001/
    └── ...
```

Minimum required files:
- `config.md`
- `STATE.md`
- `results.tsv`
- `changelog.md`

If they do not exist, initialize them from templates before starting.
Templates live in `assets/templates/`.
Detailed file-role guidance lives in `references/workflow.md`.

## Modes

### Mode 1 — init
Use when the user is starting autoresearch for a new target.

Steps:
1. Confirm target file
2. Confirm workspace name
3. Confirm dataset
4. Confirm binary evals
5. Write initial workspace files
6. Run baseline
7. Save baseline into `results.tsv`, `STATE.md`, and `changelog.md`

### Mode 2 — baseline
Use when the user wants to measure the current prompt/skill without changing it.

Steps:
1. Load workspace
2. Re-run dataset
3. Score using the same evals
4. Update baseline artifacts

### Mode 3 — continue
Use when a workspace already exists and the user wants to keep optimizing.

Steps:
1. Read `STATE.md`
2. Read `results.tsv`
3. Read latest `changelog.md`
4. Identify weakest eval
5. Propose one mutation
6. Run one experiment
7. Keep/discard
8. Update all logs

### Mode 4 — one-iteration
Use when the user wants exactly one controlled experiment.

This is the recommended default for ongoing work.

## Required inputs

Before running autoresearch, make sure these are known:

1. **Target file**
   - Example: `skills/commit-extract/prompt.md`

2. **Workspace directory**
   - Example: `autoresearch-commit-extract/`

3. **Dataset**
   - Fixed test cases, examples, prompts, or SHAs

4. **Evals**
   - Binary yes/no checks only

5. **Stop condition**
   - Example: one iteration only, or stop after two non-improving rounds

If any of these are missing, ask before proceeding.

## Prompt layers inside the autoresearch system

Autoresearch is not one prompt. It is a workflow with multiple prompt roles.

### 1. Orchestrator
Controls the loop:
- which mode is active
- which files to read
- what to do next

### 2. Evaluator
Scores outputs against binary evals.

### 3. Diagnoser
Explains why outputs failed.

### 4. Mutation generator
Proposes one hypothesis for improvement.

### 5. Patch writer
Turns that hypothesis into an actual edit.

### 6. Judge
Makes the keep/discard decision.

Keep these concerns separate. Do not collapse them into one vague instruction block.

## Standard one-iteration workflow

When running one iteration, always follow this order:

1. Read `config.md`
2. Read `STATE.md`
3. Read `results.tsv`
4. Read the latest experiment entry from `changelog.md`
5. Identify the weakest eval
6. Summarize the likely failure mode
7. Propose **one** mutation
8. Edit the target file
9. Re-run the same dataset
10. Re-score with the same evals
11. Compare to the previous baseline
12. If improved: **KEEP**
13. If not improved: **DISCARD** and revert
14. Update:
   - `STATE.md`
   - `results.tsv`
   - `changelog.md`
   - `mutations/exp-XXX.md`

## Keep / discard policy

### KEEP when:
- Total score improves
- Or the weakest eval improves with no unacceptable regressions elsewhere

### DISCARD when:
- Total score does not improve
- Or score improves trivially but introduces obvious regressions
- Or the mutation increases complexity without measurable benefit

Do not keep a mutation just because it sounds reasonable.

## Boundaries

By default, autoresearch should **not**:
- change the dataset
- change eval definitions
- run multiple unrelated mutations in one iteration
- auto-commit git changes
- auto-push changes
- optimize for a new target without an explicit new workspace

Only do these things if the user explicitly asks.

## Suggested files

### `config.md`
Should define:
- target file
- dataset location or list
- eval list
- stop conditions
- boundaries

### `STATE.md`
Should define:
- current baseline
- weakest eval
- last kept mutation
- known good directions
- known risks
- next hypothesis

### `results.tsv`
Should define:
- experiment number
- score
- max score
- pass rate
- keep/discard
- short description

### `changelog.md`
Should explain:
- what changed
- why it was changed
- what improved
- what regressed
- what remains weak

## Example user intents that should trigger this skill

- "continue autoresearch on commit-extract"
- "optimize this prompt with evals"
- "run one prompt-tuning iteration"
- "use the same dataset and improve the weakest eval"
- "turn this manual prompt iteration workflow into a repeatable loop"
- "initialize autoresearch for this skill"

## Report format

After each iteration, report briefly:

```md
STATUS: KEEP | DISCARD
BASELINE: X/Y (Z%)
NEW SCORE: X/Y (Z%)
DELTA: +N / -N
WEAKEST EVAL BEFORE: ...
MUTATION: ...
RESULT: ...
NEXT LIKELY DIRECTION: ...
```

Keep the report short. The detailed reasoning belongs in the workspace files.

## What success looks like

A good autoresearch run should leave behind a workspace that another future run can resume without reading conversation history.

That means the disk state should be sufficient to answer:
- What are we optimizing?
- How are we measuring it?
- What was tried already?
- What worked?
- What failed?
- What should happen next?

If the workspace cannot answer those questions, the run is incomplete.
