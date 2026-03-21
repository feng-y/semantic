# Harness Engineering — 完整知识总结

> 来源：13 篇核心文献综合 (2025-2026)
> 更新：2026-03-21

---

## 一、核心定义

**Harness Engineering** = 构建结构来控制、约束、验证 AI 生成的代码，使得人类无需逐行阅读代码也能确保质量。

**为什么重要：**
- AI 生成代码 ≠ 正确代码
- AI 会过度自信地填补模糊指令（"fanfiction"）
- 人类的注意力是固定瓶颈
- **质量靠结构积累，不靠人工检查**

---

## 二、Three Pillars 框架（Martin Fowler / Thoughtworks）

| 支柱 | 内容 | 示例 |
|------|------|------|
| **Context Engineering** | 代码库中持续增强的知识库 + 动态上下文 | AGENTS.md、schema、observability 数据 |
| **Architectural Constraints** | LLM 代理 + 确定性 linter + 结构测试双重监控 | 自定义 lint、ArchUnit |
| **Garbage Collection** | 定期运行的 Agent 扫描文档不一致和架构违规 | 后台 task 持续重构 |

---

## 三、核心模式（按重要性排序）

### 1. AGENTS.md —— 入口地图，不是说明书

| 做法 | 反模式 |
|------|--------|
| ~100 行，"地图"风格 | 1000 行百科全书 |
| 指向深层次文档 | 所有细节堆在一起 |
| 每次错误后更新 | 写完就烂掉 |
| 每条可验证（说 pytest 就真能跑通） | 写"run tests"但测试是坏的 |
| 渐进式披露：从小而稳定的入口开始 | 一开始淹没 agent |

**来源：** Mitchell Hashimoto (coined the term)、OpenAI、Hashimoto AGENTS.md 实践

### 2. JSON Feature List + passes 字段 —— 防止 Agent 自说自话

```json
{
  "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "steps": ["Navigate to main interface", "Click 'New Chat'", "Verify a new conversation is created"],
  "passes": false
}
```

**为什么用 JSON：**
- Agent 难以随意修改/删除条目（比 Markdown 更结构化）
- `passes: false` 初始状态 → Agent 必须在 E2E 测试后才改为 true
- **Prompt 要强调："移除或修改测试是不可接受的"**

**来源：** Anthropic Justin Young

### 3. Two-Agent Architecture —— 解决上下文失忆

| Agent | 职责 | 输出 |
|-------|------|------|
| **Initializer** | 首次 session | `init.sh`、`claude-progress.txt`、JSON feature list、initial git commit |
| **Coding** | 每次后续 session | 增量功能、git commit、progress 更新 |

**标准 Session 启动流程：**
```
[Assistant] Getting my bearings...
[Tool] pwd → 确认目录
[Tool] read progress.txt → 理解当前状态
[Tool] git log --oneline -20 → 最近的进展
[Tool] read feature_list.json → 选最高优先级且 passes=false 的功能
[Tool] run init.sh → 启动 dev server
[Tool] E2E smoke test → 验证基础功能未被破坏
[Assistant] 基础功能正常 → 开始实现新功能
```

**来源：** Anthropic

### 4. E2E 测试优先 —— Agent 必须自己验证

- **Anthropic 警告：** Agent 会在没测完时就 mark passes=true
- **Osmani：** "测试把 unreliable agent 变成 reliable system"
- **Stripe 基准：** Claude Opus 4.5 达到 92% full-stack，但 agent 自验证是最大差异化因素
- **Puppeteer MCP：** Agent 截图验证，像真实用户一样测试
- **原则：** 总是先 run init.sh + E2E smoke test，再实现新功能

### 5. Backpressure & Ralph Wiggum Loop

**机制：**
```
Agent 做功
  ↓
Verifier 检查
  ↓
失败 → Agent 修复 → 重新验证
  ↓
通过 → Agent 声明完成
```

**Backpressure 信号：**
| 信号 | Agent 响应 | Loop 行为 |
|------|-----------|----------|
| 低质量输出 | 必须修复后才能继续 | **减速** — 增加验证、收紧约束 |
| 高质量输出 | 可以继续 | **加速** — 减少冗余检查 |

**Ralph 特点：** Agent 验证自己的工作后才声明完成（自引用）

**来源：** Geoffrey Huntley

### 6. Trust Debt —— 每次不检查都在累积债务

> "Every unchecked assumption delegated to the AI is accumulating 'trust debt' that compounds until Future You pays it all back at once." — Cassie Kozyrkov

**Two-Translation Habit：**
```
# 写代码前 — 让 AI 确认理解：
"在写代码之前，告诉我你理解我的指令是什么意思，
以及哪些假设需要我批准。"

# 写代码后 — 换另一个 AI（无 session 访问）翻译回来：
"用外行能懂的话逐步描述这段代码做了什么，
列出所有它可能出问题的地方。"
```

### 7. 构建壁垒，不只是对话

| 对话验证 | 壁垒验证 |
|---------|---------|
| 依赖人类注意力和记忆 | 自动运行，无人值守 |
| 有天花板 | 无天花板 |
| 聊完就没了 | 现在建好，未来保护你 |

**壁垒形式：** linter、CI pipeline、架构不变量、自动化测试、Agent 互相审查

> "The harness doesn't need to be as complex as the thing it controls." — Cassie Kozyrkov

### 8. Garbage Collection —— 对抗熵增

**问题：** Agent 会复现代码库中已有的模式（包括坏模式）→ 漂移不可避免

**解法：** 将"黄金原则"编码为代码中的机械规则

```
# 好的实践：
1. 优先使用共享 utility 包而非手写辅助函数（不变式集中管理）
2. 不做 "YOLO" 数据探测（验证边界或用 typed SDK）

# 自动运行：
后台 Agent 任务定期扫描漂移、更新质量分、发起定向重构 PR
（大多数一分钟内审完并自动合并）
```

> "Technical debt is like a high-interest loan: continuously paying small installments beats accumulating and paying painfully later." — OpenAI

### 9. 规范架构（Normative Architecture）

**OpenAI 的实践：**
- 每业务域 = 固定层：Types → Config → Repo → Service → Runtime → UI
- 横切关注点通过单一显式接口进入：Providers
- 其他跨依赖禁止，linter + 结构测试机械强制执行

> "这种架构通常要等到有数百名工程师时才推迟。对于 coding agent 来说，这是早期先决条件：有了约束，速度才不会下降，架构才不会漂移。" — Ryan Lopopolo

---

## 四、Context Engineering 分类（Birgitta Böckeler）

### 两类 Prompt 意图

| 类型 | 目的 | 例子 |
|------|------|------|
| **Instructions** | 告诉 Agent 做什么 | "Write an E2E test as follows: ..." |
| **Guidance**（rules/guardrails） | Agent 应遵循的通用约定 | "Always write independent tests" |

### Context Interfaces（Agent 如何获取上下文）

| Interface | 谁决定加载 | 确定性 | Claude Code 对应 |
|-----------|-----------|--------|----------------|
| 文件读取/搜索 | — | Yes | 工作区文件 |
| Tools | 内置 | Yes | bash、edit |
| **MCP Servers** | LLM | Yes | Playwright、Puppeteer |
| **Skills** | LLM 或 Human | Partial | `/skill` 命令 |
| **Hooks** | Agent 软件 | Yes | after-write-hook |
| **Subagents** | LLM 或 Human | Yes | 并行子任务 |

### 关键张力

> "Context engineering can make a coding agent more effective. However, as long as LLMs are involved, we can never be certain of anything — still think in probabilities." — Böckeler

**不要做的事：**
- 一开始塞太多东西（build up gradually）
- 说 "ensure it does X" / "prevent hallucinations"（LLM = 概率，不是保证）
- 复制陌生人的配置（可能重复、矛盾）

---

## 五、统一结论

### 通用失败模式
Agent 填满模糊指令 → 人类在看到"能跑"的代码后放松警惕 → 控制链断裂

### 通用解法
**精确指定 + 严格验证 + 构建自动化壁垒**

### 术语收敛
| 术语 | 强调 |
|------|------|
| "Vibe coding" | YOLO |
| "Agentic engineering" | 人类负责架构/质量 |
| "Harness engineering" | 控制结构 |

> "The rise of AI coding doesn't replace the craft of software engineering — it raises the bar for it." — Addy Osmani

---

## 六、实操检查清单

- [ ] AGENTS.md 存在、~100 行、每条可验证
- [ ] 有 `init.sh` 启动脚本
- [ ] 有 `progress.txt` 或 feature list 追踪进展
- [ ] 有 `tech-debt-tracker.md` 管理债务
- [ ] 有 CI gate（lint + test）
- [ ] 有结构测试（ArchUnit 或等价物）
- [ ] E2E 测试优先于 unit test
- [ ] 定期运行 garbage collection 任务
- [ ] 不确定性规则编码为 lint，而非注释
