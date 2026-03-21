# Phase 2: Semantic-Fact Implementation Plan

> **Goal:** Create `/semantic-fact` skill with full E2E validation and upstream dependency checking.

**验收标准（必须全部满足）:**
- [ ] E2E 测试覆盖 5 个 intent (run/status/step/resume/reset)
- [ ] 前置依赖验证 (检查 fact baseline 是否存在)
- [ ] 下游输出验证 (semantic-fact 输出可被 semantic 消费)
- [ ] ruff/mypy 零错误
- [ ] 所有测试通过

---

## Task 1: Create Semantic-Fact Skill Structure

**Files:**
- Create: `skills/semantic-fact/SKILL.md`
- Create: `skills/semantic-fact/run.py`

**Stag定义:**
```python
STAGES = ["discover", "review", "refine", "baseline"]
```

**前置依赖检查:**
- 检查 `docs/fact/baseline/` 是否存在 accepted baseline
- 若无，返回错误提示用户先完成 fact pipeline

**实现方式:**
- 继承 `SkillRunner` 基类
- `run_stage()` 内部调用 `src/dispatcher.py` 的 `dispatch()`
- 将 dispatcher 返回的 dict 存入 state.metadata

**Step-by-Step:**
- [ ] Write SKILL.md with correct state.json path
- [ ] Write run.py with prerequisite check
- [ ] Manual test: run/status/step/resume/reset

**验证命令:**
```bash
python skills/semantic-fact/run.py status  # 应提示无 baseline
python skills/semantic-fact/run.py run     # 应有依赖错误
# 创建 mock baseline 后重试
```

---

## Task 2: E2E Tests with Dependency Validation

**Files:**
- Create: `tests/e2e/test_semantic_fact.py`

**测试场景（6个）:**

```python
def test_semantic_fact_fails_without_baseline(workspace, run_skill):
    """没有 fact baseline 时应失败并提示."""
    result = run_skill("semantic-fact", "run", cwd=workspace)
    assert result.returncode != 0
    assert "baseline" in result.stderr.lower() or "fact" in result.stderr.lower()

def test_semantic_fact_succeeds_with_baseline(workspace_with_baseline, run_skill):
    """有 baseline 时完整 pipeline 应成功."""
    result = run_skill("semantic-fact", "run", cwd=workspace_with_baseline)
    assert result.returncode == 0
    assert "Complete" in result.stdout

def test_semantic_fact_step_breakpoint(workspace_with_baseline, run_skill, load_state):
    """step 应停在 breakpoint."""
    run_skill("semantic-fact", "step", cwd=workspace_with_baseline)
    state = load_state(workspace_with_baseline, "semantic-fact")
    assert state["metadata"]["status"] == "breakpoint"

def test_semantic_fact_resume_completes(workspace_with_baseline, run_skill, load_state):
    """resume 应完成剩余 stages."""
    run_skill("semantic-fact", "step", cwd=workspace_with_baseline)
    result = run_skill("semantic-fact", "resume", cwd=workspace_with_baseline)
    assert result.returncode == 0
    state = load_state(workspace_with_baseline, "semantic-fact")
    assert len(state["metadata"]["completed_stages"]) == 4

def test_semantic_fact_reset_clears_progress(workspace_with_baseline, run_skill, load_state):
    """reset 应清除进度但保留 artifacts."""
    run_skill("semantic-fact", "run", cwd=workspace_with_baseline)
    run_skill("semantic-fact", "reset", cwd=workspace_with_baseline)
    state = load_state(workspace_with_baseline, "semantic-fact")
    assert state["metadata"]["completed_stages"] == []

def test_semantic_fact_output_compatible_with_semantic(workspace_with_baseline, run_skill):
    """输出格式应可被 semantic skill 消费."""
    run_skill("semantic-fact", "run", cwd=workspace_with_baseline)
    # 验证输出文件存在且格式正确
    output_path = workspace_with_baseline / ".harness/outputs/semantic-fact"
    assert (output_path / "semantic-signals.yaml").exists()
```

**Fixture 需求:**
- `workspace_with_baseline`: 创建临时 workspace 并初始化 fact baseline

---

## Task 3: Upstream/Downstream Validation

**上游依赖 (Input):**
- Fact baseline: `docs/fact/baseline/repo-facts.v*.md`
- Schema: `docs/fact/schemas/`

**验证逻辑:**
```python
def check_fact_prerequisites() -> tuple[bool, str]:
    baseline_dir = Path("docs/fact/baseline")
    if not baseline_dir.exists():
        return False, "Fact baseline not found. Run /semantic-fact-pipeline first."

    baseline_files = list(baseline_dir.glob("*.md"))
    if not baseline_files:
        return False, "No accepted baseline found. Complete fact pipeline first."

    return True, ""
```

**下游输出 (Output):**
- 格式应与现有 `semantic-pipeline` 期望的输入兼容
- 验证点: `signals/`, `candidates/`, `recommendations/` 目录结构

**验证测试:**
```python
def test_output_format_compatible():
    """验证 semantic-fact 输出可被 semantic 读取."""
    # 运行 semantic-fact
    # 然后验证 semantic 可以 load 这些文件
```

---

## Task 4: Deprecate Old Semantic-Fact Skills

**Files:**
- Modify: `skills/semantic-fact-pipeline/SKILL.md`
- Modify: `skills/semantic-discover/SKILL.md`
- Modify: `skills/semantic-refine/SKILL.md`
- Modify: `skills/semantic-baseline/SKILL.md`

**修改内容:**
在文件头部添加 deprecation 标记：
```markdown
> ⚠️ **DEPRECATED**: This skill is replaced by `/semantic-fact`.
> Use `/semantic-fact run` instead.

---

```

---

## Task 5: Regression Suite

**验证清单:**
- [ ] `pytest tests/e2e/test_semantic_fact.py -v` 全过
- [ ] `pytest tests/test_harness_state.py tests/test_intent_router.py -v` 全过
- [ ] `ruff check src/ skills/semantic-fact/` 无错误
- [ ] `mypy src/skill_runner.py` 无错误
- [ ] 手动验证: `/semantic-fact run` 在真实 repo 上运行

---

## Phase 2 Gate

| 检查项 | 要求 | 验证方式 |
|--------|------|----------|
| 功能完整 | 5 个 intent 工作 | E2E 测试 |
| 依赖验证 | 无 baseline 时失败 | E2E 测试 |
| 下游兼容 | 输出可被 semantic 消费 | 兼容性测试 |
| 代码质量 | ruff/mypy 零错误 | CI |
| 回归通过 | 现有测试不破 | pytest |

**Phase 2 完成标准:** 全部 ✅ 后方可进入 Phase 3。
