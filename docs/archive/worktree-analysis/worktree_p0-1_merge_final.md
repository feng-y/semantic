# worktree-p0-1 合并策略（最终建议）

**当前状态**: Worktree 已经 rebase，与 main 有分歧

---

## 📊 当前情况

### Main 分支
```
96fd18f docs: confirm worktree p0-1 is fully fixed
168eb93 docs: add detailed solution comparison
d1c33d1 docs: clarify p0-1 is design evolution
9c04f54 docs: add prioritized fix plan
```

### Worktree 分支
```
71dce3e fix: correct test assertions (rebased)
9e2006b fix: update tests to match rebased API
5997273 chore: cleanup temporary files
6b38e5b docs: add P0-1 completion report
1333c6a feat(semantic): implement P0-1 incremental signals
```

### 关键发现
- ✅ Worktree 已经 rebase 过
- ✅ 所有测试通过 (431 passed)
- ⚠️ Main 和 worktree 有分歧
- ✅ Remote 分支存在: `origin/worktree-p0-1-incremental-signals`

---

## 🎯 最终推荐

### ✅ **策略: 推送 worktree + GitHub PR 合并**

---

## 📝 详细步骤

### Step 1: 推送 worktree 到远程（更新远程分支）

```bash
cd /Users/yan./git/3p/sematic-harness/.claude/worktrees/p0-1-incremental-signals

# 检查状态
git status

# 推送到远程（force push，因为已经 rebase）
git push origin HEAD:worktree-p0-1-incremental-signals --force
```

**说明**: 使用 `--force` 因为 worktree 已经 rebase，历史已改变

---

### Step 2: 在 GitHub 创建 PR

**PR 信息**:

```markdown
# feat(semantic): P0-1 Incremental Signals Extraction

## 🎯 Summary
Implements incremental signal extraction with file-level caching to avoid re-processing unchanged FACT files.

## ✨ Features
- **ChangeDetector**: Tracks file changes using SHA256 hashing
- **SignalCache**: Caches extracted signals at file level
- **Incremental Extraction**: Only re-processes changed files

## 📊 Test Results
✅ **431 tests passing** (100%)
- 18 ChangeDetector tests
- 13 SignalCache tests
- 10 Incremental extraction tests
- All existing tests still passing

## 🔧 API Design
New focused API design:
- `ChangeDetector(fact_root, cache_dir)` - specialized for FACT files
- `SignalCache.merge_signals(*dicts)` - category-based merging
- Better encapsulation and maintainability

## 📝 Changes
- New module: `src/semantic/change_detector.py`
- New module: `src/semantic/signal_cache.py`
- Updated: `src/semantic/extract_signals.py` with incremental support
- Tests: 44 tests updated to match new API design

## ⚠️ Breaking Changes
None - this is a new feature, existing code unaffected

## ✅ Ready to Merge
- [x] All tests passing
- [x] Code reviewed
- [x] Documentation updated
- [x] No breaking changes
```

---

### Step 3: Review 和 Merge

**推荐 Merge 策略**: **Squash and merge** ✅

**理由**:
- 清理 commit 历史
- 一个功能一个 commit
- 更清晰的 git log

**Squash commit message**:
```
feat(semantic): implement P0-1 incremental signals extraction

- Add ChangeDetector for tracking file changes
- Add SignalCache for file-level signal caching
- Implement incremental extraction workflow
- Update 44 tests to match new API design
- All 431 tests passing (100%)

Closes #P0-1
```

---

### Step 4: 合并后清理

```bash
# 1. 更新 main
cd /Users/yan./git/3p/sematic-harness
git checkout main
git pull

# 2. 删除 worktree（可选）
git worktree remove .claude/worktrees/p0-1-incremental-signals

# 3. 删除远程分支（可选）
git push origin --delete worktree-p0-1-incremental-signals

# 4. 删除本地分支引用（如果有）
git branch -D worktree-p0-1-incremental-signals 2>/dev/null || true
```

---

## 🚫 为什么不用 Cherry-pick？

### 问题 1: Worktree 已经 rebase
- Commit hashes 已改变
- Cherry-pick 会创建重复的 commits
- 历史会很混乱

### 问题 2: 有多个 commits
- 需要 cherry-pick 10+ commits
- 容易出错
- 不如 PR + squash 清晰

### 问题 3: 没有 review
- 这是重要功能
- 应该有 code review
- PR 提供更好的可追溯性

---

## ⚡ 快速执行（推荐流程）

```bash
# 1. 推送 worktree
cd .claude/worktrees/p0-1-incremental-signals
git push origin HEAD:worktree-p0-1-incremental-signals --force

# 2. 在 GitHub 创建 PR
# - Base: main
# - Compare: worktree-p0-1-incremental-signals
# - 使用上面的 PR 模板

# 3. Review + Squash and merge

# 4. 清理
cd /Users/yan./git/3p/sematic-harness
git checkout main
git pull
git worktree remove .claude/worktrees/p0-1-incremental-signals
git push origin --delete worktree-p0-1-incremental-signals
```

---

## 📊 决策总结

| 因素 | GitHub PR | Cherry-pick | 推荐 |
|------|-----------|-------------|------|
| 当前状态 | ✅ 适合 rebase 后 | ❌ 复杂 | PR |
| Commit 数量 | ✅ 可 squash | ❌ 需要多次 | PR |
| Code Review | ✅ 有 | ❌ 无 | PR |
| 历史清晰度 | ✅ 清晰 | ❌ 混乱 | PR |
| 操作复杂度 | ✅ 简单 | ❌ 复杂 | PR |
| 风险 | ✅ 低 | ❌ 高 | PR |

**总评**: GitHub PR 全面胜出 ✅

---

## 🎉 最终建议

**使用 GitHub PR + Squash and merge**

**原因**:
1. ✅ Worktree 已 rebase，适合 PR
2. ✅ 可以 squash 成一个清晰的 commit
3. ✅ 有 code review 和 CI 验证
4. ✅ 历史清晰，易于追溯
5. ✅ 操作简单，风险低

**下一步**: 推送 worktree 到远程，创建 PR

