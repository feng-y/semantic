# step4 · review and local evidence

## Goal
Turn `recommendations.yaml` into final review decisions and optional local evidence checks.

## Canonical outputs
- `review-decisions.yaml`
- `evidence-checks.yaml` (optional)

## View output
- `review-note.md`

## Allowed actions
- keep
- merge
- drop
- backlog
- verify_first

## Rules
- human is final decision-maker
- verify_first must enter evidence check loop
- merge requires merge_target
- review decisions are canonical, markdown is not
