# Finalize Guard 详解

## 什么是 Finalize Guard？

**Finalize guard** 是一个安全机制，防止在证据验证未完成时生成最终语义资产。

---

## 问题场景

### 语义工作流的 5 个阶段

```
1. semantic-signals      → 提取信号
2. semantic-candidates   → 生成候选
3. semantic-recommend    → 评分推荐
4. semantic-review       → 生成审查决策
5. semantic-finalize     → 生成最终资产 ⚠️
```

### 第 4 阶段的输出

**review-decisions.yaml** 包含决策：
```yaml
domains:
  - name: "User Management"
    final_action: "keep"          # ✅ 直接接受

  - name: "Payment Processing"
    final_action: "verify_first"  # ⚠️ 需要先验证证据

  - name: "Legacy Code"
    final_action: "drop"           # ❌ 丢弃
```

**evidence-checks.yaml** 跟踪验证状态：
```yaml
evidence_checks:
  - target_name: "Payment Processing"
    status: "pending"              # ⚠️ 还未验证
    required_evidence:
      - "src/payment/processor.py"
      - "docs/payment-flow.md"
```

---

## 问题：如果没有 Finalize Guard

### 场景

1. semantic-review 生成决策：
   - "Payment Processing" → `final_action: verify_first`
   - 需要验证证据，但 `status: pending`

2. 用户直接运行 semantic-finalize

3. **问题**：
   - Finalize 会生成包含 "Payment Processing" 的最终资产
   - 但证据还没验证！
   - 可能包含错误或不完整的信息

### 后果

```yaml
# domain-map.yaml (最终资产)
domains:
  - name: "Payment Processing"
    id: "domain_abc123"
    evidence_refs:
      - "未验证的证据"  # ⚠️ 危险！
```

这个最终资产会被 demand 层使用，但基于未验证的信息！

---

## 解决方案：Finalize Guard

### 代码实现

在 `src/semantic/finalize_assets.py` 第 101-107 行：

```python
# Check for unresolved verifications
unresolved = check_unresolved_verifications(checks)
if unresolved:
    print(f"⚠ Unresolved verify_first items: {', '.join(unresolved)}")
    print("Finalization blocked. Resolve evidence checks first.")
    sys.exit(1)  # 阻止执行
```

### 工作原理

1. **读取 evidence-checks.yaml**
2. **检查所有 verify_first 项的状态**
3. **如果有 status == "pending"**：
   - 打印错误消息
   - 阻止 finalize 执行
   - 退出并返回错误码

---

## 实际例子

### 场景 1：有未解决的验证

```bash
$ semantic-finalize

⚠ Unresolved verify_first items: Payment Processing, API Gateway
Finalization blocked. Resolve evidence checks first.

# 退出码：1（失败）
```

**用户必须**：
1. 检查 evidence-checks.yaml
2. 验证所需证据
3. 更新 status 为 "completed"
4. 然后才能运行 finalize

---

### 场景 2：所有验证已完成

```yaml
# evidence-checks.yaml
evidence_checks:
  - target_name: "Payment Processing"
    status: "completed"  # ✅ 已验证
    required_evidence:
      - "src/payment/processor.py"
      - "docs/payment-flow.md"
```

```bash
$ semantic-finalize

✓ domain-map.yaml
✓ concept-map.yaml
✓ rule-map.yaml
✓ demand-model-map.yaml
✓ change-log.yaml

✓ Finalized 3 domains, 5 concepts, 2 rules, 1 demand models

# 退出码：0（成功）
```

---

## 为什么叫 "Guard"（守卫）？

就像门卫一样：

```
用户 → 想进入 finalize 阶段
       ↓
   Finalize Guard 检查
       ↓
   有未验证项？
       ↓
   YES → ❌ 阻止进入
       ↓
   NO  → ✅ 允许通过
```

---

## 当前问题

### 问题 1：Guard 已存在但不完整

**finalize_assets.py** 有 guard（101-107 行）✅

**run.py** 也有 guard（63-71 行）⚠️ 但不完整：

```python
# 当前实现
if any(d.get("final_action") == "verify_first" for d in data.get("decisions", [])):
    if not evidence.exists():
        # 只检查文件是否存在
        state["blocked_reason"] = "verify_first exists but evidence-checks.yaml is missing"
        raise SystemExit("BLOCKED")
```

**缺少**：
- 不检查 evidence-checks.yaml 的 status 字段
- 不检查是否有 status == "pending"

---

### 问题 2：错误消息不清晰

**当前**：
```
BLOCKED
```

**应该**：
```
⚠ Finalization blocked: 2 items require evidence verification

Unresolved items:
  - Payment Processing (status: pending)
  - API Gateway (status: pending)

Next steps:
  1. Review evidence-checks.yaml
  2. Verify required evidence
  3. Update status to "completed"
  4. Run semantic-finalize again
```

---

## P0-3 任务：集成 Finalize Guard

### 实际工作

**不是**：创建新的 guard 机制（已存在）

**是**：增强 runner 中的 guard 检查

### 需要做的

1. **增强 run.py 的检查**（20-30 行）：
   ```python
   # 当前
   if not evidence.exists():
       raise SystemExit("BLOCKED")

   # 改进
   checks = yaml.safe_load(evidence.read_text())
   unresolved = [c for c in checks.get('evidence_checks', [])
                 if c.get('status') == 'pending']
   if unresolved:
       names = [c['target_name'] for c in unresolved]
       state["blocked_reason"] = f"Unresolved verify_first: {', '.join(names)}"
       print(f"⚠ Finalization blocked: {len(unresolved)} items require verification")
       for name in names:
           print(f"  - {name}")
       raise SystemExit("BLOCKED")
   ```

2. **改进错误消息**：
   - 列出未解决的项
   - 提供下一步指导
   - 保存到 run-state.yaml

---

## 为什么这是 P0？

### 原计划说

"用户理解为什么 finalize 被阻塞"

### 实际情况

- Guard 已经工作 ✅
- 只是错误消息不够清晰 ⚠️
- 只需要 20-30 行增强 📝

### 评分

- **价值**: 5/10（已部分工作）
- **紧迫性**: 6/10（错误消息不清晰）
- **工作量**: 9/10（很简单）
- **风险**: 9/10（低风险）
- **总分**: 36/50

### 结论

这不是独立的 P0 任务，应该合并到 "Runner 增强" 中。

---

## 类比：现实世界的 Guard

### 机场安检（Finalize Guard）

```
乘客（语义资产）想登机（进入最终状态）
    ↓
安检员检查
    ↓
护照验证完成？
    ↓
NO → ❌ 不能登机，去验证护照
    ↓
YES → ✅ 可以登机
```

### 没有 Guard 的后果

```
未验证的乘客登机
    ↓
可能是危险人物
    ↓
飞机起飞后才发现
    ↓
太晚了！
```

### 有 Guard 的好处

```
在登机前检查
    ↓
发现问题
    ↓
阻止登机
    ↓
去验证
    ↓
验证完成后再登机
    ↓
安全！
```

---

## 总结

### Finalize Guard 是什么？

一个安全检查，确保只有已验证的语义资产进入最终状态。

### 为什么需要？

防止未验证的信息污染最终资产，被 demand 层错误使用。

### 当前状态？

- ✅ Guard 逻辑已存在
- ⚠️ Runner 集成不完整
- ⚠️ 错误消息不清晰

### P0-3 做什么？

增强 runner 中的 guard 检查（20-30 行），不是创建新功能。

### 为什么评分不高？

因为核心功能已经工作，只是需要改进用户体验。

---

**简单一句话**：

Finalize guard = 在生成最终资产前，检查所有 "需要先验证" 的项是否已验证完成，如果没有就阻止执行。
