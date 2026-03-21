# Tech Debt Tracker

Prioritized list of known technical debt. Lower ID = higher priority.

## P0 — Must Fix

*(No P0 items currently known)*

## P1 — High Priority

| ID | Description | Location | Impact | Notes |
|----|-------------|----------|--------|-------|
| T001 | Capability 3 (demand-pipeline) marked "in progress" | `README.md`, `src/demand/` | Users see incomplete feature | ✅ Completed: missing `skills/demand-pipeline/run.py` created, pipeline tested, status → stable |
| T002 | Some skills still use legacy naming (semantic-*) | `skills/` directory | Inconsistent skill names | Planned: rename per migration docs |
| T003 | mypy added to pyproject.toml | `pyproject.toml` | Runtime errors | ⚠️ Configured; existing errors not fixed yet (50 errors in 24 files). See T003-detail below. |
| T004 | ruff lint added to CI | `pyproject.toml`, `.github/workflows/ci.yml` | Code style drift | ✅ CI gate active. `E,F` rules enforced on src/; tests/ excluded. |

## P2 — Medium Priority

| ID | Description | Location | Impact | Notes |
|----|-------------|----------|--------|-------|
| T005 | `schemas/` has `demand/demand-card.schema.json` | `schemas/` | Only demand schema present | Update T002/T005 or consolidate |
| T006 | `templates/` has 13 files (fact/semantic/demand) | `templates/` | Rich template set exists | Useful, no action needed |
| T007 | 3 legacy `.skill` files in `skills/legacy/` | `skills/legacy/` | Migration burden | Migrate or delete |
| T008 | `docs/archive/` is large and inactive | `docs/archive/` | Context noise for agents | Archive aggressively |

## P3 — Low Priority / Nice to Have

| ID | Description | Location | Impact | Notes |
|----|-------------|----------|--------|-------|
| T009 | `data/` directory mostly empty | `data/` | Unclear purpose | Document expected contents |
| T010 | `scripts/` has only validate_e2e_real.py | `scripts/` | Minimal scripts | Consider adding utility scripts |
| T011 | Test coverage unknown | `tests/` | Blind spots | Add coverage reporting |
| T012 | No benchmark/performance tests | (none) | No perf regression detection | Add timing tests if useful |

---

**Maintenance**: Run `grep -r "TODO\|FIXME\|XXX" src/ tests/` quarterly to surface new debt.
