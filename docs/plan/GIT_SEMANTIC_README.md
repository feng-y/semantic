# 历史代码变更语义抽取系统

从仓库历史 commit 中提炼出可独立成立的主语义包，并为每个主语义包生成结构化语义样本。

## 目标

系统对每个有效语义单元输出：

- `commit_log` - 代码修改主动作
- `rules` - 对象语义约束
- `invariants` - 对象语义保持项
- `issue_text` - 压缩需求句
- `development_type` - 开发类型分类
- `split_suggestion` - 拆分建议

用于：

- 需求理解
- case 检索
- few-shot 样本沉淀
- 经验规则沉淀
- 离线训练数据构造

## 核心原则

### 1. commit 不是 issue 单位

不要假设一个 commit 对应一个 issue_text。commit 只是原始代码变更容器，不是需求单位。

### 2. 小改动块也不是 issue 单位

不要把每个细粒度改动块都直接产出一个 commit_log 和 issue_text。

### 3. 真正单位是 semantic_case

**semantic_case = 可独立成立的主语义包**

一个 semantic_case 对应一个 commit_log 和一个 issue_text。

### 4. 测试、配置、开关默认是附带属性

以下内容默认不是主语义主体：

- tests
- config
- flags
- wiring
- registration
- import/include 调整
- 小型 cleanup

它们默认挂靠主改动动作，不单独形成 issue_text。

### 5. split 是 issue_text 压缩溢出的结果

split_suggestion 不是先验判断，而是在尝试把当前 semantic_case 压缩成一个短的、单主体的 issue_text 时，如果发生语义溢出，则触发 split。

### 6. bugfix 是组合证据判断

bugfix 是高优先级解释方向，但不是单个代码模式判断。正确做法是综合判断 commit_log、rules/invariants、regression/restore/compatibility repair 等证据。

## 系统架构

系统包含 3 个 skill：

1. **collect_cases** - 从 git 历史提取 semantic_case 输入
2. **generate_case_semantics** - 生成语义字段
3. **export_cases** - 导出和统计

## 使用方法

### 1. 收集 semantic cases

```bash
python skills/collect_cases/run.py /path/to/repo \
  --commit-range HEAD~10..HEAD \
  --output-dir data/semantic_case_inputs
```

参数：
- `repo_path` - Git 仓库路径
- `--commit-range` - 提交范围（可选）
- `--author` - 按作者过滤（可选）
- `--since` - 起始日期（可选）
- `--until` - 结束日期（可选）
- `--output-dir` - 输出目录

### 2. 生成语义字段

```bash
python skills/generate_case_semantics/run.py \
  --input-dir data/semantic_case_inputs \
  --output-dir data/semantic_cases \
  --invalid-dir data/invalid_cases
```

**注意**: 此步骤需要 Claude API 集成。当前 `src/prompt_runner.py` 中的 `run_prompt_with_claude` 函数是占位符，需要实现实际的 API 调用。

### 3. 导出结果

```bash
python skills/export_cases/run.py \
  --input-dir data/semantic_cases \
  --output-dir data/exports \
  --invalid-dir data/invalid_cases
```

输出：
- `data/exports/cases.jsonl` - 所有 case 的 JSONL 格式
- `data/exports/summary.json` - 统计摘要

## 数据结构

### SemanticCaseInput

```yaml
case_id: ...
commit_id: ...
module: ...
files: []
diff_chunks: []
related_tests: []

bugfix_evidence:
  weak: []
  medium: []
  strong: []

split_hints:
  too_many_files: false
  too_many_diff_themes: false
  mixed_feature_and_bugfix: false
  unrelated_objects_detected: false
```

### SemanticCaseOutput

```yaml
case_id: ...
commit_id: ...
module: ...

commit_log: ...
issue_text: ...
development_type: ...

rules: []
invariants: []

split_suggestion:
  needs_split: false
  split_reasons: []
```

## 开发类型

- `feature` - 新功能
- `bugfix` - 错误修复
- `refactor` - 重构
- `migration` - 迁移
- `optimize` - 优化

## 校验规则

系统会自动校验：

1. **结构校验** - 必需字段存在
2. **类型校验** - 字段类型正确
3. **枚举校验** - development_type 合法
4. **一致性校验**:
   - issue_text 前缀与 development_type 一致
   - needs_split=false 时 split_reasons 为空
   - commit_log 不得 requirement 化
   - rules/invariants 不得退化为通用开发规范

## TODO

### 必需实现

- [ ] **Claude API 集成** - 在 `src/prompt_runner.py` 中实现 `run_prompt_with_claude` 函数
  - 调用 Claude API
  - 解析 YAML 响应
  - 错误处理

### 可选增强

- [ ] 更智能的文件分组逻辑
- [ ] 更精确的 bugfix 证据检测
- [ ] 支持更多 git 过滤选项
- [ ] 并行处理多个 case
- [ ] 增量处理支持
- [ ] Web UI 界面

## 示例输出

### commit_log

```
在 parser 中补充 legacy 写法的边界检查，并更新对应回归测试。
```

### rules

```yaml
rules:
  - legacy syntax compatibility must be preserved during repair
```

### invariants

```yaml
invariants:
  - historical inputs remain parseable
```

### issue_text

```
bugfix：修复旧DSL写法边界检查
```
