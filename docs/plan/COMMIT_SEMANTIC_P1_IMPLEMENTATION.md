# Commit Semantic P1 - Implementation Plan

## Date
2026-03-18

## Overview
基于code review fixes完成后，新增5个约束的实现计划。

## 新增约束

### 1. Skill Pipeline约束
- 外部保持3个skill不变
- 每个skill完成一个完整任务
- skill内部允许子步骤，但不外扩

### 2. 输出目录约束
新增目录结构：
```
data/
├─ raw_commits/           # 原始commit（调试用）
├─ semantic_case_inputs/  # collect输出
├─ semantic_cases/        # 主语义库（高价值）
├─ low_value_cases/       # 低价值样本
├─ invalid_cases/         # 失败样本
└─ exports/
   ├─ cases.jsonl         # 全量case
   ├─ patterns.jsonl      # 模式归并结果
   └─ summary.json        # 统计摘要
```

### 3. 并发粒度约束
- **一个commit一个agent**
- 不允许一个commit内多个agent分头处理
- agent负责该commit的完整闭环：提取→分组→归并→生成→校验→输出

### 4. 价值过滤约束
在collect阶段判断semantic_value：
- `high`: 进入主库
- `medium`: 进入主库或观察
- `low`: 进入low_value_cases/或丢弃

### 5. 去重约束
在export阶段：
- 严格近重复去重（基于dedup_key）
- 高频模式归并（基于pattern_fingerprint）
- 保留canonical sample + frequency

---

## Implementation Tasks

### Phase 1: 数据结构扩展

#### Task 1.1: 扩展 types.py
**文件**: `src/types.py`

新增字段：
```python
@dataclass
class SemanticCaseInput:
    # ... existing fields ...
    semantic_value: str = "medium"  # high/medium/low

@dataclass
class SemanticCaseOutput:
    # ... existing fields ...
    semantic_value: str = "medium"
    dedup_key: str = ""
    pattern_id: str = ""
```

新增枚举：
```python
class SemanticValue(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

#### Task 1.2: 扩展 validators.py
**文件**: `src/validators.py`

新增验证：
- semantic_value枚举验证
- dedup_key格式验证

---

### Phase 2: Collect阶段增强

#### Task 2.1: 实现semantic_value判断
**新文件**: `src/commit_semantic/value_classifier.py`

功能：
```python
def classify_semantic_value(
    commit: RawCommit,
    groups: List[ChangeGroup],
    cases: List[SemanticCaseInput]
) -> str:
    """
    判断semantic_value: high/medium/low

    Low value indicators:
    - format/lint/doc/import only
    - snapshot update only
    - trivial config wiring only
    - pure threshold tweak only
    - 无法形成稳定主语义包

    High value indicators:
    - 明确主对象 + 主动作
    - 能形成稳定commit_log
    - 有对象语义约束价值
    """
    pass
```

判断规则：
- 检查文件类型分布
- 检查diff模式
- 检查change_group质量
- 检查是否能形成稳定语义包

#### Task 2.2: 更新 collect skill
**文件**: `skills/commit-semantic-collect/run.py`

新增逻辑：
```python
# After building semantic_cases
for case in cases:
    value = classify_semantic_value(commit, groups, [case])
    case.semantic_value = value

    if value == "low":
        # Save to low_value_cases/
        output_file = low_value_dir / f"{case.case_id}.yaml"
    else:
        # Save to semantic_case_inputs/
        output_file = input_dir / f"{case.case_id}.yaml"
```

#### Task 2.3: 更新 SKILL.md
**文件**: `skills/commit-semantic-collect/SKILL.md`

新增章节：
- Semantic Value Classification
- Low Value Filtering
- Output Directory Routing

---

### Phase 3: Export阶段增强

#### Task 3.1: 实现去重逻辑
**新文件**: `src/commit_semantic/deduplication.py`

功能：
```python
def generate_dedup_key(case: Dict) -> str:
    """
    生成去重key，基于：
    - module
    - normalized issue_text
    - development_type
    - normalized commit_log
    """
    pass

def deduplicate_cases(cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    返回：(unique_cases, duplicate_cases)
    """
    pass
```

#### Task 3.2: 实现模式归并
**新文件**: `src/commit_semantic/pattern_extraction.py`

功能：
```python
def generate_pattern_fingerprint(case: Dict) -> str:
    """
    生成模式指纹，基于：
    - module
    - development_type
    - normalized issue template
    - modified object class
    - rules/invariants signature
    """
    pass

def extract_patterns(cases: List[Dict]) -> List[Dict]:
    """
    返回pattern列表：
    {
        "pattern_id": "...",
        "count": 10,
        "canonical_case_id": "...",
        "variant_case_ids": [...]
    }
    """
    pass
```

#### Task 3.3: 更新 export skill
**文件**: `skills/commit-semantic-export/run.py`

新增逻辑：
```python
# After loading all cases
cases = load_all_cases(input_dir)

# Deduplication
unique_cases, duplicates = deduplicate_cases(cases)

# Pattern extraction
patterns = extract_patterns(unique_cases)

# Export
export_jsonl(unique_cases, output_dir / "cases.jsonl")
export_jsonl(patterns, output_dir / "patterns.jsonl")

# Update summary
summary = {
    "total_cases": len(cases),
    "unique_cases": len(unique_cases),
    "duplicate_cases": len(duplicates),
    "pattern_count": len(patterns),
    "low_value_cases": count_low_value_cases(),
    # ... other stats
}
```

#### Task 3.4: 更新 SKILL.md
**文件**: `skills/commit-semantic-export/SKILL.md`

新增章节：
- Deduplication Strategy
- Pattern Extraction
- Canonical Sample Selection

---

### Phase 4: Teams Agent支持

#### Task 4.1: 创建commit级批处理入口
**新文件**: `skills/commit-semantic-batch/run.py`

功能：
```python
def process_commit_batch(
    repo_path: str,
    commit_ids: List[str],
    output_base_dir: str,
    executor: Callable
) -> Dict:
    """
    批量处理commit列表
    每个commit完整闭环：
    1. 提取raw commit
    2. 构造change_group
    3. 归并semantic_case
    4. 判断semantic_value
    5. 生成语义字段
    6. 校验
    7. 输出
    """
    results = {
        "success": [],
        "failed": [],
        "low_value": []
    }

    for commit_id in commit_ids:
        try:
            # Complete processing for this commit
            cases = process_single_commit(
                repo_path, commit_id, output_base_dir, executor
            )
            results["success"].extend(cases)
        except Exception as e:
            results["failed"].append({
                "commit_id": commit_id,
                "error": str(e)
            })

    return results
```

#### Task 4.2: 创建teams协调脚本
**新文件**: `scripts/run_with_teams.py`

功能：
```python
def shard_commits(commit_list: List[str], num_agents: int) -> List[List[str]]:
    """将commit列表切片"""
    pass

def run_teams_parallel(
    repo_path: str,
    commit_list: List[str],
    num_agents: int,
    output_dir: str
) -> None:
    """
    使用teams agent并行处理
    - 切片commit列表
    - 为每个agent分配一个shard
    - 每个agent处理其shard中的所有commit
    - 汇总结果
    """
    shards = shard_commits(commit_list, num_agents)

    # Create team and tasks
    team_name = "commit-semantic-batch"
    for i, shard in enumerate(shards):
        task = {
            "subject": f"Process commit shard {i}",
            "description": f"Process {len(shard)} commits",
            "commit_ids": shard
        }
        # Create task for agent
```

---

### Phase 5: 文档更新

#### Task 5.1: 更新主README
**文件**: `docs/plan/git-sematic-readme.md`

新增章节：
- 实施约束（5条）
- 输出目录结构
- Semantic Value分类规则
- 去重与模式归并策略
- Teams Agent使用指南

#### Task 5.2: 创建使用指南
**新文件**: `docs/plan/COMMIT_SEMANTIC_USAGE.md`

内容：
- 单机模式使用
- Teams并发模式使用
- 输出文件说明
- 常见问题

---

## Implementation Priority

### P0 - 必须实现（核心功能）
1. Task 1.1: 扩展数据结构
2. Task 2.1: semantic_value判断
3. Task 2.2: collect阶段分流
4. Task 3.1: 去重逻辑
5. Task 3.2: 模式归并
6. Task 3.3: export阶段增强

### P1 - 应该实现（效率提升）
7. Task 4.1: commit批处理入口
8. Task 4.2: teams协调脚本

### P2 - 可选实现（文档完善）
9. Task 5.1: 更新主README
10. Task 5.2: 创建使用指南

---

## Testing Strategy

### Unit Tests
- `test_value_classifier.py`: 测试semantic_value判断
- `test_deduplication.py`: 测试去重逻辑
- `test_pattern_extraction.py`: 测试模式归并

### Integration Tests
- `test_collect_with_filtering.py`: 测试collect阶段分流
- `test_export_with_dedup.py`: 测试export阶段去重

### E2E Tests
- `test_full_pipeline_with_filtering.py`: 完整流程测试
- `test_teams_batch_processing.py`: teams并发测试

---

## Estimated Effort

### Phase 1: 数据结构扩展
- 1-2 hours

### Phase 2: Collect阶段增强
- 4-6 hours (value_classifier是核心)

### Phase 3: Export阶段增强
- 4-6 hours (dedup + pattern extraction)

### Phase 4: Teams Agent支持
- 3-4 hours

### Phase 5: 文档更新
- 2-3 hours

**Total**: 14-21 hours

---

## Next Steps

1. Review this plan with user
2. Confirm priority and scope
3. Start with Phase 1 (data structures)
4. Implement Phase 2 (collect filtering)
5. Implement Phase 3 (export dedup/pattern)
6. Add teams support if needed
7. Update documentation

---

## Open Questions

1. **Semantic value判断的具体规则**：是否需要更细粒度的规则？
2. **Pattern fingerprint算法**：使用什么相似度算法？
3. **Canonical sample选择**：按什么标准选择canonical？
4. **Teams agent数量**：默认多少个agent？如何动态调整？
5. **Low value cases保留策略**：全部保留还是采样保留？
