# 005 Artifact Versioning

## Analysis
Refine can accidentally overwrite semantic understanding. History should be preserved.

## Research
State-bearing systems often retain rolling versions or immutable checkpoints.

## Questions
Should discovery and review artifacts be versioned?

## Alternatives
- patch only, single file
- full versioning on every artifact
- rolling version window with retained accepted baseline

## Scoring
Rolling version window with retained accepted baseline balances safety and simplicity.

## Recommendation
Version discovery and review artifacts, keep latest 3 working versions by default, retain accepted baseline versions.

## Decision
Accepted.
