# commit-semantic 使用手册

在 Claude Code 对话框中用自然语言调用，Claude 会自动处理当前仓库。

---

## 三步流程

### 第一步：Collect — 提取语义 case

直接描述你想分析的范围：

```
/commit-semantic-collect 最近 10 个 commit
/commit-semantic-collect 最近一个月的 commit
/commit-semantic-collect 2026-01-01 到 2026-03-01 的 commit
/commit-semantic-collect 张三提交的最近 50 个 commit
```

Claude 会扫描当前仓库，将相关改动归并为 semantic case，过滤低价值变更，输出到 `data/semantic_case_inputs/`。

---

### 第二步：Generate — 生成语义字段

```
/commit-semantic-generate
```

Claude 会读取上一步的输出，为每个 case 生成：
- `commit_log` — 代码修改动作描述
- `issue_text` — 单主体压缩句（如 `feat：HTTP 请求增加指数退避重试`）
- `rules / invariants` — 对象级语义约束
- `development_type` — feature / bugfix / refactor / migration / optimize

校验失败的 case 会单独保存到 `data/invalid_cases/`，Claude 会在对话中说明原因。

---

### 第三步：Export — 去重导出

```
/commit-semantic-export
```

Claude 会对有效 case 去重、聚合高频模式，输出到 `data/exports/`：

| 文件 | 内容 |
|------|------|
| `cases.jsonl` | 去重后的唯一 case |
| `duplicates.jsonl` | 重复组 |
| `patterns.jsonl` | 高频模式聚合 |
| `summary.json` | 统计与告警 |

---

## 典型用法

### 快速验证

```
/commit-semantic-collect 最近 10 个 commit
/commit-semantic-generate
/commit-semantic-export
```

### 增量追加

已有历史数据时，只处理新增 commit：

```
/commit-semantic-collect 最近 10 个 commit，增量模式
/commit-semantic-generate
/commit-semantic-export
```

### 排除配置管理目录

```
/commit-semantic-collect 最近 50 个 commit，排除 config 目录
/commit-semantic-generate
/commit-semantic-export
```

---

## 数据目录

```
data/
├── semantic_case_inputs/   # collect 输出
├── semantic_cases/         # generate 输出（有效）
├── low_value_cases/        # 低价值 case（自动过滤）
├── invalid_cases/          # 校验失败 / 生成异常
└── exports/
    ├── cases.jsonl
    ├── duplicates.jsonl
    ├── patterns.jsonl
    └── summary.json
```

---

## 常见问题

**invalid_cases 太多**
generate 完成后 Claude 会说明失败原因。常见原因：
- `issue_text` 前缀与 `development_type` 不一致
- `rules`/`invariants` 包含通用开发规范（如"增加异常处理"）

**low_value_cases 太多**
正常现象，格式变更和 trivial 改动会被自动过滤。

**patterns 数量过多（>20/domain）**
export 完成后 Claude 会在对话中提示，`summary.json` 的 `alerts` 字段也会有说明。

---

## 核心概念

**semantic_case 是最小单位**，不是 commit，不是单个改动块。一个 semantic_case 必须能被压缩成一个短的、单主体 `issue_text`。

**rules/invariants 必须是对象级约束**
- ✓ `legacy syntax compatibility must be preserved during repair`
- ✗ `增加空值判断`（通用规范，会被校验拦截）
