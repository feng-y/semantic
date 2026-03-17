# P0 任务深度分析与评分对比

**分析日期**: 2026-03-17

**目标**: 质疑、调研、评分 P0 路线图中的 4 个任务

---

## 执行摘要

**关键发现**:
1. ❌ P0 任务列表有重复 - P0-3 和 P0-4 实际上是 P0-1 的增强
2. ⚠️ 增量执行（P1-1）的价值评分**高于**所有 P0 任务
3. ✅ 验证层有用但不是关键阻塞项
4. ❌ 自动接受（P1-2）解决的问题在当前实现中不存在

**修订建议**: 重新排序优先级，将增量执行提升到 P0

---

## 任务 1: 增强 semantic-runner

### 当前状态
- `src/semantic/run.py` 已存在（80 行）
- 支持 `--mode next` 和 `--mode all`
- 已有基础状态持久化
- 已有部分 finalize guard 检查（63-71 行）

### 声称的价值
"将 5 个手动命令变成 1 个可靠的工作流"

### 质疑与调研

**质疑 1**: 真的需要吗？
- `semantic-pipeline` 组合技能已存在
- 用户可以直接运行 `/semantic-pipeline`
- 为什么需要单独的 runner？

**答案**: 组合技能只是顺序调用，不提供：
- 中断后的状态持久化
- 阻塞条件强制执行
- 输出验证
- 恢复能力

**质疑 2**: 实际复杂度是多少？
- 阻塞条件：检查文件存在、解析 YAML 查找 verify_first
- 恢复：读写 run-state.yaml
- 验证集成：调用 semantic-validate，检查退出码
- 错误恢复：跟踪失败阶段，允许重试

**估算**: ~200-300 行编排逻辑

**质疑 3**: 如果跳过会怎样？
- 用户手动运行 5 个命令
- 错误时无指导
- 中断后无法恢复
- finalize guard 违规不清晰

**影响**: 高摩擦，差 UX，但工作流仍可手动运行

### 评分（1-10）

| 维度 | 分数 | 说明 |
|------|------|------|
| 价值 | 7 | 良好的编排，但工作流可手动运行 |
| 紧迫性 | 5 | 用户可以手动运行命令 |
| 工作量 | 6 | 200-300 行，中等复杂度（反向：10=简单） |
| 风险 | 7 | 编排逻辑可能有边界情况（反向：10=安全） |
| 独立性 | 8 | 基本独立 |
| **总分** | **33/50** | |

### 实际需求
- ✅ 需要：更好的编排和恢复能力
- ⚠️ 但不是最关键的 P0 项

---

## 任务 2: 构建 semantic-validate

### 当前状态
- ❌ 不存在验证层
- ✅ 模型已存在：`finalize_models.py`, `review_models.py`
- ✅ finalize 阶段已有部分验证

### 声称的价值
"在传播前捕获 schema 漂移、无效操作、缺失字段"

### 质疑与调研

**质疑 1**: 实际会发生什么错误？
查看代码库：
- review-decisions.yaml 有 final_action 字段，允许值有限
- evidence-checks.yaml 有 status 字段
- 所有输出都有 metadata 部分
- 模板存在但很简单

**真实风险**: 有人手动编辑 YAML 并引入：
- 无效操作如 "reject" 而不是 "drop"
- 缺失必需字段
- 损坏的证据引用

**质疑 2**: 这种情况多久发生一次？
- 如果输出总是由 Python 代码生成，schema 违规很少
- 如果人类编辑 YAML 文件，违规很常见
- 当前工作流：Python 生成，人类可能编辑 review-decisions.yaml

所以验证对人类编辑的文件最关键：review-decisions.yaml

**质疑 3**: 实现复杂度？
- Schema 验证：使用 pydantic 模型（已存在）
- 操作验证：检查允许列表
- 引用验证：检查文件存在
- 必需字段验证：检查 None/缺失

**估算**: ~150-200 行，使用现有模型

**质疑 4**: 如果跳过会怎样？
- 无效的 review decisions 导致 finalize 失败
- 错误消息晦涩（KeyError, AttributeError）
- 用户浪费时间调试

**影响**: 中等摩擦，但错误在 finalize 阶段仍可捕获

### 评分（1-10）

| 维度 | 分数 | 说明 |
|------|------|------|
| 价值 | 6 | 捕获错误，但 finalize 也会验证 |
| 紧迫性 | 4 | 错误在 finalize 时可捕获 |
| 工作量 | 7 | 150-200 行，使用现有模型 |
| 风险 | 8 | 验证很直接 |
| 独立性 | 9 | 完全独立 |
| **总分** | **34/50** | |

### 实际需求
- ✅ 有用但不关键
- ⚠️ finalize 已经做了一些验证
- 💡 可以作为可选的预检查

---

## 任务 3: 集成 finalize guard 到 runner

### 当前状态
- ✅ finalize_assets.py 已有 finalize guard 逻辑（101-106 行）
- ✅ run.py 已有部分 finalize guard 检查（63-71 行）

### 声称的价值
"用户理解为什么 finalize 被阻塞"

### 质疑与调研

**质疑 1**: 实际缺少什么？

finalize guard 已在 finalize_assets.py 中工作：
```python
unresolved = check_unresolved_verifications(checks)
if unresolved:
    print(f"⚠ Unresolved verify_first items: {', '.join(unresolved)}")
    print("Finalization blocked. Resolve evidence checks first.")
    return
```

run.py 中已有检查：
```python
if stage == "step5_finalize":
    review = workspace / "review-decisions.yaml"
    evidence = workspace / "evidence-checks.yaml"
    if review.exists():
        data = yaml.safe_load(review.read_text(encoding="utf-8")) or {}
        if any(d.get("final_action") == "verify_first" for d in data.get("decisions", [])):
            if not evidence.exists():
                state["blocked_reason"] = "verify_first exists but evidence-checks.yaml is missing"
                save_state(state_path, state)
                raise SystemExit("BLOCKED")
```

**发现**: Runner 已经有 finalize guard 逻辑！

**质疑 2**: 那缺少什么？
- 当前检查不完整：只检查 evidence-checks.yaml 是否存在，不检查项目是否已解决
- 应该检查 evidence-checks.yaml 的 status 字段是否为 "pending"
- 应该提供更清晰的错误消息

**质疑 3**: 实际工作量？
- 增强 run.py 中的现有检查以解析 evidence-checks.yaml
- 检查 status == "pending"
- 改进错误消息

**估算**: ~20-30 行代码增强，不是新功能

### 评分（1-10）

| 维度 | 分数 | 说明 |
|------|------|------|
| 价值 | 5 | 已部分工作 |
| 紧迫性 | 6 | 当前错误消息不清晰 |
| 工作量 | 9 | 20-30 行，简单增强 |
| 风险 | 9 | 低风险，小改动 |
| 独立性 | 7 | 依赖 runner 存在 |
| **总分** | **36/50** | |

### 实际需求
- ❌ 这不是单独的 P0 项
- ✅ 应该合并到 P0-1（runner 增强）
- 💡 是 bug 修复/增强，不是新功能

---

## 任务 4: 添加 semantic-status --next

### 当前状态
- ✅ semantic-status 存在
- ✅ 调用 `src.state_inspector.inspect`
- ✅ 已推荐下一步操作

### 声称的价值
"用户知道中断后下一步运行什么"

### 质疑与调研

**质疑 1**: 当前 semantic-status 做什么？
查看 skills/semantic-status/SKILL.md：
- 报告当前工作流阶段
- 显示可用工件
- 推荐下一步操作

**发现**: 它已经推荐下一步操作！

**质疑 2**: 实际用户需求是什么？

场景 1：用户运行 semantic-pipeline，在阶段 3 失败
- 用户运行 semantic-status
- Status 说 "阶段 3 失败，再次运行 semantic-recommend"
- 用户运行 semantic-recommend

场景 2：用户中断工作流
- 用户运行 semantic-status
- Status 说 "完成阶段 1-2，下一步是 semantic-recommend"
- 用户运行 semantic-recommend

**质疑 3**: --next 添加了什么？
- semantic-status --next 会自动运行推荐的命令
- 节省用户复制粘贴命令

**但等等**，这不就是 semantic-runner --mode next 做的吗？

查看 run.py 47-56 行：
```python
if args.mode == "next":
    stage = next_stage(state.get("completed_stages", []))
    if stage is None:
        print("DONE")
        return
    state["completed_stages"].append(stage)
    state["current_stage"] = stage
    save_state(state_path, state)
    print(f"PASS: {stage}")
    return
```

**发现**: semantic-runner --mode next 已经做了这个！

**质疑 4**: 实际缺少什么？
- semantic-status 应该读取 runner 状态并显示
- semantic-status 应该推荐 "运行 semantic-runner --mode next"
- 不需要 semantic-status --next，只需要更好的消息

### 评分（1-10）

| 维度 | 分数 | 说明 |
|------|------|------|
| 价值 | 4 | runner --mode next 已存在 |
| 紧迫性 | 3 | 用户可以读取状态并运行命令 |
| 工作量 | 9 | 50 行，简单增强 |
| 风险 | 10 | 非常安全，只是消息 |
| 独立性 | 8 | 基本独立 |
| **总分** | **34/50** | |

### 实际需求
- ❌ 这不是单独的 P0 项
- ✅ 是 semantic-status 的增强，读取 runner 状态
- 💡 大约 50 行代码

---

## P1 任务重新评估

### P1-1: 增量 signals 提取

### 声称的价值
"增量运行减少 80% 成本"

### 质疑与调研

**质疑**: 这比 runner 增强更有价值吗？

思考用户痛点：
- 痛点 1：手动运行 5 个命令（runner 修复）
- 痛点 2：每次运行花费 $X token（增量修复）
- 痛点 3：每次运行需要 Y 分钟（增量修复）

如果 X 很大且 Y 很长，增量可能比 runner 更重要！

**依赖性分析**:
- 增量需要稳定的工作流吗？不需要
- 增量需要验证吗？不需要
- 增量需要 runner 吗？不需要

**发现**: 增量是独立的！可以先做。

### 评分（1-10）

| 维度 | 分数 | 说明 |
|------|------|------|
| 价值 | 10 | 80% 成本降低是巨大的 |
| 紧迫性 | 8 | 成本是真实障碍 |
| 工作量 | 5 | 300 行，变更检测逻辑 |
| 风险 | 6 | 增量的正确性问题 |
| 独立性 | 9 | 独立于其他任务 |
| **总分** | **38/50** | |

**惊人结果**: 增量评分高于所有 P0 项！

---

### P1-2: 基于置信度的自动接受

### 声称的价值
"减少 60% 的人工审查负担"

### 质疑与调研

**质疑**: 人工审查实际上是瓶颈吗？

查看工作流：
- semantic-review 自动生成 review-decisions.yaml
- 人类不需要审查，除非想要覆盖
- 那瓶颈在哪里？

**发现**: 当前 semantic-review 是确定性的（1:1 转换 recommendations 到 decisions）。"审查"本应是人类审查 recommendations 后再接受。

但当前实现没有人工审查！它是完全自动化的。

**结论**: P1-2（自动接受）解决的问题在当前实现中不存在。

### 评分

| 维度 | 分数 | 说明 |
|------|------|------|
| 价值 | 2 | 解决不存在的问题 |
| 紧迫性 | 1 | 当前无人工审查瓶颈 |
| 工作量 | 6 | 中等复杂度 |
| 风险 | 7 | 自动接受可能降低质量 |
| 独立性 | 8 | 基本独立 |
| **总分** | **24/50** | |

---

## 综合评分对比

| 任务 | 价值 | 紧迫性 | 工作量 | 风险 | 独立性 | 总分 | 排名 |
|------|------|--------|--------|------|--------|------|------|
| **P1-1: 增量执行** | 10 | 8 | 5 | 6 | 9 | **38** | 🥇 1 |
| **P0-3: Finalize guard** | 5 | 6 | 9 | 9 | 7 | **36** | 🥈 2 |
| **P0-2: 验证层** | 6 | 4 | 7 | 8 | 9 | **34** | 🥉 3 |
| **P0-4: Status --next** | 4 | 3 | 9 | 10 | 8 | **34** | 🥉 3 |
| **P0-1: Runner 增强** | 7 | 5 | 6 | 7 | 8 | **33** | 5 |
| P1-2: 自动接受 | 2 | 1 | 6 | 7 | 8 | **24** | 6 |

---

## 修订后的优先级建议

### 真正的 P0（必须有）

#### 1. 增量 signals 提取（原 P1-1）
- **为什么**: 最高价值，减少 80% 成本
- **工作量**: 300 行，中等复杂度
- **风险**: 正确性问题，但可以通过测试缓解
- **独立性**: 完全独立，可以立即开始

#### 2. 增强 semantic-runner（合并 P0-1 + P0-3）
- **为什么**: 改善编排和 UX
- **工作量**: 250 行（runner 200 + finalize guard 50）
- **风险**: 中等，编排逻辑
- **包含**: 阻塞条件、恢复、finalize guard 集成

#### 3. 增强 semantic-status（原 P0-4 简化版）
- **为什么**: 简单增强，高 UX 价值
- **工作量**: 50 行
- **风险**: 低
- **内容**: 读取 runner 状态，显示清晰的下一步

### P1（应该有）

#### 1. 验证层（原 P0-2）
- **为什么**: 错误预防，可以随时添加
- **工作量**: 200 行
- **时机**: P0 完成后

#### 2. 缓存层（原 P1-4）
- **为什么**: 性能提升
- **工作量**: 400 行
- **时机**: 增量执行稳定后

#### 3. 端到端测试（原 P1-3）
- **为什么**: 质量保证
- **工作量**: 测试套件
- **时机**: 核心功能稳定后

### P2（很好有）

1. 自动接受 - 仅在人工审查成为瓶颈时需要
2. 反馈循环 - 基于使用情况优化
3. LSP 集成 - 准确性改进

---

## 争议性观点

### 原计划说："工作流稳定性优先"

**支持论据**:
- 在优化前先做好编排
- 验证防止错误的增量结果
- Runner 为增量提供框架

**反对论据**:
- 增量是独立的，不需要 runner
- 成本障碍比 UX 摩擦更紧迫
- 用户可以手动运行命令，但无法手动降低成本

### 我的最终建议

**从增量开始，然后 runner，然后验证**

这最大化了价值交付速度：
1. 增量立即降低成本（最大痛点）
2. Runner 改善 UX（第二痛点）
3. 验证增加安全性（良好实践）

---

## 执行风险

### 风险 1: Runner 复杂性蔓延
**缓解**: 保持 runner 专注于编排。不要嵌入业务逻辑。

### 风险 2: 验证过于严格
**缓解**: 从结构验证开始。逐步添加语义验证。

### 风险 3: 增量执行破坏正确性
**缓解**: 使增量可选。保持完整模式为默认。彻底测试。

### 风险 4: 自动接受降低质量
**缓解**: 从高置信度阈值开始（>0.9）。需要审计日志。允许覆盖。

---

## 结论

原始 P0 计划高估了 runner 的紧迫性，低估了增量执行的价值。

**修订后的执行顺序**:
1. 增量 signals 提取（2-3 天）
2. 增强 semantic-runner + finalize guard（2-3 天）
3. 增强 semantic-status（1 天）
4. 验证层（2 天）

**总 P0 工作量**: ~1 周

这个顺序最大化了价值交付，同时保持了合理的风险水平。
