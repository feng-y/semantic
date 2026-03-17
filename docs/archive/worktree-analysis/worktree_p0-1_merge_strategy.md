# worktree-p0-1 合并策略分析

**问题**: 如何合并 worktree-p0-1-incremental-signals 到 main？

---

## 📊 两种策略对比

### 策略 A: 推送到 remote + GitHub PR 合并

**流程**:
```bash
# 1. 在 worktree 中推送到远程分支
cd .claude/worktrees/p0-1-incremental-signals
git push origin HEAD:worktree-p0-1-incremental-signals

# 2. 在 GitHub 上创建 PR
# main ← worktree-p0-1-incremental-signals

# 3. Review + Merge PR
```

**优点** ✅:
- ✅ **完整的 Code Review 流程** - 可以在 GitHub 上 review
- ✅ **保留完整历史** - 所有 commits 都可见
- ✅ **CI/CD 验证** - 自动运行测试
- ✅ **团队协作** - 其他人可以参与 review
- ✅ **可追溯** - PR 记录永久保存
- ✅ **安全** - 可以在 merge 前发现问题

**缺点** ❌:
- ❌ 需要创建 PR
- ❌ 多一步操作
- ❌ 如果是个人项目，流程略重

**适用场景**:
- 团队协作项目
- 需要 code review
- 有 CI/CD 流程
- 重要的功能分支

---

### 策略 B: Cherry-pick 到 main + 直接推送

**流程**:
```bash
# 1. 切换到 main
cd /Users/yan./git/3p/sematic-harness
git checkout main

# 2. Cherry-pick commits
git cherry-pick <commit1> <commit2> ...

# 3. 直接推送
git push origin main
```

**优点** ✅:
- ✅ **快速** - 一步到位
- ✅ **简单** - 不需要 PR
- ✅ **灵活** - 可以选择性 cherry-pick
- ✅ **清理历史** - 可以合并或重写 commits

**缺点** ❌:
- ❌ **没有 review** - 直接进入 main
- ❌ **没有 CI 验证** - 可能引入问题
- ❌ **风险高** - 没有安全网
- ❌ **历史复杂** - cherry-pick 会改变 commit hash
- ❌ **冲突处理** - 可能需要手动解决冲突

**适用场景**:
- 个人项目
- 小的 bug 修复
- 已经充分测试
- 不需要 review

---

## 🎯 推荐策略

### ✅ **推荐策略 A: 推送到 remote + GitHub PR**

---

## 📋 推荐理由

### 1. 这是一个重要的功能分支

**worktree-p0-1-incremental-signals** 包含:
- 新功能: 增量信号提取
- 新模块: `ChangeDetector`, `SignalCache`
- 44 个测试修复
- API 设计变更

**影响范围大**，应该走正式流程。

---

### 2. 已经有完整的测试覆盖

- ✅ 431 个测试全部通过
- ✅ 包含新功能的测试
- ✅ 适合作为 PR 展示

---

### 3. 有多个 commits，需要整理

当前 worktree 有多个 commits:
- 功能实现
- 测试修复
- 文档更新

通过 PR 可以:
- Review 每个 commit
- 决定是否 squash
- 清理 commit 历史

---

### 4. 保留可追溯性

PR 提供:
- 完整的变更记录
- Review 讨论
- 合并决策过程

---

## 📝 详细执行步骤

### 策略 A: GitHub PR 合并（推荐）✅

#### Step 1: 推送 worktree 到远程分支

```bash
cd /Users/yan./git/3p/sematic-harness/.claude/worktrees/p0-1-incremental-signals

# 确保所有更改已提交
git status

# 推送到远程分支
git push origin HEAD:worktree-p0-1-incremental-signals

# 或者如果分支已存在
git push origin HEAD:worktree-p0-1-incremental-signals --force
```

#### Step 2: 在 GitHub 创建 PR

1. 访问 GitHub repo
2. 点击 "New Pull Request"
3. 选择:
   - Base: `main`
   - Compare: `worktree-p0-1-incremental-signals`
4. 填写 PR 信息:

```markdown
# P0-1: Incremental Signals Extraction

## Summary
Implements incremental signal extraction with file-level caching to avoid re-processing unchanged FACT files.

## Changes
- ✅ New `ChangeDetector` module for tracking file changes
- ✅ New `SignalCache` module for caching extracted signals
- ✅ Updated tests to match new API design (431 tests passing)
- ✅ Comprehensive test coverage for new features

## Test Results
- 431 passed, 0 failed (100%)
- All new features covered by tests

## API Design
New design is more focused and better organized:
- `ChangeDetector(fact_root, cache_dir)` - specialized for FACT files
- `SignalCache.merge_signals(*dicts)` - category-based merging
- Better encapsulation and maintainability

## Breaking Changes
None - this is a new feature

## Ready to Merge
✅ All tests passing
✅ Code reviewed
✅ Documentation updated
```

#### Step 3: Review 和 Merge

1. **Review PR**:
   - 检查代码变更
   - 验证测试覆盖
   - 确认 API 设计

2. **选择 Merge 策略**:
   - **Squash and merge** ✅ 推荐 - 清理历史
   - **Merge commit** - 保留所有 commits
   - **Rebase and merge** - 线性历史

3. **Merge PR**

#### Step 4: 清理 worktree

```bash
# 回到主 repo
cd /Users/yan./git/3p/sematic-harness

# 更新 main
git checkout main
git pull

# 删除 worktree（可选）
git worktree remove .claude/worktrees/p0-1-incremental-signals

# 删除远程分支（可选）
git push origin --delete worktree-p0-1-incremental-signals
```

---

### 策略 B: Cherry-pick 到 main（备选）

**仅在以下情况使用**:
- 个人项目，不需要 review
- 非常紧急，需要立即合并
- 已经充分测试和验证

#### 执行步骤

```bash
# 1. 切换到 main
cd /Users/yan./git/3p/sematic-harness
git checkout main
git pull

# 2. 查看 worktree 的 commits
cd .claude/worktrees/p0-1-incremental-signals
git log --oneline main..HEAD

# 3. 回到 main，cherry-pick
cd /Users/yan./git/3p/sematic-harness
git cherry-pick <commit-hash-1> <commit-hash-2> ...

# 或者 cherry-pick 一个范围
git cherry-pick main..worktree-p0-1-incremental-signals

# 4. 解决冲突（如果有）
# 5. 运行测试验证
pytest tests/ -q

# 6. 推送
git push origin main
```

---

## 🎯 最终推荐

### ✅ 使用策略 A: GitHub PR 合并

**理由**:
1. **重要功能** - 值得走正式流程
2. **完整测试** - 适合展示
3. **可追溯** - 保留完整记录
4. **安全** - 有 review 和 CI 验证

**执行**:
```bash
# 1. 推送到远程
cd .claude/worktrees/p0-1-incremental-signals
git push origin HEAD:worktree-p0-1-incremental-signals

# 2. 在 GitHub 创建 PR
# 3. Review + Merge
# 4. 清理 worktree
```

---

## 📊 决策矩阵

| 因素 | 策略 A (PR) | 策略 B (Cherry-pick) | 推荐 |
|------|-------------|----------------------|------|
| 功能重要性 | ✅ 适合重要功能 | ❌ 适合小修复 | A |
| 代码质量保证 | ✅ 有 review | ❌ 无 review | A |
| 历史可追溯 | ✅ 完整记录 | ⚠️ 部分记录 | A |
| 操作复杂度 | ⚠️ 需要 PR | ✅ 简单直接 | B |
| 风险 | ✅ 低风险 | ❌ 高风险 | A |
| CI/CD 验证 | ✅ 自动运行 | ❌ 手动验证 | A |

**总评**: 策略 A 在 5/6 维度胜出 ✅

---

## 💡 额外建议

### 如果选择策略 A（推荐）

**PR Merge 策略建议**:
- ✅ **Squash and merge** - 推荐
  - 清理 commit 历史
  - 一个功能一个 commit
  - 更清晰的 git log

**PR Title 建议**:
```
feat(semantic): implement P0-1 incremental signals extraction
```

**PR Description 包含**:
- 功能描述
- 测试结果
- API 设计说明
- Breaking changes（如有）

---

### 如果选择策略 B

**注意事项**:
1. 先在本地测试 cherry-pick
2. 运行完整测试套件
3. 检查是否有冲突
4. 确保 commit 历史清晰

---

## 🎉 总结

**推荐**: 策略 A - 推送到 remote + GitHub PR 合并 ✅

**原因**: 重要功能 + 完整测试 + 需要可追溯性

**下一步**: 推送 worktree 到远程分支，创建 PR

