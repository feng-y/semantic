"""LLM 调用"""
import json
import re
from pathlib import Path
from typing import Any

import yaml


def load_prompt(prompt_name: str) -> str:
    """加载 prompt 模板"""
    prompt_path = Path("skills/commit-refine/prompts") / f"{prompt_name}.md"
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()


def refine_commit(
    commit_details: dict[str, Any],
    executor: Any,
) -> dict[str, Any]:
    """调用 LLM 重写 commit message"""
    prompt_template = load_prompt("refine")

    # 截断过长的 diff
    diff = commit_details["diff"]
    max_diff_len = 15000
    if len(diff) > max_diff_len:
        diff = diff[:max_diff_len] + "\n... (truncated)"

    # 构造输入
    input_data = {
        "original_title": commit_details["title"],
        "original_body": commit_details["body"],
        "diff": diff,
    }

    input_yaml = yaml.dump(input_data, allow_unicode=True, default_flow_style=False)
    full_prompt = f"{prompt_template}\n\n---\n\nInput:\n\n```yaml\n{input_yaml}\n```"

    # 调用 LLM
    response = executor(full_prompt)

    # 解析 JSON 响应
    # 尝试从 markdown 代码块中提取
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group(1))
    else:
        # 尝试直接解析
        result = json.loads(response)

    return result
