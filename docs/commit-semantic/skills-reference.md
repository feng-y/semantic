# commit-semantic Skills 参考

本文档描述三个 Claude Code skill 的接口与行为。这些 skill 在 Claude Code 对话框中通过 `/` 命令调用，由 Claude 解析自然语言参数后执行。

---

## commit-semantic-collect

**调用方式**

```
/commit-semantic-collect <自然语言范围描述>
```

**参数映射**

| 用户描述 | 转换参数 |
|---------|---------|
| 最近 N 个 commit | `commit_range="HEAD~N..HEAD"` |
| 最近一周 / 一个月 / N 天 | `since="N days ago"` 等 |
| YYYY-MM-DD 到 YYYY-MM-DD | `since=` / `until=` |
| 某人的 commit | `author="姓名"` |
| 增量模式 | `incremental=True` |
| 排除 X 目录 | `exclude_paths=["X/"]` |

`repo_path` 默认为当前工作目录。

**输出**：`data/semantic_case_inputs/*.yaml`，低价值 case 进入 `data/low_value_cases/`

**不负责**：生成 commit_log、rules、issue_text、development_type

---

## commit-semantic-generate

**调用方式**

```
/commit-semantic-generate
```

无需参数。读取 `data/semantic_case_inputs/`，为每个 case 调用三个内部 prompt：

1. `generate_commit_log` — 生成代码修改动作描述
2. `generate_rules_invariants` — 生成对象级语义约束
3. `generate_issue_text` — 生成 issue_text / development_type / split_suggestion

**输出**：`data/semantic_cases/*.yaml`，校验失败进入 `data/invalid_cases/`

**校验规则**
- `issue_text` 前缀必须与 `development_type` 一致
- `rules`/`invariants` 不得退化为通用开发规范
- `needs_split=false` 时 `split_reasons` 必须为空

**不负责**：git 扫描、semantic_case 归并、导出

---

## commit-semantic-export

**调用方式**

```
/commit-semantic-export
/commit-semantic-export 增量模式
```

读取 `data/semantic_cases/`，执行严格去重与高频模式归并。

**输出**

| 文件 | 内容 |
|------|------|
| `data/exports/cases.jsonl` | 去重后唯一 case |
| `data/exports/duplicates.jsonl` | 重复组 |
| `data/exports/patterns.jsonl` | 高频模式（按 domain 聚合） |
| `data/exports/summary.json` | 统计 + 告警 |

**去重主键**：`module + development_type + normalized_issue_text`

**pattern fingerprint**：`domain + development_type + action_class + object_class + constraint_class`

**pattern 数量告警阈值**（单 domain）
- < 10：优秀
- 10–20：可接受
- > 20：告警
- > 30：严重，归并策略可能失效

**不负责**：重写语义字段、重新生成 case
