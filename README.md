# semantic-harness

Claude Code skill repository for extracting structured semantic knowledge from a codebase and its git history.

## Five Capabilities

| # | Capability | Command | Status |
|---|-----------|---------|--------|
| 1 | **fact** — repo structure discovery | `/semantic-fact-pipeline` | stable |
| 2 | **semantic** — domain extraction | `/semantic-pipeline` | stable |
| 3 | **demand** — requirement mapping | `/demand-pipeline` | stable |
| 4 | **commit-semantic** — git history → domain cases | `/commit-semantic-pipeline` | stable |
| 5 | **semantic-extract** — commit + rules/invariants | `/semantic-extract` | stable |

Each capability is independent. Use them in order for a full picture, or run any one standalone.

---

## Quick Start

```bash
git clone <repo-url> && cd semantic-harness
pip install -e ".[test]"
pytest tests/test_commit_semantic_logic.py tests/test_grouping_boundaries.py -q
```

---

## Capabilities

### 1. fact — Repo Structure Discovery

Samples the repo, extracts facts, identifies domains and concepts. Produces a versioned semantic baseline in `docs/fact/`.

**Pipeline:**
```
/semantic-fact-pipeline    # discover → review → refine → baseline
```

**Individual steps:**
```
/semantic-init        # create workspace
/semantic-discover    # run discovery pipeline
/semantic-review      # architect reviews artifacts
/semantic-refine      # patch with feedback
/semantic-baseline    # accept and lock baseline
/semantic-status      # check current state
/semantic-reset       # reset working state (keeps baseline)
```

---

### 2. semantic — Domain Extraction

Builds a semantic layer on top of the fact baseline: signals → candidates → recommendations → review → finalized assets.

**Pipeline:**
```
/semantic-pipeline     # signals → candidates → recommend → review → finalize
```

**Individual steps:**
```
/semantic-signals      # stage 1: extract signals from facts
/semantic-candidates   # stage 2: synthesize candidates
/semantic-recommend    # stage 3: score and recommend
/semantic-review       # stage 4: review decisions
/semantic-finalize     # stage 5: finalize asset maps
```

Requires: fact baseline accepted (`/semantic-baseline` completed).

---

### 3. demand — Requirement Mapping

Maps incoming issue text to semantic assets. Normalizes → maps → matches → builds demand card → validates.

**Pipeline:**
```
/demand-pipeline      # issue_text → demand card (one-shot)
```

Requires: semantic assets from capability 2.

---

### 4. commit-semantic — Git History → Domain Cases

Extracts structured semantic cases from git commit history. Produces deduplicated, pattern-aggregated case libraries for few-shot samples, rule extraction, and training data.

**Pipeline:**
```
/commit-semantic-pipeline 最近 50 个 commit
/commit-semantic-pipeline HEAD~100..HEAD，排除 config 目录
/commit-semantic-pipeline 最近一个月，增量模式
```

**Individual steps:**
```
/commit-semantic-collect   # git history → semantic_case_inputs/
/commit-semantic-generate  # semantic_case_inputs/ → semantic_cases/
/commit-semantic-export    # semantic_cases/ → exports/ (dedup + patterns)
```

**Python API:**
```python
from src.commit_semantic.pipeline import run_pipeline
run_pipeline(repo_path=".", commit_range="HEAD~50..HEAD", executor=my_llm)
```

→ Details: `README-commit-semantic.md`, `docs/commit-semantic/user-guide.md`

---

### 5. semantic-extract — Commit + Rules/Invariants

统一提取 commit 功能语义和工程化约束，通过 SHA 关联。

```
/semantic-extract --last 10 --view both
```

Output: `data/commit_refine/` + `data/rules_invariants/`

详见 `docs/plan/rule.md`。

---

## Repository Layout

```
skills/                    # skill definitions (SKILL.md per skill)
  semantic-fact-pipeline/  # capability 1 pipeline
  semantic-pipeline/       # capability 2 pipeline
  demand-pipeline/         # capability 3 pipeline
  commit-semantic-pipeline/# capability 4 pipeline
  semantic-extract/        # capability 5: commit + rules extraction
  semantic-*/              # fact + semantic individual skills
  commit-semantic-*/       # git history individual skills

src/                       # Python runtime
  semantic/                # semantic layer implementation
  commit_semantic/         # commit-semantic implementation
  dispatcher.py            # skill routing

prompts/                   # LLM prompt files

docs/
  commit-semantic/         # commit-semantic user guide + skills reference
  demand/                  # demand pipeline design
  fact/                    # schemas, templates, generated state
  semantic-design/         # architecture decision records (001–010)

data/                      # runtime output (gitignored)
  semantic_case_inputs/
  semantic_cases/
  exports/
```

---

## Documentation

- `README-commit-semantic.md` — commit-semantic quick start and CLI reference
- `docs/commit-semantic/user-guide.md` — CC skill usage (natural language invocation)
- `docs/commit-semantic/skills-reference.md` — skill interface contracts
- `docs/semantic-design/` — architecture decision records
- `docs/demand/` — demand pipeline design docs
- `docs/plan/rule.md` — rules/invariants 规范定义
