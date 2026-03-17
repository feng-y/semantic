# Semantic Layer Review — 2026-03-17

## 前置：架构上下文（需先理解才能正确评审）

**整个 sematic-harness repo 是一个 Claude Code skill 插件**，由宿主 repo 安装后在 Claude Code (CC) 环境中执行。

执行模型：
- Claude Code 读取 SKILL.md 的 prompt 指令
- Claude Code 自身（LLM）做推断、合成、决策
- `src/semantic/` Python 脚本作为 CLI 工具被 Claude Code 调用，负责结构化 I/O、校验和持久化
- Python 代码不需要包含"智能逻辑"——智能来自 Claude Code 执行 prompt

**本报告包含初次评审的误判记录及修正。**

---

## 误判记录

### 误判 1（部分修正）：`build_candidates.py` 硬编码名字

**初次判断**：`synthesize_domain_candidates` 把信号映射为硬编码名字，认为合成逻辑需要重写。

**误判原因**：没有理解 CC 执行模型。Python 脚本是 CC LLM 输出的校验/持久化层，不需要自己做合成推理。

**进一步修正（用户反馈）**：虽然 Python 不做合成，但硬编码占位值**仍然是 bug**——当 CC 输出不符合预期时，脚本不应静默降级填入占位字符串，而应明确报错，让流水线 fail fast。详见「问题 0」。

---

### 误判 2：认为 `apply_review.py` 的透传是设计空缺

**初次判断**：`convert_to_review_decision` 直接 `final_action = rec_action`，100% 透传推荐结果，认为"Review 步骤没有独立决策逻辑"是设计问题。

**误判原因**：同上。Review 步骤的决策逻辑在 SKILL.md 的 prompt 里由 Claude Code 执行，Python 脚本负责把 CC 的决策输出结构化存储。透传本身是正确的——CC 已经做了决策，Python 只是格式化。

**修正**：不是 bug。关闭。

---

### 误判 3：认为"整个 semantic 层没有版本化产物管理"是问题

**初次判断**：与 FACT 层的 `vN.md` 版本控制对比，认为 semantic 层缺少版本历史是缺陷。

**用户修正**：没必要。semantic 层的产物（signals.yaml、candidates.yaml 等）是中间过程数据，FACT 层的基线才是需要版本管理的最终产物。

**修正**：设计决策正确。关闭。

---

## 有效问题（保留）

### 🔴 高优先级

#### 问题 0：Fallback 占位值掩盖 CC 推理错误 — 应改为 fail fast

**位置**：`build_candidates.py`、`finalize_assets.py`、`extract_signals.py` 多处

Python 脚本是 Claude Code LLM 输出的**下游校验层**。若 CC 推理结果不符合预期（字段缺失、格式错误），脚本不应用占位值降级运行，应 **明确抛出错误**，让流水线 fail fast，迫使 CC 重新推理或人工介入。

当前反例：

```python
# build_candidates.py — 不管 CC 给什么 signal，都生成同一个硬编码候选
'name': 'Repository Structure',  # 应校验 signal 包含预期字段，否则 raise

# finalize_assets.py — CC 没提供 summary 时静默造占位字符串
'summary': f"Domain: {decision['name']}",  # 应 raise 或透传真实 summary

# extract_signals.py — 可选输入缺失只 WARNING，继续运行
if not working:
    print("WARNING: ...missing")  # 若此输入为必须，应 raise
```

**正确做法**：
- 必要字段缺失 → `raise ValueError("CC output missing required field 'summary'")`
- 不要用 `.get('field', 'default')` 掩盖结构错误
- 测试环境可用 `pytest.raises` 验证错误路径

**修复成本**：低（在各 `main()` 入口加输入 schema 校验），但**优先级最高**，是数据质量的安全网。

---

### 🟡 中优先级

#### 问题 1：`extract_signals.py` 依赖 `_sample` 文件，FACT → Semantic 数据接口未定义

**位置**: `src/semantic/extract_signals.py:16-28`

```python
canonical_path = fact_root / "fact_canonical_sample.yaml"       # _sample 后缀
working_path   = fact_root / "fact_working_summary_sample.yaml"  # _sample 后缀
```

当前 semantic 层读的是示例文件，而非真实 FACT 流水线产出（`docs/fact/baseline/` 下的 `purpose.md`、`domains.md` 等）。两层之间没有明确的数据接口契约。

**影响**：semantic 层无法在真实场景下运行，只能在沙盒数据上工作。

**修复成本**：中（需先定义 FACT → Semantic 的数据接口规范，再更新读取路径）。

---

### 🟢 低优先级

#### 问题 2：`rec_type` 用 `rstrip('s')` 截取，脆弱

**位置**: `apply_review.py:79`、`evidence_check.py:63`

```python
rec_type = group_name.rstrip('s')  # 'domains'→'domain' ✓ 但依赖字符串巧合
```

**修复**：换成显式映射 dict，5 行改动。

---

#### 问题 3：`render_markdown` 只渲染第一个匹配的 key，change-log 渲染为空

**位置**: `finalize_assets.py:83-89`

```python
items_key = 'domains' if 'domains' in data else 'concepts' if ...
# change-log 的 data 有 {added, merged, dropped, deferred}，全部命中 None
```

change-log 的 markdown 文件会生成但内容为空（只有标题和时间戳）。

**修复**：按实际 data 结构分支渲染，约 15 行改动。

---

#### 问题 4：`run.py` finalize 门控逻辑在 `next` 和 `all` 两个分支中完全重复

**位置**: `src/semantic/run.py:53-80` 和 `93-119`

同样的 `verify_first` 检测写了两遍（约 25 行重复）。

**修复**：提取 `_check_finalize_guard(workspace)` 函数，纯重构，约 30 min。

---

## 总结

| 级别 | 有效问题数 | 说明 |
|---|---|---|
| 🔴 高 | 1 | Fallback 占位掩盖 CC 推理错误，应 fail fast（补充发现） |
| 🟡 中 | 1 | FACT → Semantic 数据接口缺失 |
| 🟢 低 | 3 | 机械性改动，合计约 1.5 小时 |

**最优先处理**：问题 0（fail fast 原则），问题 1（数据接口），其余 3 条可随时修复。


---

### 误判 2：认为 `apply_review.py` 的透传是设计空缺

**初次判断**：`convert_to_review_decision` 直接 `final_action = rec_action`，100% 透传推荐结果，认为"Review 步骤没有独立决策逻辑"是设计问题。

**误判原因**：同上。Review 步骤的决策逻辑在 SKILL.md 的 prompt 里由 Claude Code 执行，Python 脚本负责把 CC 的决策输出结构化存储。透传本身是正确的——CC 已经做了决策，Python 只是格式化。

**修正**：不是 bug。关闭。

---

### 误判 3：认为"整个 semantic 层没有版本化产物管理"是问题

**初次判断**：与 FACT 层的 `vN.md` 版本控制对比，认为 semantic 层缺少版本历史是缺陷。

**用户修正**：没必要。semantic 层的产物（signals.yaml、candidates.yaml 等）是中间过程数据，FACT 层的基线才是需要版本管理的最终产物。

**修正**：设计决策正确。关闭。

---

## 有效问题（保留）

### 🔴 高优先级

无。初次标记的两个高优先级问题均为误判（见上）。

---

### 🟡 中优先级

#### 问题 1：`extract_signals.py` 依赖 `_sample` 文件，FACT → Semantic 数据接口未定义

**位置**: `src/semantic/extract_signals.py:16-28`

```python
canonical_path = fact_root / "fact_canonical_sample.yaml"       # _sample 后缀
working_path   = fact_root / "fact_working_summary_sample.yaml"  # _sample 后缀
```

当前 semantic 层读的是示例文件，而非真实 FACT 流水线产出（`docs/fact/baseline/` 下的 `purpose.md`、`domains.md` 等）。两层之间没有明确的数据接口契约。

**影响**：semantic 层无法在真实场景下运行，只能在沙盒数据上工作。

**修复成本**：中（需先定义 FACT → Semantic 的数据接口规范，再更新读取路径）。

---

### 🟢 低优先级

#### 问题 2：`rec_type` 用 `rstrip('s')` 截取，脆弱

**位置**: `apply_review.py:79`、`evidence_check.py:63`

```python
rec_type = group_name.rstrip('s')  # 'domains'→'domain' ✓ 但依赖字符串巧合
```

**修复**：换成显式映射 dict，5 行改动。

---

#### 问题 3：`render_markdown` 只渲染第一个匹配的 key，change-log 渲染为空

**位置**: `finalize_assets.py:83-89`

```python
items_key = 'domains' if 'domains' in data else 'concepts' if ...
# change-log 的 data 有 {added, merged, dropped, deferred}，全部命中 None
```

change-log 的 markdown 文件会生成但内容为空（只有标题和时间戳）。

**修复**：按实际 data 结构分支渲染，约 15 行改动。

---

#### 问题 4：`run.py` finalize 门控逻辑在 `next` 和 `all` 两个分支中完全重复

**位置**: `src/semantic/run.py:53-80` 和 `93-119`

同样的 `verify_first` 检测写了两遍（约 25 行重复）。

**修复**：提取 `_check_finalize_guard(workspace)` 函数，纯重构，约 30 min。

---

#### 问题 5：`finalize_assets.py` — `finalize_domain/concept/rule` 的 summary 字段

**位置**: `finalize_assets.py:26,35,46`

```python
'summary': f"Domain: {decision['name']}",  # 信息量为零
```

若 Claude Code 在调用前已在 decision 数据里生成了有意义的 summary，Python 应透传而非重造。

**修复**：需先确认 SKILL.md prompt 的输出 schema 是否包含 summary 字段，若包含则改为透传。

---

## 总结

| 级别 | 有效问题数 | 说明 |
|---|---|---|
| 🔴 高 | 0 | 初次标记的 2 条均为误判 |
| 🟡 中 | 1 | FACT → Semantic 数据接口缺失 |
| 🟢 低 | 4 | 机械性改动，合计约 2 小时 |

**最优先处理**：问题 1（数据接口），其余 4 条可随时修复。
