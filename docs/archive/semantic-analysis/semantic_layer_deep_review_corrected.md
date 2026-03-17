# Semantic Layer Review — 2026-03-17 (Corrected)

**Reviewer**: User + Architect
**Status**: 误判已修正

---

## 前置：架构上下文（需先理解才能正确评审）

**整个 sematic-harness repo 是一个 Claude Code skill 插件**，由宿主 repo 安装后在 Claude Code (CC) 环境中执行。

### 执行模型

- **Claude Code** 读取 SKILL.md 的 prompt 指令
- **Claude Code 自身（LLM）** 做推断、合成、决策
- **`src/semantic/` Python 脚本** 作为 CLI 工具被 Claude Code 调用，负责：
  - 结构化 I/O
  - 数据校验
  - 持久化
- **Python 代码不需要包含"智能逻辑"** — 智能来自 Claude Code 执行 prompt

**本报告包含初次评审的误判记录及修正。**

---

## 误判记录

### ❌ 误判 1：认为 `build_candidates.py` 的合成逻辑是"空壳"

**初次判断**：
> `synthesize_domain_candidates` 把信号映射为硬编码名字的候选（如 `'Repository Structure'`），认为这是设计缺失，合成逻辑需要重写。

**误判原因**：
没有理解 CC 执行模型。在 CC 环境里，Claude Code 通过 SKILL.md prompt 生成真实的候选内容（YAML），Python 脚本只是接收、校验、落盘。Python 里那些硬编码的字符串是"无 LLM 时的降级路径"或测试占位符，不是主执行路径。

**修正**：✅ 不是 bug，不需要修改。关闭。

---

### ❌ 误判 2：认为 `apply_review.py` 的透传是设计空缺

**初次判断**：
> `convert_to_review_decision` 直接 `final_action = rec_action`，100% 透传推荐结果，认为"Review 步骤没有独立决策逻辑"是设计问题。

**误判原因**：
同上。Review 步骤的决策逻辑在 SKILL.md 的 prompt 里由 Claude Code 执行，Python 脚本负责把 CC 的决策输出结构化存储。透传本身是正确的——CC 已经做了决策，Python 只是格式化。

**修正**：✅ 不是 bug。关闭。

---

### ❌ 误判 3：认为"整个 semantic 层没有版本化产物管理"是问题

**初次判断**：
> 与 FACT 层的 `vN.md` 版本控制对比，认为 semantic 层缺少版本历史是缺陷。

**用户修正**：
没必要。semantic 层的产物（signals.yaml、candidates.yaml 等）是中间过程数据，FACT 层的基线才是需要版本管理的最终产物。

**修正**：✅ 设计决策正确。关闭。

---

## ✅ 有效问题（保留）

### 🟡 中优先级

#### 问题 1：`extract_signals.py` 依赖 `_sample` 文件，FACT → Semantic 数据接口未定义

**位置**: `src/semantic/extract_signals.py:16-28`

```python
canonical_path = fact_root / "fact_canonical_sample.yaml"       # _sample 后缀
working_path   = fact_root / "fact_working_summary_sample.yaml"  # _sample 后缀
```

**问题**：
当前 semantic 层读的是示例文件，而非真实 FACT 流水线产出（`docs/fact/baseline/` 下的 `purpose.md`、`domains.md` 等）。两层之间没有明确的数据接口契约。

**影响**：
Semantic 层无法在真实场景下运行，只能在沙盒数据上工作。

**修复成本**：
中（需先定义 FACT → Semantic 的数据接口规范，再更新读取路径）。

---

### 🟢 低优先级

#### 问题 2：`rec_type` 用 `rstrip('s')` 截取，脆弱

**位置**:
- `apply_review.py:79`
- `evidence_check.py:63`

```python
rec_type = group_name.rstrip('s')  # 'domains'→'domain' ✓ 但依赖字符串巧合
```

**问题**：
凑巧现在对的，但如果 group 名称将来有变化（如 `statuses`、`aliases`），会产生错误的 `rec_type`。

**修复**：
换成显式映射 dict，5 行改动。

```python
GROUP_TO_TYPE = {
    'domains': 'domain',
    'concepts': 'concept',
    'rules': 'rule',
    'demand_models': 'demand_model'
}
rec_type = GROUP_TO_TYPE.get(group_name, group_name.rstrip('s'))
```

---

#### 问题 3：`render_markdown` 只渲染第一个匹配的 key，change-log 渲染为空

**位置**: `finalize_assets.py:83-89`

```python
items_key = 'domains' if 'domains' in data else 'concepts' if ...
# change-log 的 data 有 {added, merged, dropped, deferred}，全部命中 None
```

**问题**：
change-log 的 markdown 文件会生成但内容为空（只有标题和时间戳）。

**修复**：
按实际 data 结构分支渲染，约 15 行改动。

---

#### 问题 4：`run.py` finalize 门控逻辑在 `next` 和 `all` 两个分支中完全重复

**位置**: `src/semantic/run.py:53-80` 和 `93-119`

**问题**：
同样的 `verify_first` 检测写了两遍（约 25 行重复）。

**修复**：
提取 `_check_finalize_guard(workspace)` 函数，纯重构，约 30 min。

---

#### 问题 5：`finalize_assets.py` — `finalize_domain/concept/rule` 的 summary 字段

**位置**: `finalize_assets.py:26,35,46`

```python
'summary': f"Domain: {decision['name']}",  # 信息量为零
```

**问题**：
若 Claude Code 在调用前已在 decision 数据里生成了有意义的 summary，Python 应透传而非重造。

**修复**：
需先确认 SKILL.md prompt 的输出 schema 是否包含 summary 字段，若包含则改为透传。

---

## 总结

| 级别 | 有效问题数 | 说明 |
|---|---|---|
| 🔴 高 | 0 | 初次标记的 2 条均为误判 |
| 🟡 中 | 1 | FACT → Semantic 数据接口缺失 |
| 🟢 低 | 4 | 机械性改动，合计约 2 小时 |

**最优先处理**：问题 1（数据接口），其余 4 条可随时修复。

---

## 架构理解修正

### 正确的理解

**Semantic 层的设计是正确的**：
- Python 代码是"哑管道"（dumb pipeline）
- 智能逻辑在 Claude Code 的 prompt 执行中
- Python 负责结构化 I/O、校验、持久化

### 错误的理解（已纠正）

- ❌ 认为 Python 代码应该包含语义推断逻辑
- ❌ 认为硬编码字符串是"占位符"需要替换
- ❌ 认为透传是"缺少逻辑"

---

## 下周深读清单（更新）

基于正确的架构理解，建议深读：

### 必读（理解 CC 执行模型）
1. `skills/semantic-discover/SKILL.md` - 理解整体流程
2. `prompts/semantic/*.prompt.md` - 理解 LLM 交互逻辑
3. `src/semantic/run.py` - 理解 Python 如何调用 prompts

### 配套（理解数据流）
4. `src/semantic/extract_signals.py` - 理解输入接口
5. `src/semantic/finalize_assets.py` - 理解输出格式
6. `tests/test_semantic_*.py` - 理解预期行为

### 关键问题
7. **FACT → Semantic 数据接口** - 需要定义清楚

---

**Review 完成**: 2026-03-17
**状态**: 误判已修正，有效问题 5 个（1 中 + 4 低）

