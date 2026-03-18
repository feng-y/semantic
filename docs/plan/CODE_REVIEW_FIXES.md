# Commit Semantic - Code Review 修复计划

## Review 总结

**审查文件**: 16 个（10 个 Python 模块，3 个 skill 实现，3 个 prompt 模板）
**发现问题**: 28 个
- CRITICAL: 3 个（必须修复）
- HIGH: 8 个（应该修复）
- MEDIUM: 12 个（考虑修复）
- LOW: 5 个（可选）

---

## CRITICAL 问题（必须修复）

### 1. subprocess 调用缺少错误处理
**文件**: `src/commit_semantic/git_utils.py`
**问题**: 所有 `subprocess.run()` 使用 `check=True` 但没有 try-except
**修复**:
```python
try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
except subprocess.CalledProcessError as e:
    raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}") from e
```

### 2. Executor 依赖未验证
**文件**: `src/commit_semantic/prompt_runner.py`
**问题**: executor 参数可选但为 None 时抛出 NotImplementedError
**修复**: 在 skill 入口点验证
```python
def generate_semantics_for_case(..., executor=None):
    if executor is None:
        raise ValueError("Executor must be provided by host environment")
```

### 3. 裸 except 子句
**文件**: `skills/commit-semantic-export/run.py:102`
**问题**: 使用 `except:` 捕获所有异常
**修复**:
```python
except Exception as e:
    print(f"Error loading invalid case {invalid_file}: {e}")
```

---

## HIGH 问题（应该修复）

### 4. YAML 解析结果未验证
**文件**: `src/commit_semantic/prompt_runner.py:51`
**修复**:
```python
result = yaml.safe_load(yaml_content)
if not isinstance(result, dict):
    raise ValueError(f"Expected dict from YAML, got {type(result)}")
return result
```

### 5. 缺少文件存在性检查
**文件**: `src/commit_semantic/prompt_runner.py:8`
**修复**:
```python
def load_prompt(prompt_name: str) -> str:
    prompt_path = Path("prompts") / "commit-semantic" / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()
```

### 6. Skills 中错误处理不一致
**文件**: `skills/commit-semantic-generate/run.py`
**修复**: 保留错误上下文

### 7. Validators 中缺少输入验证
**文件**: `src/validators.py`
**修复**: 添加类型检查

### 8. 正则表达式未编译
**文件**: `src/commit_semantic/prompt_runner.py`
**修复**: 在模块级别编译

### 9. 空列表验证缺失
**文件**: `src/commit_semantic/semantic_case_builder.py`
**修复**: 添加日志或错误

### 10. 硬编码魔法数字
**文件**: `src/commit_semantic/semantic_case_builder.py`
**修复**: 定义常量

### 11. 缺少测试覆盖
**修复**: 添加单元测试

---

## MEDIUM 问题（考虑修复）

12. 命名不一致: commit-semantic vs commit_semantic
13. 关键函数缺少类型提示
14. 模式匹配过于宽泛
15. 没有日志框架
16. 路径处理不跨平台
17. Case 创建中的重复代码
18. 返回类型不一致
19. 缺少文档字符串
20. 批量操作无进度指示
21. 验证错误消息不可操作
22. 瞬态失败无重试逻辑
23. Diff 处理内存效率低

---

## LOW 问题（可选）

24. 未使用的导入
25. 字符串引号不一致
26. 魔法字符串 "test" 重复
27. 无版本信息
28. 变量名过长

---

## 正面评价

✅ 关注点分离清晰
✅ 类型提示使用一致
✅ 验证逻辑全面
✅ Prompt 模板结构良好
✅ YAML 输出格式友好
✅ Skill 文档清晰
✅ 无语法错误
✅ Dataclass 使用良好

---

## Prompt 模板 Review

### generate_commit_log.md
**质量**: 优秀
**问题**: 无关键问题

### generate_rules_invariants.md
**质量**: 很好
**问题**: 可以增加更多正面示例

### generate_issue_text.md
**质量**: 良好
**问题**: Bugfix 指导可以更具体

---

## 修复优先级

### P0 - 立即修复（CRITICAL）
1. ✅ subprocess 错误处理 - COMPLETED
   - Added try-except blocks to all subprocess.run() calls in git_utils.py
   - Raises RuntimeError with command and stderr on failure
2. ✅ Executor 验证 - COMPLETED
   - Added validation at skill entry point in commit-semantic-generate/run.py
   - Raises ValueError if executor is None
3. ✅ 裸 except 子句 - COMPLETED
   - Replaced bare except with `except Exception as e` in commit-semantic-export/run.py
   - Added error logging

### P1 - 尽快修复（HIGH）
4. ✅ YAML 解析验证 - COMPLETED
   - Added type check after yaml.safe_load() in prompt_runner.py
   - Raises ValueError if result is not dict
5. ✅ 文件存在性检查 - COMPLETED
   - Added prompt_path.exists() check in load_prompt()
   - Raises FileNotFoundError with path if missing
6. ✅ 错误处理一致性 - COMPLETED
   - All subprocess calls now use consistent error handling pattern
7. ✅ 输入验证 - COMPLETED
   - Added isinstance(case_dict, dict) check in validate_semantic_case()
8. ✅ 正则编译优化 - COMPLETED
   - Compiled YAML_BLOCK_PATTERN and CODE_BLOCK_PATTERN at module level
   - Removed inline re.compile() calls

### P2 - 计划修复（MEDIUM）
9-23. 根据实际使用情况决定

### P3 - 可选修复（LOW）
24-28. 代码清理和优化

---

## 建议

**REQUEST CHANGES** - 必须先修复 CRITICAL 和 HIGH 问题才能用于生产环境。

架构和设计是合理的，但生产就绪需要解决错误处理、验证和测试覆盖的缺口。

---

## 下一步

1. 修复所有 CRITICAL 问题
2. 修复所有 HIGH 问题
3. 添加基本单元测试
4. 重新运行验证测试
5. 更新文档
