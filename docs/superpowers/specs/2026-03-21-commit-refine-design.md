# Commit Refine - Commit Log/Title 重写 Skill

## 目标

使用 Claude 重新生成高质量的 commit log 和 commit title。

## 核心特点

- **输出 > 回写**: 结果保存到 JSONL，不直接改写 git 历史
- **增量更新**: 跳过已存在，append 新增
- **分块信号**: commit_log 数组中用空行分隔不同语义块

## 用法

```bash
# 指定单个 commit
/commit-refine --commit abc123...

# 最近 N 个
/commit-refine --last 50

# 日期范围
/commit-refine --since 2025-01-01 --until 2026-01-01

# 全量
/commit-refine --all
```

## 输出

### 目录结构

```
data/commit_refine/
├── commits_2025_01.jsonl
├── commits_2025_02.jsonl
...
└── commits_2026_03.jsonl
```

### 格式 (JSONL)

```jsonl
{"sha":"e61f13091d6e2ce7be8fb0811665a330c227e7cb","title":"feat: 新增 CPU 配置分析工具","body":"支持从 Discovery API 获取实例列表...","commit_log":["新增 CPU 配置分析工具","","支持从 Discovery API 获取实例列表","查询 CPU 型号和核心数"],"generated_at":"2026-03-21T10:00:00Z"}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| sha | string | commit ID |
| title | string | 重写后的 commit title |
| body | string | 重写后的 commit body (title 之后到 footer 之前) |
| commit_log | array | 重写后的 commit log 详情，空行表示分块 |
| generated_at | datetime | 生成时间 |

## 原始数据获取

从 git 获取原始 commit 数据：

```bash
git log {sha} --format="%H%n%s%n%b%n---COMMIT-FOOTER---%n%an%n%ae%n%aI%n%cn%n%ce%n%cI"
```

解析结果：
- 第 1 行: sha
- 第 2 行: title
- 第 3 行~: body (到 ---COMMIT-FOOTER--- 之前)
- footer: ---COMMIT-FOOTER--- 之后的内容 (Co-Authored-By, Signed-off-by 等)
- author name/email, author date
- committer name/email, commit date

## Prompt 设计

### 输入 Prompt

```markdown
# 重写 Commit Message

你是一个 commit message 专家。请根据以下 diff 重写 commit title 和 body。

## 要求

1. title 使用 conventional commits 格式: type: description
2. type 可选: feat, fix, refactor, optimize, docs, test, chore
3. body 详细描述改了什么，为什么改
4. 如果 diff 包含多个语义块，用空行分隔

## Diff

```diff
[这里是 diff 内容]
```

## 输出格式 (JSON)

```json
{
  "title": "feat: 新增 CPU 配置分析工具",
  "body": "支持从 Discovery API 获取实例列表...",
  "commit_log": [
    "新增 CPU 配置分析工具",
    "",
    "支持从 Discovery API 获取实例列表",
    "查询 CPU 型号和核心数"
  ]
}
```

注意: commit_log 是数组，用空行 "" 分隔不同语义块。
```

## 增量逻辑

1. 读取目标 commit range
2. 确定输出月份文件 (如 commits_2026_03.jsonl)
3. 读取现有文件的 sha 集合
4. 对每个 commit:
   - 如果 sha 已存在 → 跳过
   - 如果 sha 不存在 → 调用 Claude 生成 → append 到文件
5. `--force` 强制重新生成所有

### 重复检测

```python
def load_existing_shas(file_path: str) -> Set[str]:
    """读取现有 JSONL 文件，返回 sha 集合"""
    shas = set()
    if os.path.exists(file_path):
        with open(file_path) as f:
            for line in f:
                if line.strip():
                    shas.add(json.loads(line)['sha'])
    return shas
```

## 分块信号

1. 读取目标 commit range
2. 检查每个 sha 是否已存在于对应月份文件
3. 未存在 → 调用 Claude 生成 → append 到文件
4. 已存在 → 跳过
5. `--force` 强制重新生成

## 分块信号

commit_log 数组中用空行 `""` 分隔不同语义块：

```python
commit_log = [
    "新增 CPU 配置分析工具",      # 块 1
    "",                             # 空行 = 分块信号
    "支持从 Discovery API 获取实例列表",  # 块 2
    "查询 CPU 型号和核心数"        # 块 2
]
```

## CLI 参数

| 参数 | 说明 |
|------|------|
| --commit | 指定单个 commit ID |
| --last N | 最近 N 个 commit |
| --since DATE | 开始日期 (YYYY-MM-DD) |
| --until DATE | 结束日期 (YYYY-MM-DD) |
| --all | 全量 |
| --force | 强制重新生成 |
| --output | 自定义输出目录 |

## 示例

```bash
# 最近 50 个 commit
/commit-refine --last 50

# 2025 年全年
/commit-refine --since 2025-01-01 --until 2025-12-31

# 指定单个 commit 验证效果
/commit-refine --commit e61f13091d6e2ce7be8fb0811665a330c227e7cb
```
