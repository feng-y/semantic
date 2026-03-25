# Autoresearch Skill Structure

This skill uses the following directory layout:

- `SKILL.md` — entrypoint, trigger guidance, workflow, and boundaries
- `references/` — detailed supporting docs loaded only when needed
- `scripts/` — deterministic helpers for workspace setup, scoring, and result processing
- `assets/templates/` — reusable templates for `config.md`, `STATE.md`, and related files
- `assets/prompts/` — reusable evaluator / diagnoser / mutation / judge prompt fragments
- `assets/examples/` — examples of workspace structure and expected outputs

The skill package defines the method.
User/project workspaces (for example `autoresearch-commit-extract/`) store the state and experiment history.
