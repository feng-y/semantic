# Rules & Invariants Extraction Prompt

## Context

You are analyzing a git commit diff to extract semantic constraints.

## Rules Extraction

分析 diff，识别被修改对象周围的语义关系。回答：

- 修改此对象时，什么语义关系/边界不能被破坏？
- 什么对齐关系被恢复或保持？
- 什么兼容性边界需要维持？

### 典型示例
- alignment constraints（对齐约束）
- compatibility boundaries（兼容性边界）
- boundedness requirements（边界要求）
- contract preservation（契约保持）
- mapping consistency（映射一致性）
- subsystem interaction rules（子系统交互规则）

## Invariants Extraction

分析 diff 和代码变更，回答：

- 修改后，什么语义属性必须保持不变？
- 什么契约/协议必须继续满足？
- 什么外部可见的语义行为需要保持？

### 典型示例
- preserved alignment（保持对齐）
- preserved compatibility（保持兼容）
- preserved boundedness（保持边界）
- preserved state consistency（保持状态一致性）
- preserved externally visible semantic behavior（保持外部语义行为）

## 禁止生成

- 空检查建议
- 边界检查建议
- 异常处理建议
- 代码风格建议
- 代码动作的同义改写
- 通用正确性陈述（如"系统不应崩溃"、"代码应编译"）

## Output Format

Return JSON:
```json
{
  "rules": ["rule1", "rule2"],
  "invariants": ["invariant1", "invariant2"]
}
```
