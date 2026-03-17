# worktree-p0-1 测试失败：Bug 还是需要同步 UT？

**分析日期**: 2026-03-17
**问题**: 44个测试失败

---

## 重新评估：这是 Bug 还是设计演进？

### 答案：**设计演进，需要同步更新测试** ✅

---

## 设计对比分析

### 1. ChangeDetector 设计变更

#### 旧设计 (测试期望)
```python
ChangeDetector(state_file: Path, patterns: List[str])
```

**特点**:
- ✅ 通用性强，可跟踪任意文件模式
- ✅ 灵活，可复用
- ❌ 需要调用者指定模式
- ❌ 不知道具体跟踪什么文件

#### 新设计 (实际实现)
```python
ChangeDetector(fact_root: Path, cache_dir: Path)
```

**特点**:
- ✅ 专门为 FACT → Semantic 设计
- ✅ 硬编码跟踪特定文件（`fact_canonical_sample.yaml` 等）
- ✅ 更简单，调用者不需要知道跟踪什么
- ❌ 不够通用

**评估**: **新设计更好** - 因为这个类就是专门为 FACT → Semantic 设计的，不需要通用性

---

### 2. SignalCache.merge_signals() 设计变更

#### 旧设计 (测试期望)
```python
def merge_signals(cached: List[Dict], new: List[Dict]) -> List[Dict]:
    """简单的列表合并"""
    return cached + new
```

**特点**:
- ✅ 简单直接
- ❌ 不区分信号类型
- ❌ 调用者需要自己管理分类

#### 新设计 (实际实现)
```python
def merge_signals(*signal_dicts: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """分类的字典合并"""
    return {
        'domain_signals': [...],
        'concept_signals': [...],
        'rule_signals': [...],
        'demand_pattern_signals': [...]
    }
```

**特点**:
- ✅ 按类别组织信号
- ✅ 支持多个来源合并
- ✅ 更符合实际数据结构
- ❌ 更复杂

**评估**: **新设计更好** - 因为信号本来就是按类别组织的（domain/concept/rule/demand_pattern）

---

### 3. get_cache_stats() 返回值变更

#### 旧设计 (测试期望)
```python
{
    'cache_entries': int,
    'total_size_bytes': int,
    'cache_dir': str
}
```

#### 新设计 (实际实现)
```python
{
    'indexed_files': int,           # 索引中的文件数
    'cached_signal_files': int,     # 实际缓存的信号文件数
    'cache_dir': str,
    'total_size_bytes': int
}
```

**评估**: **新设计更好** - 提供了更详细的信息（区分索引和实际文件）

---

## 结论

### 这不是 Bug，是设计改进 ✅

**理由**:
1. **新设计更符合实际需求** - 专门为 FACT → Semantic 设计
2. **新设计更合理** - 按类别组织信号
3. **新设计提供更多信息** - 更详细的统计

### 应该做什么？

**同步更新测试** ✅

---

## 修复方案（修正版）

### 推荐：更新测试以匹配新实现 ✅

**理由**:
- 新设计更好，应该保留
- 测试应该反映当前的设计
- 这是正常的开发流程

**需要做的**:

### 1. 更新 test_change_detector.py (18个测试)

**修改所有测试的初始化**:
```python
# 旧测试
def test_change_detector_init(tmp_path):
    state_file = tmp_path / "state.json"
    patterns = ["*.yaml", "*.py"]
    detector = ChangeDetector(state_file, patterns)

# 新测试
def test_change_detector_init(tmp_path):
    fact_root = tmp_path / "fact"
    cache_dir = tmp_path / "cache"
    detector = ChangeDetector(fact_root, cache_dir)

    # 验证新的属性
    assert detector.fact_root == fact_root
    assert detector.cache_dir == cache_dir
    assert detector.state_file == cache_dir / "change_state.json"
```

**修改测试逻辑**:
- 不再测试 `tracked_patterns`（已移除）
- 测试 `get_tracked_files()` 返回硬编码的文件列表
- 创建测试需要的 FACT 文件

---

### 2. 更新 test_signal_cache.py (2个统计测试)

```python
# 旧测试
def test_stats_empty_cache(tmp_path):
    cache = SignalCache(tmp_path)
    stats = cache.get_cache_stats()
    assert stats['cache_entries'] == 0

# 新测试
def test_stats_empty_cache(tmp_path):
    cache = SignalCache(tmp_path)
    stats = cache.get_cache_stats()
    assert stats['indexed_files'] == 0
    assert stats['cached_signal_files'] == 0
```

---

### 3. 更新 merge_signals 相关测试 (7个测试)

```python
# 旧测试
def test_merge_signals_simple(tmp_path):
    cache = SignalCache(tmp_path)
    cached = [{'signal_type': 'cached1'}, {'signal_type': 'cached2'}]
    new = [{'signal_type': 'new1'}]
    merged = cache.merge_signals(cached, new)
    assert len(merged) == 3

# 新测试
def test_merge_signals_simple(tmp_path):
    cache = SignalCache(tmp_path)

    cached = {
        'domain_signals': [{'signal_type': 'cached1'}],
        'concept_signals': [{'signal_type': 'cached2'}]
    }

    new = {
        'domain_signals': [{'signal_type': 'new1'}],
        'rule_signals': [{'signal_type': 'new2'}]
    }

    merged = cache.merge_signals(cached, new)

    # 验证合并结果
    assert len(merged['domain_signals']) == 2  # cached1 + new1
    assert len(merged['concept_signals']) == 1  # cached2
    assert len(merged['rule_signals']) == 1     # new2
```

---

### 4. 更新 test_incremental_extraction.py (10个测试)

这些测试依赖上面的 API，需要相应更新。

---

## 时间估算

| 任务 | 测试数 | 预计时间 |
|------|--------|----------|
| 更新 test_change_detector.py | 18 | 1.5小时 |
| 更新 test_signal_cache.py 统计 | 2 | 15分钟 |
| 更新 merge_signals 测试 | 7 | 1小时 |
| 更新 test_incremental_extraction.py | 10 | 1小时 |
| 验证和调试 | - | 30分钟 |
| **总计** | **37** | **4小时** |

---

## 对比两种方案

### 方案 A: 修复实现以匹配旧测试
- **时间**: 1小时
- **结果**: 保留旧设计（不够好）
- ❌ **不推荐** - 倒退

### 方案 B: 更新测试以匹配新实现 ✅
- **时间**: 4小时
- **结果**: 保留新设计（更好）
- ✅ **推荐** - 正确的方向

---

## 最终建议

### ✅ 同步更新测试，保留新设计

**理由**:
1. **新设计更好** - 更专注、更合理
2. **这是正常的开发流程** - 设计演进需要同步测试
3. **长期收益** - 更好的设计值得投入时间

**执行**:
- 投入 4 小时更新 44 个测试
- 保留新的 API 设计
- 确保测试覆盖新的行为

---

## 回答你的问题

> 是bug 还是要同步改ut

**答案**: **要同步改 UT** ✅

这不是 bug，是设计改进。新设计更好，应该保留，测试需要同步更新。

