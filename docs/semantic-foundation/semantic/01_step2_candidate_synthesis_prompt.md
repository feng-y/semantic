# semantic_asset_build · 第二步实现 Prompt（Claude Code / Codex）

请实现 semantic_asset_build 的第二步：candidate synthesis。

## 目标
把 `signals.yaml` 转成 `candidates.yaml`，并渲染 `candidates.md`。

## 输入
- docs/semantic-foundation/semantic-asset-build/signals.yaml

## 输出
- docs/semantic-foundation/semantic-asset-build/candidate-clusters.yaml
- docs/semantic-foundation/semantic-asset-build/candidates.yaml
- docs/semantic-foundation/semantic-asset-build/candidates.md

## 实现方式
### 程序负责
- 读取 signals.yaml
- 做结构预处理
- 校验模型输出 schema
- 写 canonical YAML
- 渲染 Markdown

### 模型负责
- 把 signals 归并成 candidate clusters
- 给 cluster 定名
- 为 candidate 写：
  - summary
  - boundary
  - type-specific fields

## 输出必须分四类
- domains
- concepts
- rules
- demand_models

## 通用字段要求
每个 candidate 必须包含：
- id
- type
- name
- summary
- boundary
- source_signal_ids
- evidence_refs
- notes

## 类型字段要求
### domain
- role
- not_responsible_for

### concept
- domain
- why_it_matters

### rule
- statement
- rule_type
- consequence_hint

### demand_model
- typical_scenario
- handling_hint

## 关键约束
1. 不要把 raw signals 一对一复制成 candidates，除非确实必要
2. 优先少量、稳定、可评审的 candidates
3. 不要把 implementation trivia 升格成 candidate
4. 必须保留 source_signal_ids 和 evidence_refs
5. 如果无法稳定命名或无法写 boundary，应让实现 fail，而不是胡乱输出

## 建议模块
- src/semantic_asset_build/build_candidates.py
- src/semantic_asset_build/models.py
- src/semantic_asset_build/io_utils.py

## 最终交付
1. 新增/修改的文件列表
2. build_candidates.py 的命令行用法
3. 一个 candidates.yaml 示例片段
4. 尚未解决的边界问题
