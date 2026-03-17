# Semantic 层深度 Review

**Date**: 2026-03-17
**Reviewer**: User + Architect
**Status**: 分析确认

---

## 执行摘要

Semantic 层目前是**结构完整、语义空洞**的状态。5个步骤的数据流框架已就位，但核心转换逻辑要么是硬编码占位，要么是透传。更像一个**集成测试骨架**，需要填入真正的 LLM 推断或规则引擎。

**关键发现**: 7个高/中优先级问题，semantic 层与 FACT 层数据未连接。

---

## 🔴 高优先级问题

### 1. `build_candidates.py` — 候选合成是"伪合成"

**位置**: `src/semantic/build_candidates.py:28-66`

**问题**: 每个 synthesize 函数把一个 signal 映射成硬编码名字的 candidate

```python
def synthesize_domain_candidates(domain_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for signal in module_grouping_signals:
        candidate = {
            'id': generate_stable_id('repository_structure', 'domain'),
            'name': 'Repository Structure',   # ← 永远是这个名字
            'summary': 'Core repository organization and module structure',  # ← 硬编码
            'boundary': {'modules': ['all_modules']},  # ← 硬编码
            ...
        }
```

**影响**:
- 无论输入 signal 内容是什么，候选的 `name`、`summary`、`boundary` 都是写死的字符串
- signals → candidates 转换**不携带任何真实的语义信息**，只是形状变换
- Semantic 层的核心价值（从信号推断域/概念）在这里是空壳

**建议**:
- 需要实现真正的语义推断逻辑（LLM 或规则引擎）
- 从 signal 的实际内容中提取 name、summary、boundary
- 或者明确标记为 "placeholder implementation"

---

### 2. `apply_review.py` — Review 决策是透传，无独立逻辑

**位置**: `src/semantic/apply_review.py:27-40`

**问题**: Step 4 "Review" 100% 复制 Step 3 的 action

```python
def convert_to_review_decision(recommendation, rec_type):
    rec_action = recommendation['recommendation']['action']
    final_action = rec_action  # ← 直接复制，没有任何修改
```

**影响**:
- Review 步骤存在意义不清晰
- 如果不引入任何新判断，它只是数据格式转换层
- 本应是人工或规则驱动的修正点，但实际上是透传

**建议**:
- 明确 Review 步骤的职责：是人工审查点？还是规则验证？
- 如果是透传，考虑合并到 Step 3
- 或者实现真正的审查逻辑（规则检查、冲突解决等）

---

### 3. `rec_type` 字符串截取逻辑脆弱

**位置**:
- `src/semantic/apply_review.py:79`
- `src/semantic/evidence_check.py:63`

**问题**: 使用 `rstrip('s')` 去除复数后缀

```python
rec_type = group_name.rstrip('s')   # 'domains' → 'domain' ✓
                                     # 'rules'   → 'rule' ✓
                                     # 'demand_models' → 'demand_model' ✓
                                     # 'concepts' → 'concept' ✓
```

**风险**:
- 凑巧现在对的，但这是脆弱的字符串截取
- 如果 group 名称将来有变化（如 `statuses`、`aliases`），会产生错误的 `rec_type`
- 没有任何校验或错误处理

**建议**: 使用显式映射字典

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

## 🟡 中优先级问题

### 4. `finalize_assets.py` — `render_markdown` 只处理一个 key

**位置**: `src/semantic/finalize_assets.py:80-89`

**问题**: 链式三元表达式只处理第一个匹配的 key

```python
items_key = 'domains' if 'domains' in data else 'concepts' if 'concepts' in data \
    else 'rules' if 'rules' in data else 'demand_models' if 'demand_models' in data else None
```

**影响**:
- 如果一个 `data` dict 同时包含 `domains` 和 `concepts`，只会渲染 `domains`
- `change-log` 的 `data` 结构是 `{added, merged, dropped, deferred}`，这些 key 不在判断链里
- 导致 change-log 的 markdown 渲染为空

**建议**:
- 为不同类型的数据使用不同的渲染函数
- 或者检测数据结构类型（asset map vs change log）

---

### 5. `finalize_assets.py` — Summary 是占位字符串

**位置**: `src/semantic/finalize_assets.py:22-49`

**问题**: 最终产出的 summary 信息量为零

```python
def finalize_domain(decision: Dict) -> Dict:
    return {
        'summary': f"Domain: {decision['name']}",  # ← 信息量为零
        ...
    }

def finalize_rule(decision: Dict) -> Dict:
    return {
        'statement': f"Rule: {decision['name']}",  # ← 同上
        ...
    }
```

**影响**:
- 最终产出的 semantic asset map 里，每个 domain/concept/rule 的描述就是它自己的名字加前缀
- 对下游 Agent 消费几乎没有价值

**建议**:
- 从 decision 中提取真实的 summary/statement
- 或者从源 candidate/recommendation 中传递描述信息

---

### 6. `run.py` — `finalize` 步骤门控逻辑重复

**位置**: `src/semantic/run.py:53-80` 和 `93-119`

**问题**: 同样的 `verify_first` 检测逻辑写了两遍

**建议**: 提取成函数

```python
def check_verify_first_blocking(decisions_path, checks_path):
    """Check if there are unresolved verify_first items"""
    # ... 检测逻辑
    return has_unresolved, unresolved_items
```

---

## 🟢 低优先级问题

### 7. `extract_signals.py` — 读 `_sample` 文件，与 FACT 脱节

**位置**: `src/semantic/extract_signals.py`

**问题**: 依赖 `_sample` 后缀的示例文件

```python
canonical_path = fact_root / "fact_canonical_sample.yaml"   # 含 _sample
working_path   = fact_root / "fact_working_summary_sample.yaml"
```

**影响**:
- Semantic 层与 FACT 层**没有数据连接**
- 只能在沙盒数据上运行
- 无法处理真实的 FACT 流水线输出

**建议**:
- 修改为读取真实的 FACT 产出文件
- 或者添加参数支持两种模式（sample vs production）

---

## ~~8. 整个 semantic 层没有版本化产物管理~~ (用户确认不需要)

**用户反馈**: "semantic 我理解不要版本化"

**原因**: Semantic 层的产出可能是临时的、可重新生成的，不需要像 FACT 层那样的版本控制。

---

## 总体判断

### 当前状态
- **结构**: ✅ 完整（5个步骤清晰）
- **语义**: ❌ 空洞（核心逻辑是占位符）
- **集成**: ❌ 未连接（与 FACT 层脱节）

### 定位
更像一个**集成测试骨架**，需要填入：
1. 真正的 LLM 推断（synthesize_* 函数）
2. 规则引擎或审查逻辑（convert_to_review_decision）
3. 与 FACT 层的数据连接

### 优先级建议

**立即修复** (高优先级):
1. 修复 `rec_type` 字符串截取（安全问题）
2. 明确标记占位实现（文档/注释）

**短期改进** (中优先级):
3. 修复 `render_markdown` 的 key 处理
4. 改进 summary/statement 生成
5. 提取重复的门控逻辑

**长期规划** (低优先级):
6. 实现真正的语义推断逻辑
7. 连接 FACT 层数据
8. 明确 Review 步骤职责

---

## 下周深读清单

基于此分析，建议深读以下文件以理解 semantic 层的完整设计意图：

### 必读
1. `src/semantic/extract_signals.py` - 理解 signal 提取逻辑
2. `src/semantic/build_candidates.py` - 理解候选合成的预期行为
3. `src/semantic/generate_recommendations.py` - 理解推荐生成逻辑
4. `src/semantic/apply_review.py` - 理解审查决策流程
5. `src/semantic/finalize_assets.py` - 理解最终产出格式

### 配套
6. `src/semantic/run.py` - 理解整体流程编排
7. `src/semantic/evidence_check.py` - 理解证据检查机制
8. `tests/test_semantic_*.py` - 理解预期行为和测试覆盖

### 设计文档
9. `docs/semantic/` - 查找设计文档（如果存在）
10. `prompts/semantic/` - 查看 prompt 模板（理解预期的 LLM 交互）

---

**Review 完成**: 2026-03-17
**下一步**: 等待 Phase 2 Reviewer 报告，然后创建开发报告并 push

