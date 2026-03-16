# Claude Code 执行顺序

1. 先看 `README_CC_INTEGRATION.md`
2. 再看 `INVENTORY_AND_EXPECTATION.md`
3. 用 `prompts/semantic/trigger.prompt.md` 作为总触发
4. 按顺序实现：
   - src/semantic/extract_signals.py
   - src/semantic/build_candidates.py
   - src/semantic/score_recommend.py
   - src/semantic/apply_review.py
   - src/semantic/evidence_check.py
   - src/semantic/finalize_assets.py
   - src/semantic/run.py
5. 跑 `tests/semantic/`
