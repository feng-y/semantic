# Semantic Harness — Code Review

总体评价：整体设计思路清晰，分层合理，关键路径（版本化、原子写入、基线门控）有良好的防护。以下按优先级列出改进意见。

---

## 🔴 高优先级（正确性 / 潜在 Bug）

### 1. `_next_version` 的锁文件残留问题

**位置**: [`artifact_writer.py:65-91`](file:///Users/yan./git/3p/sematic-harness/src/artifact_writer.py#L65-L91)

`_next_version` 用 `O_CREAT | O_EXCL` 创建空锁文件来"占位"，注释说"lock file is left in place; the caller will overwrite it"——但调用方 `write_artifact` 用的是 `_atomic_write`（write-then-rename），**rename 目标恰好是锁文件本身，所以是安全的**。
然而，如果 `_atomic_write` 中途抛异常（例如磁盘满），锁文件将永远留在磁盘上，下次 `_find_versions` 会把它扫描到（文件存在但为空），导致 `get_latest_version_path` 的 **`st_size > 0` 过滤**跳过它，版本号仍然"被消耗"但内容丢失。

**改进方向**:
- `get_latest_version_path` 已做 `st_size > 0` 的空文件过滤，但 `_find_versions`（被 `_next_version` 调用计算下一版本号）**不过滤空文件**，已占位的版本号会被跳过而不是重用，造成版本号空洞（v1, v3, v5...）。虽然功能不影响，但会使版本号快速增长。建议在 `_find_versions` 或 `_next_version` 中跳过空文件。

---

### 2. `plugin.json` 用 `yaml.safe_load` 解析而非 `json.loads`

**位置**: [`skill_loader.py:135`](file:///Users/yan./git/3p/sematic-harness/src/skill_loader.py#L135)

```python
plugin_data = yaml.safe_load(plugin_json_path.read_text())
```

`plugin.json` 是 JSON 文件，虽然 YAML 超集能解析合法 JSON，但：
- 错误信息会显示 "Invalid JSON... YAML error"，令人困惑
- 代码注释也写着 `# Invalid JSON in {plugin_json_path}: {e}`，与实际行为矛盾

**改进**: 改用 `json.loads`，错误信息才能准确反映格式要求。

---

### 3. `_find_bullets_after_label` 中的越界访问

**位置**: [`change_analysis_generator.py:116`](file:///Users/yan./git/3p/sematic-harness/src/change_analysis_generator.py#L96-L119)

```python
for nxt in lines[i + 1:]:
    ...
    if re.match(r"^\s*[-*]?\s*[A-Za-z].*:\s*", nxt):
        break
    break  # ← 非 bullet 非 header 直接 break，逻辑存在歧义
```

内层 `break` 语义不清晰：遇到任何非 bullet 行都终止（无论是空行、纯文本还是子标题），但空行已在前面 `if not nxt.strip(): continue` 被跳过，那么实际上一遇到非 bullet 非 header 非空行就会 break，逻辑正确但可读性极差。建议用 `else` 分支或更明确的条件替代。

---

## 🟡 中优先级（设计改进）

### 4. `artifact_validation.py` 中的验证强度过低

**位置**: [`artifact_validation.py`](file:///Users/yan./git/3p/sematic-harness/src/artifact_validation.py)

所有验证器的逻辑是 **"包含至少一个预期章节标题之一"**（`_has_any_section_heading`，OR 逻辑），意味着：
- 只需要 `## Repository` 就能通过 `validate_repo_facts`，即使缺少 `## Modules`、`## Core Entities` 等
- `validate_domain_candidates` 的 `DOMAIN_CANDIDATES_SECTIONS` 只有一个元素 `("Candidate Domains",)`，其实等同于"必须有这一节"

**改进建议**:
- 对"必须都有"的章节（如 `repo-facts` 的 5 个节）使用 AND 逻辑，或者区分 `required_sections`（AND）和 `optional_sections`（OR）
- 当前设计对 LLM 输出质量要求极低，容易接受结构不完整的产物

---

### 5. `VALIDATION_STEP_TARGETS` 硬编码在 `discovery_executor.py`

**位置**: [`discovery_executor.py:64-67`](file:///Users/yan./git/3p/sematic-harness/src/discovery_executor.py#L64-L67)

```python
VALIDATION_STEP_TARGETS = {
    3: "repo-facts",         # 依赖步骤绝对索引
    6: "repo-understanding",
}
```

验证目标与**步骤的绝对索引**绑定，一旦 `SKILL.md` 中的 steps 顺序调整（增删或重排），验证会静默地映射到错误的产物，或完全不触发（代码走 `"No validation target mapped for this step"` 分支）。

**改进建议**: 在 `SKILL.md` 的步骤中增加 `validate: <artifact-name>` 字段，让验证目标随步骤声明走，而不依赖硬编码位置。

---

### 6. 两个流水线层之间缺乏明确的集成边界

**设计层面**

FACT 层（`dispatcher` → `discovery_executor` / `refine_executor`）与 Semantic 层（`src/semantic/`）之间**没有程序化接口**：
- Semantic 层从 FACT `baseline/` 目录读文件，但没有正式的"FACT 已完成基线"事件或状态检查
- `semantic/run.py` 的状态机（`run-state.yaml`）与 FACT 层的 `state_inspector` 完全独立
- `semantic/extract_signals.py` 读的是 `fact_canonical_sample.yaml`（带 `_sample` 后缀），看起来是开发期占位文件而非真实产出

**改进建议**:
- 明确 FACT baseline 完成后的激活条件（如检查 `baseline/checkpoint.json` 存在且完整）
- 移除 `_sample` 后缀文件依赖，改为读真实的 FACT 输出
- 或在 README 中显式说明两层的集成方式，目前文档对此没有任何描述

---

### 7. `refine_executor._execute_patch_step` 是孤立的死代码

**位置**: [`refine_executor.py:312-361`](file:///Users/yan./git/3p/sematic-harness/src/refine_executor.py#L312-L361)

`run_refine()` 已改用 `_execute_staged_patches()`（原子提交两个产物），但 `_execute_patch_step()` 仍然保留，没有任何调用者。

**改进**: 删除该函数，或注明其为保留的单产物补丁接口。

---

## 🟢 低优先级（可读性 / 健壮性）

### 8. `context_builder` 中存在循环导入规避（惰性导入）

**位置**: [`context_builder.py:271`](file:///Users/yan./git/3p/sematic-harness/src/context_builder.py#L259-L272)

```python
def _get_artifact_validator(name: str):
    # Lazy import to break circular: context_builder <- discovery_executor
    from .discovery_executor import validate_artifact_content
    return validate_artifact_content
```

用惰性导入解决循环依赖是临时手段，说明两模块之间存在不合理的耦合。`validate_artifact_content` 本质上属于 `artifact_validation.py`，但 `discovery_executor` 又在其基础上增加了分发逻辑。

**改进建议**: 将 `validate_artifact_content` 的分发逻辑移入 `artifact_validation.py`，从根本上消除循环依赖。

---

### 9. `_check_sampling_timeout` 对 `result.sampling_mode` 的更新时机

**位置**: [`discovery_executor.py:441-448`](file:///Users/yan./git/3p/sematic-harness/src/discovery_executor.py#L437-L448)

```python
effective_mode, switched = _check_sampling_timeout(
    start_time, sampling_timeout, result.sampling_mode,
)
if switched:
    result.sampling_mode = effective_mode
    result.sampling_mode_switched = True
# 后续仍用 result.sampling_mode，正确
```

逻辑正确，但 `_check_sampling_timeout` 每步都判断一次，一旦切换后传入的是已更新的 `result.sampling_mode == "confirm"`，`sampling_mode != "auto"` 会直接返回 `confirm, False`，不会重复设置 `sampling_mode_switched = True`。行为正确但不够直观，建议加注释说明。

---

### 10. 测试中的重复代码

**位置**: `tests/` 目录

`test_system.py`（24KB）、`test_step8_verification.py`（26KB）中存在大量重复的 `tmp_path` 初始化、`fake_executor` 构建样板。建议提取为 `pytest fixture`，集中在 `conftest.py` 管理，提升可维护性。

---

## 📌 小结

| 级别 | 问题 | 数量 |
|------|------|------|
| 🔴 高 | 正确性风险、误导性错误信息 | 3 |
| 🟡 中 | 设计缺陷、死代码、层间耦合 | 4 |
| 🟢 低 | 可读性、测试卫生 | 3 |

**最优先建议处理**：
1. 第 5 条（`VALIDATION_STEP_TARGETS` 硬编码索引）—— 最容易因维护操作引入静默 bug
2. 第 4 条（验证强度太低）—— 决定了整条流水线的输出质量下限
3. 第 2 条（JSON 用 YAML 解析）—— 一行修复，改善调试体验
