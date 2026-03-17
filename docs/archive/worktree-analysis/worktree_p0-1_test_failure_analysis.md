# worktree-p0-1-incremental-signals 测试失败分析（修正版）

**分析日期**: 2026-03-17
**Worktree**: p0-1-incremental-signals
**测试结果**: 44 failed, 388 passed

---

## 问题总结

**是的，这个分支改出 bug 了。** 主要是 **API 签名不匹配** 和 **行为不一致**。

---

## 根本原因

### 问题 1: ChangeDetector 构造函数签名改变 (18个失败)

**测试期望的 API**:
```python
ChangeDetector(state_file: Path, patterns: List[str])
```

**实际实现的 API**:
```python
ChangeDetector(fact_root: Path, cache_dir: Path)
```

**错误**:
```python
# 测试代码
detector = ChangeDetector(state_file, patterns)
# state_file 是 Path, patterns 是 List[str]

# 实际执行
# patterns (List) 被当作 cache_dir (Path)
# 调用 cache_dir.mkdir() 时报错
# AttributeError: 'list' object has no attribute 'mkdir'
```

**影响**: 所有 18 个 `test_change_detector.py` 的测试

---

### 问题 2: SignalCache.get_cache_stats() 返回值不匹配 (2个失败)

**测试期望**:
```python
{
    'cache_entries': int,      # 缓存条目数
    'total_size_bytes': int,
    'cache_dir': str
}
```

**实际返回**:
```python
{
    'indexed_files': int,           # ← 不同的 key
    'cached_signal_files': int,     # ← 额外的 key
    'cache_dir': str,
    'total_size_bytes': int
}
```

**错误**:
```python
stats = cache.get_cache_stats()
assert stats['cache_entries'] == 0  # KeyError: 'cache_entries'
```

**影响**:
- test_stats_empty_cache
- test_stats_with_entries

---

### 问题 3: SignalCache.merge_signals() 签名和行为不匹配 (24个失败)

**测试期望的签名**:
```python
def merge_signals(self, cached: List[Dict], new: List[Dict]) -> List[Dict]:
    """合并两个信号列表，返回列表"""
    return cached + new
```

**实际实现的签名**:
```python
def merge_signals(self, *signal_dicts: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """合并多个信号字典，返回字典"""
    return {
        'domain_signals': [...],
        'concept_signals': [...],
        ...
    }
```

**关键差异**:
1. **参数类型**: 测试期望 `List[Dict]`，实现接受 `Dict[str, List[Dict]]`
2. **返回类型**: 测试期望 `List[Dict]`，实现返回 `Dict[str, List[Dict]]`
3. **行为**: 测试期望简单列表合并，实现做分类合并

**错误示例**:
```python
# 测试代码
cached = [{'signal_type': 'cached1'}, {'signal_type': 'cached2'}]
new = [{'signal_type': 'new1'}]
merged = cache.merge_signals(cached, new)

assert len(merged) == 3  # 期望列表长度 3

# 实际执行
# merged 是字典: {'domain_signals': [], 'concept_signals': [], ...}
# len(merged) == 4 (4个key)
# AssertionError: assert 4 == 3
```

**影响**:
- test_merge_signals_* (7个)
- test_invalidate_cache (逻辑依赖)
- test_incremental_extraction_* (10个，依赖 merge_signals)
- 其他相关测试

---

## 设计冲突分析

### ChangeDetector 的设计变更

**旧设计** (测试期望):
- **通用的文件变更检测器**
- 可以跟踪任意文件模式
- 灵活，可复用

**新设计** (实际实现):
- **专门为 FACT → Semantic 设计**
- 硬编码跟踪特定文件 (`fact_canonical_sample.yaml` 等)
- 不灵活，但更简单

**评估**: 新设计更简单，但破坏了测试契约

---

### SignalCache.merge_signals 的设计变更

**旧设计** (测试期望):
- **简单的列表合并**
- 输入: 两个信号列表
- 输出: 合并后的列表
- 用途: 合并缓存和新提取的信号

**新设计** (实际实现):
- **分类的字典合并**
- 输入: 多个信号字典 (按类别组织)
- 输出: 合并后的字典 (按类别组织)
- 用途: 合并多个来源的分类信号

**评估**: 新设计更复杂，但可能更符合实际需求

---

## 修复方案

### 方案 A: 修复实现以匹配测试 ✅ 推荐

**理由**:
- 测试定义了 API 契约
- 工作量较小
- 保持向后兼容

**需要修改**:

1. **ChangeDetector 构造函数**:
```python
def __init__(self, state_file: Path, patterns: List[str]):
    self.state_file = state_file
    self.tracked_patterns = patterns
    self.state_file.parent.mkdir(parents=True, exist_ok=True)
    # ... 其他初始化
```

2. **SignalCache.get_cache_stats()**:
```python
def get_cache_stats(self) -> Dict[str, Any]:
    index = self.load_index()
    signal_files = list(self.signals_dir.glob("*.json"))

    return {
        'cache_entries': len(index),  # ← 改 key 名
        'total_size_bytes': sum(f.stat().st_size for f in signal_files),
        'cache_dir': str(self.cache_dir)
    }
```

3. **SignalCache.merge_signals()**:
```python
def merge_signals(self, cached: List[Dict], new: List[Dict]) -> List[Dict]:
    """Simple list concatenation"""
    return cached + new
```

**预计时间**: 1小时

---

### 方案 B: 更新测试以匹配新实现

**理由**: 如果新设计确实更好

**需要修改**:
- 重写所有 44 个失败的测试
- 更新测试的期望和断言

**预计时间**: 3-4小时

---

## 推荐方案

**选择方案 A** - 修复实现以匹配测试

**原因**:
1. **测试先行** - 测试定义了预期的 API
2. **工作量小** - 只需调整实现，不需要重写测试
3. **快速修复** - 1小时 vs 3-4小时

---

## 详细修复步骤

### Step 1: 修复 ChangeDetector (30分钟)

```python
# src/semantic/change_detector.py

class ChangeDetector:
    def __init__(self, state_file: Path, patterns: List[str]):
        """
        Initialize change detector.

        Args:
            state_file: Path to state file for tracking changes
            patterns: List of file patterns to track (e.g., ['*.yaml', '*.py'])
        """
        self.state_file = state_file
        self.tracked_patterns = patterns
        self.previous_state = {}
        self.current_state = {}

        # Ensure parent directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def get_tracked_files(self) -> Set[Path]:
        """Get files matching tracked patterns"""
        # 实现文件模式匹配逻辑
        ...
```

### Step 2: 修复 SignalCache.get_cache_stats() (10分钟)

```python
# src/semantic/signal_cache.py

def get_cache_stats(self) -> Dict[str, Any]:
    """Get cache statistics"""
    index = self.load_index()
    signal_files = list(self.signals_dir.glob("*.json"))

    return {
        'cache_entries': len(index),  # ← 改这里
        'total_size_bytes': sum(f.stat().st_size for f in signal_files),
        'cache_dir': str(self.cache_dir)
    }
```

### Step 3: 修复 SignalCache.merge_signals() (20分钟)

```python
# src/semantic/signal_cache.py

def merge_signals(self, cached: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Merge cached and new signal lists.

    Args:
        cached: List of cached signals
        new: List of newly extracted signals

    Returns:
        Merged list (cached + new)
    """
    return cached + new
```

---

## 测试验证

```bash
# 运行失败的测试
pytest tests/semantic/test_change_detector.py -v
pytest tests/semantic/test_signal_cache.py -v
pytest tests/semantic/test_incremental_extraction.py -v

# 预期结果: 44 个测试全部通过
```

---

## 结论

**是的，这个分支改出 bug 了。**

**问题类型**: API 签名不匹配 + 行为不一致

**严重程度**: 中等 (44个测试失败)

**修复难度**: 低 (1小时)

**根本原因**: 实现代码进行了 API 重构，但没有同步更新测试，或者测试是先写的但实现没有遵循测试定义的契约

**建议**: 修复实现以匹配测试期望的 API（方案 A）

