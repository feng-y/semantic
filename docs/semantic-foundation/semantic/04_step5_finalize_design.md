# step5 · finalize and publish

## Goal
Publish final canonical semantic assets for downstream `demand`.

## Inputs
- recommendations.yaml
- review-decisions.yaml
- evidence-checks.yaml (optional)

## Canonical outputs
- domain-map.yaml
- concept-map.yaml
- rule-map.yaml
- demand-model-map.yaml
- change-log.yaml

## View outputs
- matching `.md` files

## Rules
- only keep/merge results become final assets
- unresolved verify_first blocks finalize
- rule must contain validation
- demand model must reference domain/concept/rule
