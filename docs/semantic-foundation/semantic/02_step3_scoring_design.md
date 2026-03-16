# step3 · scoring and recommendation

## Goal
Convert `candidates.yaml` into `recommendations.yaml` for human review.

## Canonical output
- `recommendations.yaml`
- `recommendations.md` (view)

## Required fields
- semantic_validity
- validity_reason
- business_score (1.0~10.0 float)
- value_score (1.0~10.0 float)
- priority = max(business_score, value_score)
- recommendation.status
- recommendation.action
- recommended_reasons
- not_recommended_reasons
- needs_evidence_check
- evidence_gap
- merge_target

## Rules
- YAML is canonical
- priority must be recomputed by program
- AI recommends, human decides later
- reasons must be concise and specific
