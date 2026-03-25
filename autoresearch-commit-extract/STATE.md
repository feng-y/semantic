# Autoresearch State

## Target
- `skills/commit-extract/prompt.md`

## Workspace
- `autoresearch-commit-extract/`

## Dataset
- 13 fixed DaVinci commits
- Quality mix: 3 high / 7 medium / 3 weak
- Purpose: stress semantic extraction quality across rich mixed commits, config-heavy commits, docs commits, and low-semantic commits

## Current Baseline
- `67/78 (85.9%)`

## Eval Summary
- `system_object_clarity`: `13/13`
- `behavior_vs_config`: `12/13`
- `semantic_density_gate`: `12/13`
- `prose_avoidance`: `12/13`
- `section_naming_accuracy`: `13/13`
- `rule_presence_when_warranted`: `unknown` (not yet rescored)
- `rule_abstraction_level`: `unknown` (not yet rescored)
- `rule_non_duplication`: `unknown` (not yet rescored)
- `rule_selectivity`: `unknown` (not yet rescored)

## Weakest Eval
- `rule_*` metrics not yet baselined; next step is to rescore the 13 commits using the split rule evals

## Last Kept Mutation
- Added anti-patterns banning generic section names such as `Code changes`, `Configuration behavior`, `Runtime behavior`, `Observability`, and unqualified `Operations`

## Known Good Directions
- Explicit anti-patterns help section naming
- Stronger section naming constraints improve system object clarity
- The current prompt already handles generic naming and prose reasonably well
- The current prompt is much stronger than the removed `docs/generate_commit.md` variant

## Known Risks
- Overfitting weak/docs/config commits by forcing fake semantic rules
- Increasing rule count without improving rule abstraction
- Duplicating section items inside `rules_invariants`
- Trading semantic selectivity for score gaming
- Making the prompt too heavy and causing brittle / unstable extraction behavior

## Current Failure Shape
- Many commits still omit `rules_invariants` entirely
- Some commits that probably warrant rules do not emit them
- Some low-semantic commits should remain rule-light or rule-free
- One large aggregate commit (`fb3c317fe834`) produced JSON truncation / parse instability during baseline testing and may need a more robust extraction harness
- A discarded experiment that added heavy rule guidance reduced total score and increased instability

## Next Hypothesis
- First, baseline the split rule evals across the same 13 commits:
  - `rule_presence_when_warranted`
  - `rule_abstraction_level`
  - `rule_non_duplication`
  - `rule_selectivity`
- Then target the weakest rule-specific sub-eval with a smaller mutation instead of trying to improve all rule behavior at once
