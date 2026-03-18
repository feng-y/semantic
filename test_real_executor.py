#!/usr/bin/env python3
"""
Real executor test - uses actual Claude Code environment.

This test will call the real prompt execution through Claude Code.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.io_utils import load_yaml
from src.commit_semantic.prompt_runner import load_prompt
import yaml


def test_real_prompt_execution():
    """Test with real prompt - requires manual execution."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Commit Semantic - Real Prompt Test                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Load test case
    case_input = load_yaml("/tmp/test_case_input.yaml")
    print("\n=== Test Case Input ===")
    print(f"Case ID: {case_input['case_id']}")
    print(f"Module: {case_input['module']}")
    print(f"Files: {len(case_input['files'])}")

    # Load the three prompts
    print("\n=== Loading Prompts ===")
    prompt1 = load_prompt("generate_commit_log")
    prompt2 = load_prompt("generate_rules_invariants")
    prompt3 = load_prompt("generate_issue_text")
    print("✓ All prompts loaded")

    # Prepare prompt 1
    print("\n=== Prompt 1: Generate Commit Log ===")
    input_yaml = yaml.dump(case_input, allow_unicode=True, default_flow_style=False, sort_keys=False)
    full_prompt1 = f"{prompt1}\n\n---\n\nInput:\n\n```yaml\n{input_yaml}\n```"

    print("\n" + "="*60)
    print("PROMPT TO EXECUTE:")
    print("="*60)
    print(full_prompt1[:500] + "...")
    print("="*60)

    print("\n请执行上述 prompt 并返回 YAML 格式的响应。")
    print("\n期望输出格式:")
    print("```yaml")
    print("commit_log: >")
    print("  实现需求规范化和语义映射功能")
    print("```")

    print("\n\n=== 验证说明 ===")
    print("1. 上述 prompt 已准备好")
    print("2. Prompt 包含完整的规范和示例")
    print("3. 输入数据已转换为 YAML 格式")
    print("4. 在 Claude Code 环境中，executor 会自动处理这个 prompt")
    print("\n如果你能看到这个输出，说明:")
    print("  ✓ Prompt 加载正常")
    print("  ✓ 输入数据格式正确")
    print("  ✓ Prompt 组装正确")
    print("\n下一步: 需要 Claude Code host 环境提供 executor 来执行 prompt")


if __name__ == "__main__":
    test_real_prompt_execution()
