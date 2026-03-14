# 007 Sampling Policy

## Analysis
Sampling improves efficiency but may hide critical files if it is invisible or overly automatic.

## Research
Engineering systems often use quick mode vs safe mode or automatic mode vs confirmation mode.

## Questions
Should sampling always continue automatically?
Should sampling always require confirmation?

## Alternatives
- fixed auto
- fixed confirm
- architect-selected mode with optional timeout

## Scoring
Architect-selected sampling mode with optional timeout provides the best balance of simplicity, safety, and flexibility.

## Recommendation
Use visible sampling with:
- mode = auto | confirm
- optional timeout

## Decision
Accepted.
