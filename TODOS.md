# TODOS

## TODO-1: demand 阶段消费领域聚合输出

**What:** demand 阶段需要适配新的 commit-semantic 领域聚合输出（domains-aggregated.jsonl、canonical-demands.jsonl）。
**Why:** demand 是 commit-semantic 的下游消费者之一，当前接口未定义。
**Pros:** 打通 commit → semantic → demand 完整管道。
**Cons:** 需要先明确 demand 阶段需要什么字段。
**Context:** 设计文档 Open Question #2。commit-semantic 重写后输出从 theme 聚合改为 domain 聚合，demand 阶段的消费逻辑需要相应调整。当前 demand 管道在 `src/demand/`，消费 `data/commit-semantic/` 的输出。
**Depends on:** commit-semantic 领域聚合重写完成。

## TODO-2: 可审计性 + 置信度 + 回写修正

**What:** 三个后续能力：(1) 每个 section/item/rule 追溯回原始 diff/file/hunk；(2) 标记 rule/invariant 的置信度（高置信 vs 候选归纳）；(3) reviewer 发现抽错时能修规则而不是只修单次结果。
**Why:** 决定 commit-semantic 是 demo 还是 repo 级基础设施。如果 commit-extract 抽得不稳，后面所有领域发现都会被上游偏差放大。
**Pros:** 让整个管道可信赖、可纠错、可迭代。
**Cons:** 可审计性需要改 commit-extract 的输出 schema（加 file/hunk 来源）；回写修正需要设计反馈循环机制。
**Context:** 设计文档风险部分明确列出。参考 Landscape Awareness 中 RIG 的 evidence-backed 方法。
**Depends on:** commit-semantic 领域聚合重写完成。commit-extract 输出 schema 可能需要扩展。

## TODO-5: commit-semantic agent 清理不彻底

**What:** 调查并修复 `commit-semantic` 执行过程中 spawned agents 的 shutdown / teardown 不一致问题，确保 agent 生命周期能被可靠收尾，不残留 idle / ghost 状态。
**Why:** 当前会话里 agent 虽收到 shutdown request，但后续仍出现 idle 通知，说明清理链路不稳定；这会污染后续执行状态，也会削弱基于 agent orchestration 的可靠性。
**Pros:** 提升 `commit-semantic` orchestration 的可验证性与稳定性；避免残留 agent 干扰后续会话。
**Cons:** 需要梳理 skill 调用层、team 上下文层、shutdown 协议和状态同步路径，可能要补生命周期回归测试。
**Context:** 本次会话在清理 `domain-reviewer` / `classification-reviewer` 后，系统已报告 terminated，但仍收到 idle 通知，表现出收尾不一致。
**Depends on:** 需要先确认问题发生在 Claude Code team 生命周期、skill 编排层，还是 `commit-semantic` 自身的 agent 使用方式。

## Completed

### TODO-3: 补真正的 LLM orchestrator discover/classify 执行链路

**Completed:** 2026-03-23 on branch `feature/commit-semantic-domain`

`commit-semantic` 现在已经支持基于 `HostExecutor` 的 discover / classify 真正模型执行路径，不再依赖语义 fallback 作为成功主路径。

## TODO-4: 固定 repo-level golden baseline / 回归样本集

**What:** 为 commit-semantic 建立固定的 repo-level golden baseline / 回归样本集，用于后续 domain quality 回归验证，而不是每次都依赖临时人工抽检。
**Why:** 当前 repo-level 质量判断依赖手工读取 `summary.json`、`domains.json`、`domains-aggregated.jsonl`。没有固定 baseline，很难判断一次优化到底是进步、退步还是只是换了一种错误。
**Pros:** 让 domain quality 优化拥有稳定回归基准；降低主观判断成本；为 fallback/LLM 两种模式建立可比较的质量快照。
**Cons:** 需要维护 snapshot 或样本集；如果仓库历史变化太快，baseline 可能需要定期刷新。
**Context:** 当前 baseline 已有明确数值：repo-level run 的 `uncategorized_ratio = 0.1762`，且已暴露 `tests/test` 重复、domain 命名粗糙等问题。这些现象需要被固定成可回归检查的样本。
**Depends on:** 依赖本轮 domain quality 方案先落地，至少完成 normalization、classify gating、mode reporting 后再冻结 baseline。
