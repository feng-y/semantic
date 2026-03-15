# IBS Team Execution Model（面向 OMC Teams）

本文档定义 OMC Teams 在 IBS 实施过程中的职责分工与交接规则。

---

## Team 职责模型

### Research / Contract
- 读取 requirements
- 设计 schema / template / mapping
- 确保输出模型清晰

### Architecture
- 设计 IBS 与 baseline synthesis 的集成方式
- 保证不破坏当前 runtime 契约

### Coding
- 实现最小必要 runtime 改动
- 加 validators
- 扩 baseline 输出逻辑

### Test
- 编写 stage-specific tests
- 运行 pytest
- 报告失败

### Review
- 审核本阶段输出与 requirements / checklist 是否一致
- 识别 deferred items / risks

### Docs
- 更新 README / USER_GUIDE / design docs / reports

---

## Stage 参与建议

### Stage 1
Research / Contract + Architecture + Review + Docs

### Stage 2
Architecture + Coding + Test + Review

### Stage 3
Research / Contract + Coding + Test + Review

### Stage 4
Architecture + Coding + Test + Review

### Stage 5
Architecture + Coding + Test + Review

### Stage 6
Coding + Test + Review + Docs

---

## 每阶段交接物

每一阶段必须显式交接：

1. Inputs
2. Outputs
3. Acceptance
4. Deferred items（若存在）
