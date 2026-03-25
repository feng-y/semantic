# Autoresearch Config

## Target
- `skills/commit-extract/prompt.md`

## Workspace
- `autoresearch-commit-extract/`

## Dataset
- Fixed 13-commit DaVinci evaluation set
- Repo: `/Users/yan./git/b/DaVinci`
- Commits:
  - `fb3c317fe834dbeb349981951014e6be5e1773b0` — high
  - `686e0b5e8fd8ee3d1f3d1d6e1d0ccd71f80eb1a2` — high
  - `c599c1db491b3b55bbf2735fb43a49aa51e419a6` — high
  - `45c20e42e9a07d3886acb4a8d1d1858c973d663d` — medium
  - `5db79af3e46c5812763811c351a8e7b1b19fb48b` — medium
  - `24bde3a06110fd6d78f35f60db478fe838520e8d` — medium
  - `81623076538b57f9480981a5c01aac23ce1c19af` — medium
  - `7123b0fd74f1ff5a898b22370d429f0290e09087` — medium
  - `d1db872d8f0c1f3caa467b170bae94f921e54fc3` — medium
  - `b87dc9debff287ff1c4232d03ac74be6b300e8e0` — medium
  - `fc5a98f072b5502cd406e49502fafbfd02cf1fe9` — weak
  - `14bc69c445717b5cb2df67f4c413ac9368a0e6e3` — weak
  - `2482114fe70fdb461ac65beeffc2b0994f1a514f` — weak

## Evals
- `system_object_clarity`
- `behavior_vs_config`
- `semantic_density_gate`
- `prose_avoidance`
- `section_naming_accuracy`
- `rule_presence_when_warranted`
- `rule_abstraction_level`
- `rule_non_duplication`
- `rule_selectivity`

Detailed definitions live in `evals/evals.md`.

## Eval intent
- `system_object_clarity`: sections should name a real subsystem or functional object
- `behavior_vs_config`: items should describe behavior/capability, not patch/config narration
- `semantic_density_gate`: low-semantic docs/config commits should not be over-extracted
- `prose_avoidance`: avoid release-note style wording and editorial narration
- `section_naming_accuracy`: section names should match the actual semantic content
- `rule_presence_when_warranted`: relevant commits should emit rules when reusable constraints are clearly introduced
- `rule_abstraction_level`: rules should stay abstract and reusable rather than patch-specific
- `rule_non_duplication`: rules should not paraphrase section items
- `rule_selectivity`: weak/docs/config commits should not get forced rules

## Current scoring policy
- Binary evals only
- Same 13 commits every iteration
- Same eval set every iteration unless explicitly revised
- Total score = sum of eval passes across all commits
- Current max score = `13 commits × 9 evals = 117`
- `invariant_quality` is deprecated and replaced by the four rule-focused sub-evals above

## Stop Conditions
- Default mode: one iteration only
- If score does not improve, discard mutation
- If two consecutive iterations fail to improve, pause and reassess eval design
- If weakest eval changes materially, update `STATE.md` before next run

## Boundaries
- Do not change dataset unless explicitly requested
- Do not change eval definitions unless explicitly requested
- Do not auto-commit unless explicitly requested
- Do not auto-push unless explicitly requested
- One mutation per iteration
- Prefer editing only `skills/commit-extract/prompt.md`
