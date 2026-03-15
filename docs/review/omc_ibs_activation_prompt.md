# OMC IBS 激活 Prompt

将下面内容直接交给 OMC / Claude Code。

---

Use the available OMC team capabilities to implement the IBS (Intent / Behavior / Structure) output system for Semantic Harness.

Do not expand scope beyond IBS implementation.

Use these files as the source of truth:

- docs/review/ibs_requirements_and_constraints.md
- docs/review/ibs_implementation_plan.md
- docs/review/ibs_stage_acceptance_checklist.md
- docs/review/ibs_team_execution_model.md

Execution mode:

- Use OMC team capabilities as needed
- Do not assume specific named agents unless they are actually available
- Select appropriate roles/tasks dynamically for:
  - analysis
  - implementation
  - testing
  - review
  - documentation

Execution order:

Phase 1 — IBS Contract
Phase 2 — Core Baseline
Phase 3 — Intent Pack
Phase 4 — Behavior Pack
Phase 5 — Structure Pack
Phase 6 — Regression and Validation

Global constraints:

1. Execute phases sequentially without waiting for manual confirmation.
2. For each phase, you must:
   - analyze the required changes
   - implement the phase
   - add or update tests
   - run the relevant tests
   - run full pytest
   - perform review
   - fix any issues found
   - run tests again
   - generate the required phase report under docs/review/
   - create a git commit
3. Do not redesign the existing runtime architecture.
4. Do not change the public skill set.
5. Do not migrate docs/semantic paths.
6. Prefer minimal safe changes.
7. Do not introduce new external dependencies.
8. If a phase is too large, use staged rollout, but clearly record:
   - what was completed
   - what was deferred
   - why it was deferred

Minimum required delivery:

Core Baseline:
- purpose.md
- pipelines.md
- domains.md
- concepts.md

Minimum Analysis Pack:
- goals.md
- constraints.md
- workflows.md
- inputs-outputs.md
- components.md
- boundaries.md

Required reports:

- docs/review/ibs_stage1_contract_report.md
- docs/review/ibs_stage2_core_report.md
- docs/review/ibs_stage3_intent_report.md
- docs/review/ibs_stage4_behavior_report.md
- docs/review/ibs_stage5_structure_report.md
- docs/review/ibs_stage6_regression_report.md
- docs/review/ibs_implementation_final_report.md

Commit message convention:

- ibs: stage1 output contract and templates
- ibs: stage2 core baseline generation
- ibs: stage3 intent analysis pack
- ibs: stage4 behavior analysis pack
- ibs: stage5 structure analysis pack
- ibs: stage6 regression and validation hardening

Final output requirements:

After all phases are complete, provide one consolidated final summary including:

1. phases completed
2. files modified
3. files created
4. tests added
5. commits created
6. deferred items
7. remaining risks
8. final verdict

Only stop after all phases complete.
