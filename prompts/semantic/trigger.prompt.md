你现在在现有 `semantic` repo 中实现统一的 `semantic` 流程。

目标：
把旧 fact layer 之上的新链路统一收敛到 `semantic` 目录结构，并保证 Claude Code / Codex 可按 `next` 或 `all` 模式运行。

必须遵守：
1. 不重写现有 discover / review / refine / baseline 主逻辑
2. 新增代码统一放在 `src/semantic/`
3. prompts 统一放在 `prompts/semantic/`
4. templates 统一放在 `templates/semantic/`
5. workspace 固定为 `docs/semantic-foundation/semantic/`
6. canonical outputs 一律优先 YAML，Markdown 只是 view
7. runner 支持 next / all
8. priority = max(business_score, value_score)
9. verify_first 未完成时禁止 finalize
10. review-decisions.yaml 是 canonical 决策输入

实施顺序：
- step1 signals
- step2 candidates
- step3 recommendations
- step4 review + evidence
- step5 finalize
- runner + tests

交付要求：
- 新增/修改文件列表
- 每一步 CLI 命令
- 仍未完成的边界问题
