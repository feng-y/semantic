Goal:
Convert `candidates.yaml` into `recommendations.yaml`.

You must:
1. decide semantic_validity = pass|fail
2. assign:
   - business_score: float 1.0~10.0
   - value_score: float 1.0~10.0
3. output recommendation:
   - status: recommend | not_recommend | defer
   - action: keep | merge | drop | backlog | verify_first
4. include:
   - recommended_reasons
   - not_recommended_reasons
5. mark:
   - needs_evidence_check
   - evidence_gap
   - merge_target if action=merge

Program recomputes:
priority = max(business_score, value_score)
