# Distill Canonical Demands

Extract canonical demands from a module's high-value patterns.

## Input Fields

- `module`: The module name
- `patterns`: List of high-scored commit units for this module

Each pattern has:
- `commit_id`: Source commit ID
- `commit_log`: The LLM-regenerated commit log
- `score`: Quality score (0-10)
- `files`: Files changed

## Task

Review the patterns for this module and distill them into **canonical demands**.

A canonical demand is:
1. **Actionable**: Describes a clear user-facing or developer-facing capability
2. **Distinct**: Not redundant with other demands in the same module
3. **Scoped**: A single unit of work (not a mega-feature)
4. **Verifiable**: Has a clear completion criterion

## Output Format

```yaml
canonical_demands:
  - demand_id: "<module>-01"
    rank: 1
    description: >-
      One-paragraph description of the canonical demand
    source_commits: [<commit_id>]
    evidence: One sentence explaining why this is a high-value demand
    score: <average of source pattern scores>
```

## Process

1. Group semantically similar patterns
2. For each group, synthesize the most complete description
3. Rank by aggregate score and impact
4. Limit to top 5 demands per module
5. Assign sequential demand IDs

## Examples

```
Input:
  module: parser
  patterns:
    - commit_id: abc00001
      commit_log: "在 parser 中新增 AST 解析函数"
      score: 9
    - commit_id: abc00002
      commit_log: "修复 parser 边界条件"
      score: 8

Output:
  canonical_demands:
    - demand_id: "parser-01"
      rank: 1
      description: >-
        实现完整的 DSL AST 解析模块，包括词法分析、语法树构建和边界条件处理。
      source_commits: [abc00001, abc00002]
      evidence: "Two high-scored patterns addressing core parser functionality"
      score: 8.5
```
