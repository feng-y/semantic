# 任务优先级汇总

**更新日期**: 2026-03-17

**目标**: 将语义能力链（signals → candidates → recommend → review → finalize）转变为可靠、可控、经过验证的工作流系统

---

## 优先级总览

| 优先级 | 任务 | 工作量 | 评分 | 状态 |
|--------|------|--------|------|------|
| **P0-1** | 增量 signals 提取 | 2.5 天 | 38/50 | ⭐⭐⭐ 最高价值 |
| **P0-2** | 增强 semantic-runner | 2.5 天 | 40/50 | ⭐⭐ 核心编排 |
| **P0-3** | 增强 semantic-status | 0.5 天 | 34/50 | ⭐ 快速胜利 |
| **P1-1** | 验证层 | 1.5 天 | 34/50 | 错误预防 |
| **P1-2** | E2E 测试 | 2 天 | 35/50 | 质量保证 |
| **P1-3** | 缓存层 | 3.5 天 | 34/50 | 性能优化 |
| **P2** | 自动接受 | 2 天 | 29/50 | 暂不需要 |

**P0 总时间**: ~6 天
**P1 总时间**: ~7 天
**总计**: ~13 天

---

## P0 任务详解

### P0-1: 增量 Signals 提取 ⭐⭐⭐

#### 任务说明
实现增量执行模式，只对变更的文件重新提取 signals，复用未变更文件的缓存结果。

#### 为什么要做
1. **成本问题**: 每次全量运行消耗大量 tokens
   - 大型项目：每次运行可能花费 $10-50
   - 小改动也要全量扫描

2. **时间问题**: 全量分析耗时长
   - 大型项目：10-30 分钟
   - 影响迭代速度

3. **使用障碍**: 高成本导致用户避免重新运行
   - 发现问题后不敢修正
   - 无法快速迭代

#### 不做的后果
- ❌ 每次运行花费 $X（X 可能很大）
- ❌ 每次运行等待 Y 分钟（Y 可能很长）
- ❌ 用户因成本高而减少使用
- ❌ 无法快速迭代改进
- ❌ 成为使用的主要障碍

#### 实现方案
```python
# 检测变更
changed_files = git_diff_files()

# 复用缓存
for file in all_files:
    if file in changed_files:
        signals = extract_signals(file)  # 重新提取
    else:
        signals = load_cached_signals(file)  # 复用缓存

# 合并结果
all_signals = merge_signals(new_signals, cached_signals)
```

#### 预期效果
- ✅ **80% 成本降低**（只分析 20% 变更文件）
- ✅ **80% 时间节省**（跳过 80% 未变更文件）
- ✅ 用户愿意频繁运行
- ✅ 快速迭代成为可能

#### 工作量
- **代码量**: ~300 行
- **时间**: 2-3 天
- **复杂度**: 中等（变更检测 + 缓存管理）

#### 风险
- ⚠️ **正确性**: 增量可能遗漏依赖变更
- ⚠️ **缓存失效**: 变更检测可能不准确
- **缓解**: 保留全量模式作为默认，增量作为选择加入

---

### P0-2: 增强 semantic-runner ⭐⭐

#### 任务说明
增强现有 runner，添加阻塞条件、恢复能力、验证集成、错误恢复。

**合并内容**:
- 原 P0-1: Runner 增强（200-300 行）
- 原 P0-3: Finalize guard 集成（20-30 行）
- 原 P0-4: Status 改进（50 行）

#### 为什么要做
1. **手动编排负担**: 用户必须手动运行 5 个命令
   ```bash
   semantic-signals
   semantic-candidates
   semantic-recommend
   semantic-review
   semantic-finalize
   ```

2. **无恢复能力**: 中断后不知道从哪里继续
   - 运行到一半失败
   - 不知道哪些阶段完成了
   - 必须从头开始

3. **错误不清晰**: finalize 被阻塞时不知道原因
   - "BLOCKED" 消息太简单
   - 不知道如何解决

4. **无验证**: 错误输出传播到下游
   - Schema 违规不被捕获
   - 无效操作进入 finalize

#### 不做的后果
- ❌ 用户必须记住 5 个命令的顺序
- ❌ 中断后无法恢复，必须重新开始
- ❌ 错误消息不清晰，调试困难
- ❌ Finalize guard 违规时用户不知道怎么办
- ❌ 高摩擦，差用户体验

#### 实现方案

**1. 阻塞条件**（50 行）
```python
def check_stage_requirements(stage):
    if stage == "step2_candidates":
        if not signals_yaml.exists():
            raise BlockedError("Missing signals.yaml")

    if stage == "step5_finalize":
        checks = load_evidence_checks()
        unresolved = [c for c in checks if c['status'] == 'pending']
        if unresolved:
            raise BlockedError(f"Unresolved verify_first: {unresolved}")
```

**2. 恢复能力**（100 行）
```python
# 持久化状态
state = {
    "completed_stages": ["step1_signals", "step2_candidates"],
    "current_stage": "step3_recommend",
    "errors": []
}
save_state(state)

# 恢复
def resume():
    state = load_state()
    next_stage = get_next_stage(state["completed_stages"])
    run_stage(next_stage)
```

**3. 验证集成**（50 行）
```python
def run_stage(stage):
    # 前置验证
    validate_inputs(stage)

    # 执行
    result = execute_stage(stage)

    # 后置验证
    validate_outputs(stage)
```

**4. 错误恢复**（50 行）
```python
def run_with_recovery(stage):
    try:
        result = run_stage(stage)
        mark_completed(stage)
    except Exception as e:
        mark_failed(stage, error=str(e))
        print(f"Stage {stage} failed: {e}")
        print("Fix the issue and run: semantic-runner --resume")
```

**5. Finalize guard 增强**（30 行）
```python
# 当前（不完整）
if not evidence.exists():
    raise SystemExit("BLOCKED")

# 改进（完整）
checks = load_yaml(evidence)
unresolved = [c for c in checks['evidence_checks']
              if c['status'] == 'pending']
if unresolved:
    print(f"⚠ Finalization blocked: {len(unresolved)} items require verification")
    for c in unresolved:
        print(f"  - {c['target_name']}")
    print("\nNext steps:")
    print("  1. Review evidence-checks.yaml")
    print("  2. Verify required evidence")
    print("  3. Update status to 'completed'")
    print("  4. Run semantic-runner --resume")
    raise SystemExit(1)
```

#### 预期效果
- ✅ 一个命令运行完整链：`semantic-runner --mode all`
- ✅ 中断后可恢复：`semantic-runner --resume`
- ✅ 清晰的错误消息和解决步骤
- ✅ 自动验证输入输出
- ✅ 强制执行 finalize guard

#### 工作量
- **代码量**: ~350 行（合并后）
- **时间**: 2-3 天
- **复杂度**: 中等（编排逻辑）

#### 风险
- ⚠️ **边界情况**: 编排逻辑可能有边界情况
- ⚠️ **状态损坏**: 状态持久化可能损坏
- **缓解**: 彻底测试，提供状态重置

---

### P0-3: 增强 semantic-status ⭐

#### 任务说明
增强 semantic-status 读取 runner 状态，提供可操作的下一步建议。

#### 为什么要做
1. **无指导**: 用户不知道下一步该做什么
   - 中断后不知道从哪里继续
   - 错误后不知道如何修复

2. **状态不清晰**: 当前状态难以理解
   - 哪些阶段完成了？
   - 当前在哪个阶段？
   - 为什么被阻塞？

#### 不做的后果
- ❌ 用户中断后迷失
- ❌ 必须手动检查文件判断状态
- ❌ 不知道运行什么命令
- ❌ 差用户体验

#### 实现方案
```python
def enhanced_status():
    # 读取 runner 状态
    state = load_runner_state()

    # 显示当前状态
    print(f"Current stage: {state['current_stage']}")
    print(f"Completed stages: {', '.join(state['completed_stages'])}")

    # 检查阻塞
    if state.get('blocked_reason'):
        print(f"\n⚠ Blocked: {state['blocked_reason']}")
        print("\nResolution steps:")
        print_resolution_steps(state['blocked_reason'])

    # 推荐下一步
    next_stage = get_next_stage(state['completed_stages'])
    if next_stage:
        print(f"\n✓ Next: semantic-runner --mode next")
        print(f"  (will run: {next_stage})")
    else:
        print("\n✓ All stages completed!")
```

#### 预期效果
- ✅ 清晰显示当前状态
- ✅ 推荐下一步命令
- ✅ 解释阻塞原因
- ✅ 提供解决步骤

#### 工作量
- **代码量**: ~50 行
- **时间**: 0.5 天
- **复杂度**: 低（读取状态 + 格式化输出）

#### 风险
- ✅ **非常低**: 只是读取和显示，不修改状态

---

## P1 任务详解

### P1-1: 验证层

#### 任务说明
构建 semantic-validate 能力，验证 YAML 结构、操作、引用、必需字段。

#### 为什么要做
1. **错误传播**: 无效输出传播到下游
   - Schema 违规不被捕获
   - 无效操作（如 "reject"）进入 finalize
   - 缺失必需字段

2. **调试困难**: 错误在 finalize 时才发现
   - 错误消息晦涩（KeyError, AttributeError）
   - 不知道哪里出错

#### 不做的后果
- ⚠️ 无效 review decisions 导致 finalize 失败
- ⚠️ 错误消息晦涩，调试困难
- ⚠️ 用户浪费时间

**但是**: finalize 阶段已经做了一些验证，所以不是关键阻塞项

#### 实现方案
```python
def validate_review_decisions(path):
    data = load_yaml(path)

    # Schema 验证
    ReviewDecisions.model_validate(data)  # 使用 pydantic

    # 操作验证
    allowed_actions = ['keep', 'merge', 'drop', 'backlog', 'verify_first']
    for domain in data['domains']:
        if domain['final_action'] not in allowed_actions:
            raise ValidationError(f"Invalid action: {domain['final_action']}")

    # 引用验证
    for domain in data['domains']:
        for ref in domain.get('evidence_refs', []):
            if not Path(ref).exists():
                raise ValidationError(f"Evidence not found: {ref}")

    # 必需字段验证
    required_fields = ['id', 'name', 'final_action', 'final_reason']
    for domain in data['domains']:
        for field in required_fields:
            if field not in domain:
                raise ValidationError(f"Missing field: {field}")
```

#### 预期效果
- ✅ 早期捕获错误
- ✅ 清晰的错误消息
- ✅ 防止无效输出传播

#### 工作量
- **代码量**: ~200 行
- **时间**: 1-2 天
- **复杂度**: 低（使用现有 pydantic 模型）

---

### P1-2: E2E 黄金测试

#### 任务说明
创建端到端黄金测试，验证完整链：FACT → signals → candidates → recommend → review → finalize

#### 为什么要做
1. **回归风险**: 修改可能破坏链
2. **集成问题**: 各阶段单独测试通过，但集成失败
3. **质量保证**: 需要验证完整流程

#### 不做的后果
- ⚠️ 回归不被发现
- ⚠️ 集成问题在生产中出现
- ⚠️ 质量无保证

#### 实现方案
```python
def test_full_semantic_chain():
    # 准备 FACT 输入
    fact_input = load_golden_fact()

    # 运行完整链
    signals = run_signals(fact_input)
    candidates = run_candidates(signals)
    recommendations = run_recommend(candidates)
    decisions = run_review(recommendations)
    final_assets = run_finalize(decisions)

    # 验证输出
    assert_golden_match(signals, "golden/signals.yaml")
    assert_golden_match(candidates, "golden/candidates.yaml")
    assert_golden_match(recommendations, "golden/recommendations.yaml")
    assert_golden_match(decisions, "golden/decisions.yaml")
    assert_golden_match(final_assets, "golden/final_assets.yaml")
```

#### 预期效果
- ✅ 回归保护
- ✅ 集成验证
- ✅ 质量保证

#### 工作量
- **代码量**: ~300 行
- **时间**: 2 天
- **复杂度**: 中等（准备黄金数据）

---

### P1-3: 缓存层

#### 任务说明
实现文件级缓存，缓存 AST 解析、fact 提取、signal 推断等昂贵操作。

#### 为什么要做
1. **性能问题**: 重复操作很慢
   - AST 解析每次都重新做
   - Fact 提取重复计算

2. **与增量互补**: 增量检测变更，缓存存储结果

#### 不做的后果
- ⚠️ 性能不佳
- ⚠️ 重复计算浪费

**但是**: 不是阻塞项，可以后续优化

#### 实现方案
```python
def cached_extract_signals(file_path):
    # 计算文件哈希
    file_hash = compute_hash(file_path)

    # 检查缓存
    cache_key = f"signals_{file_hash}"
    if cache.exists(cache_key):
        return cache.load(cache_key)

    # 缓存未命中，执行提取
    signals = extract_signals(file_path)

    # 保存到缓存
    cache.save(cache_key, signals)

    return signals
```

#### 预期效果
- ✅ 50% 性能提升
- ✅ 减少重复计算
- ✅ 与增量执行互补

#### 工作量
- **代码量**: ~400 行
- **时间**: 3-4 天
- **复杂度**: 中等（缓存管理 + 失效策略）

---

## P2 任务

### P2: 自动接受

#### 任务说明
高置信度推荐自动接受，无需人工审查。

#### 为什么不做（暂时）
1. **问题不存在**: 当前 semantic-review 是全自动的
2. **无人工审查瓶颈**: 没有人工审查步骤
3. **评分最低**: 29/50

#### 何时做
只有当人工审查成为瓶颈时才需要。

---

## 执行计划

### 第 1 周：P0（核心工作流）

**第 1 天**:
- ✅ Finalize guard 增强（0.3 天）
- ✅ Status 增强（0.5 天）

**第 2-4 天**:
- ✅ 增量执行（2.5 天）

**第 5-7 天**:
- ✅ Runner 增强（2.5 天）

**结果**:
- ✅ 80% 成本降低
- ✅ 可靠的工作流编排
- ✅ 清晰的用户指导

---

### 第 2 周：P1（质量 + 性能）

**第 8-9 天**:
- ✅ 验证层（1.5 天）

**第 10-11 天**:
- ✅ E2E 测试（2 天）

**第 12-14 天**:
- ✅ 缓存层（3.5 天）

**结果**:
- ✅ 错误预防
- ✅ 回归保护
- ✅ 性能优化

---

## 价值对比

### 按总分排序

| 任务 | 总分 | 价值 | 紧迫性 | 工作量* | 风险* |
|------|------|------|--------|---------|-------|
| 增量执行 | 38 | 10 | 8 | 5 | 6 |
| Runner 增强 | 40 | 7 | 5 | 6 | 7 |
| E2E 测试 | 35 | 7 | 5 | 6 | 9 |
| 验证层 | 34 | 6 | 4 | 7 | 8 |
| Status 增强 | 34 | 4 | 3 | 9 | 10 |
| 缓存层 | 34 | 8 | 6 | 4 | 7 |
| 自动接受 | 29 | 3 | 2 | 7 | 8 |

*工作量和风险是反向评分（10=简单/安全）

### 按价值/工作量比率排序

| 任务 | 比率 | 说明 |
|------|------|------|
| Finalize guard | 16.7 | 快速胜利 |
| Status 增强 | 8.0 | 快速胜利 |
| 增量执行 | 4.0 | 高价值 |
| 验证层 | 4.0 | 中等价值 |
| E2E 测试 | 3.5 | 质量保证 |
| Runner 增强 | 2.8 | 核心编排 |
| 缓存层 | 2.3 | 性能优化 |

---

## 关键决策

### 决策 1: 增量执行应该是 P0

**原因**:
- 评分最高（38/50）
- 80% 成本降低是巨大价值
- 成本是使用的真实障碍
- 完全独立，不依赖其他任务

**反对意见**: "应该先稳定工作流"

**反驳**: 增量不需要 runner 就能工作，全量模式仍可用作后备

---

### 决策 2: 验证层应该是 P1

**原因**:
- Finalize 已经做了验证
- 错误可以在 finalize 时捕获
- 不是阻塞项

**反对意见**: "早期捕获错误更好"

**反驳**: 如果输出由 Python 生成，schema 违规很少；可以作为可选预检查

---

### 决策 3: 合并 P0-3 和 P0-4 到 P0-2

**原因**:
- P0-3（Finalize guard）只是 20-30 行增强
- P0-4（Status --next）功能已存在于 runner
- 不是独立任务

---

## 总结

### P0（必须有）- 6 天

1. **增量执行**（2.5 天）- 80% 成本降低
2. **Runner 增强**（2.5 天）- 可靠编排
3. **Status 增强**（0.5 天）- 用户指导

### P1（应该有）- 7 天

1. **验证层**（1.5 天）- 错误预防
2. **E2E 测试**（2 天）- 质量保证
3. **缓存层**（3.5 天）- 性能优化

### P2（可以有）

1. **自动接受** - 仅在需要时

### 预期结果

**完成 P0 后**:
- ✅ 语义链从"5 个手动命令"变成"1 个可靠工作流"
- ✅ 80% 成本降低（增量）
- ✅ 清晰的用户指导（status）
- ✅ 强制执行 finalize guard

**完成 P1 后**:
- ✅ 错误预防（验证）
- ✅ 回归保护（E2E 测试）
- ✅ 性能提升（缓存）

**总时间**: ~13 天完整实现

---

**最后更新**: 2026-03-17
