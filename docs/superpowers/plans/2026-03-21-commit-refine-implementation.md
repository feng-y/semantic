# Commit Refine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `/commit-refine` skill，使用 Claude 重新生成 commit log 和 title，保存到 JSONL 文件，支持增量更新。

**Architecture:** 基于现有 `commit-semantic-*` skills 的模式，创建新的 skill 目录结构。核心逻辑：
1. 解析用户输入 (commit id / 范围 / 日期)
2. 获取 commit diff
3. 调用 Claude 生成新的 title/body/commit_log
4. 增量写入 JSONL 文件

**Tech Stack:** Python, Claude API, git

---

## File Structure

```
skills/commit-refine/
├── SKILL.md              # Skill 定义
├── run.py                # 主入口
├── prompts/
│   └── refine.md         # LLM prompt
└── src/
    ├── __init__.py
    ├── git_utils.py      # git 操作
    ├── executor.py       # LLM 调用
    └── writer.py         # JSONL 写入

data/commit_refine/       # 输出目录 (运行时创建)
├── commits_2025_01.jsonl
├── commits_2026_03.jsonl
└── ...
```

---

## Task 1: 创建 Skill 目录结构

**Files:**
- Create: `skills/commit-refine/SKILL.md`
- Create: `skills/commit-refine/run.py`
- Create: `skills/commit-refine/prompts/refine.md`
- Create: `skills/commit-refine/src/__init__.py`
- Create: `skills/commit-refine/src/git_utils.py`
- Create: `skills/commit-refine/src/executor.py`
- Create: `skills/commit-refine/src/writer.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p skills/commit-refine/prompts skills/commit-refine/src
touch skills/commit-refine/src/__init__.py
```

- [ ] **Step 2: 写 SKILL.md**

参考 `skills/commit-semantic-collect/SKILL.md`，创建 skill 定义。

```markdown
---
name: commit-refine
description: 用 Claude 重新生成 commit log 和 title
---

# commit-refine

## Purpose

使用 Claude 重新生成高质量的 commit log 和 title，保存到 JSONL 文件。

## 调用方式

```
/commit-refine 最近 50 个 commit
/commit-refine 最近一个月
/commit-refine 2025-01-01 到 2026-01-01
/commit-refine abc123...
/commit-refine --force
```
```

- [ ] **Step 3: 写 prompts/refine.md**

```markdown
# 重写 Commit Message

你是一个 commit message 专家。请根据以下 diff 重写 commit title 和 body。

## 要求

1. title 使用 conventional commits 格式: type: description
2. type 可选: feat, fix, refactor, optimize, docs, test, chore
3. body 详细描述改了什么，为什么改
4. commit_log 是数组，用空行 "" 分隔不同语义块

## Diff

```diff
{{DIFF}}
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
```

- [ ] **Step 4: Commit**

```bash
git add skills/commit-refine/
git commit -m "feat(commit-refine): 创建 skill 目录结构"
```

---

## Task 2: 实现 git_utils.py

**Files:**
- Modify: `skills/commit-refine/src/git_utils.py`

- [ ] **Step 1: 写 git_utils.py**

```python
"""Git 操作工具"""
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path


def get_commit_list(
    repo_path: str,
    commit_range: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    last: Optional[int] = None,
    author: Optional[str] = None,
) -> List[str]:
    """获取 commit ID 列表"""
    cmd = ["git", "-C", repo_path, "log", "--format=%H"]

    if commit_range:
        cmd.append(commit_range)
    elif last:
        cmd.append(f"HEAD~{last}..HEAD")
    elif since or until:
        if since:
            cmd.extend(["--since", since])
        if until:
            cmd.extend(["--until", until])

    if author:
        cmd.extend(["--author", author])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def get_commit_details(repo_path: str, commit_id: str) -> Dict[str, Any]:
    """获取单个 commit 的详细信息"""
    # 获取 title, body, author, date
    format_str = "%s%n%b%n---COMMIT-FOOTER---%n%an%n%ae%n%aI%n%cn%n%ce%n%cI"
    cmd = ["git", "-C", repo_path, "log", commit_id, f"--format={format_str}", "-1"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    lines = result.stdout.split("\n")
    title = lines[0] if lines else ""

    # 找 footer 位置
    footer_idx = -1
    for i, line in enumerate(lines):
        if line == "---COMMIT-FOOTER---":
            footer_idx = i
            break

    body = ""
    if footer_idx > 0:
        body_lines = lines[1:footer_idx]
        body = "\n".join(body_lines).strip()

    footer = ""
    if footer_idx >= 0 and footer_idx < len(lines) - 1:
        footer = "\n".join(lines[footer_idx + 1:]).strip()

    # author info (footer 后面)
    # 格式: an\nae\naI\ncn\nce\ncI
    meta_lines = lines[footer_idx + 1:] if footer_idx >= 0 else []
    author_name = meta_lines[0] if len(meta_lines) > 0 else ""
    author_email = meta_lines[1] if len(meta_lines) > 1 else ""
    author_date = meta_lines[2] if len(meta_lines) > 2 else ""
    committer_name = meta_lines[3] if len(meta_lines) > 3 else ""
    committer_email = meta_lines[4] if len(meta_lines) > 4 else ""
    commit_date = meta_lines[5] if len(meta_lines) > 5 else ""

    # 获取 diff
    diff_cmd = ["git", "-C", repo_path, "show", commit_id, "--format=", "--patch"]
    diff_result = subprocess.run(diff_cmd, capture_output=True, text=True)
    diff = diff_result.stdout

    return {
        "sha": commit_id,
        "title": title,
        "body": body,
        "footer": footer,
        "author": author_name,
        "author_email": author_email,
        "author_date": author_date,
        "committer": committer_name,
        "committer_email": committer_email,
        "commit_date": commit_date,
        "diff": diff,
    }


def resolve_commit_range(repo_path: str, spec: str) -> str:
    """解析 commit 规格为 git range"""
    # 支持: HEAD~N..HEAD, sha..., :path, 等
    return spec
```

- [ ] **Step 2: Commit**

```bash
git add skills/commit-refine/src/git_utils.py
git commit -m "feat(commit-refine): 添加 git 操作工具"
```

---

## Task 3: 实现 executor.py

**Files:**
- Modify: `skills/commit-refine/src/executor.py`

- [ ] **Step 1: 写 executor.py**

```python
"""LLM 调用"""
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_prompt(prompt_name: str) -> str:
    """加载 prompt 模板"""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def refine_commit(
    commit_details: Dict[str, Any],
    executor: Any,
) -> Dict[str, Any]:
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
    import re
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group(1))
    else:
        # 尝试直接解析
        result = json.loads(response)

    return result
```

- [ ] **Step 2: Commit**

```bash
git add skills/commit-refine/src/executor.py
git commit -m "feat(commit-refine): 添加 LLM 调用"
```

---

## Task 4: 实现 writer.py

**Files:**
- Modify: `skills/commit-refine/src/writer.py`

- [ ] **Step 1: 写 writer.py**

```python
"""JSONL 写入工具"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set


def get_output_filename(commit_date: str) -> str:
    """根据 commit 日期生成月份文件名"""
    # commit_date 格式: 2026-03-12T15:51:37+08:00
    if "T" in commit_date:
        date_part = commit_date.split("T")[0]  # 2026-03-12
        year_month = "-".join(date_part.split("-")[:2])  # 2026-03
        return f"commits_{year_month}.jsonl"
    return f"commits_{datetime.now().strftime('%Y_%m')}.jsonl"


def load_existing_shas(output_dir: Path) -> Set[str]:
    """读取现有文件，返回 sha 集合"""
    shas = set()
    if not output_dir.exists():
        return shas

    for jsonl_file in output_dir.glob("*.jsonl"):
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        shas.add(json.loads(line)["sha"])
                    except json.JSONDecodeError:
                        continue
    return shas


def append_commit(
    output_dir: Path,
    sha: str,
    title: str,
    body: str,
    commit_log: List[str],
) -> None:
    """追加一条 commit 到 JSONL 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 用 commit date 确定月份，这里简化用当前时间
    # 实际应该传入 commit date
    filename = f"commits_{datetime.now().strftime('%Y_%m')}.jsonl"
    filepath = output_dir / filename

    record = {
        "sha": sha,
        "title": title,
        "body": body,
        "commit_log": commit_log,
        "generated_at": datetime.now().isoformat() + "Z",
    }

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

- [ ] **Step 2: Commit**

```bash
git add skills/commit-refine/src/writer.py
git commit -m "feat(commit-refine): 添加 JSONL 写入工具"
```

---

## Task 5: 实现 run.py 主入口

**Files:**
- Modify: `skills/commit-refine/run.py`

- [ ] **Step 1: 写 run.py**

```python
#!/usr/bin/env python3
"""commit-refine skill 主入口"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.commit_refine.src.git_utils import get_commit_list, get_commit_details
from skills.commit_refine.src.executor import refine_commit
from skills.commit_refine.src.writer import get_output_filename, load_existing_shas, append_commit


def commit_refine(
    repo_path: str,
    commit_id: str = None,
    commit_range: str = None,
    since: str = None,
    until: str = None,
    last: int = None,
    force: bool = False,
    output_dir: str = "data/commit_refine",
    executor=None,
):
    """主函数"""
    if executor is None:
        raise ValueError("Executor must be provided by host environment")

    # 1. 获取 commit 列表
    commit_ids = []
    if commit_id:
        commit_ids = [commit_id]
    elif commit_range or since or until or last:
        commit_ids = get_commit_list(
            repo_path,
            commit_range=commit_range,
            since=since,
            until=until,
            last=last,
        )
    else:
        # 默认最近 10 个
        commit_ids = get_commit_list(repo_path, last=10)

    print(f"Found {len(commit_ids)} commits to process")

    # 2. 加载已存在的 sha
    output_path = Path(output_dir)
    existing_shas = load_existing_shas(output_path) if not force else set()

    # 3. 处理每个 commit
    success = 0
    skipped = 0

    for i, sha in enumerate(commit_ids):
        print(f"Processing {i+1}/{len(commit_ids)}: {sha[:8]}...")

        # 跳过已存在的
        if sha in existing_shas:
            print(f"  Skipped (already exists)")
            skipped += 1
            continue

        try:
            # 获取 commit 详情
            details = get_commit_details(repo_path, sha)

            # 调用 LLM 生成新的 title/body/commit_log
            result = refine_commit(details, executor)

            # 写入 JSONL
            append_commit(
                output_path,
                sha=sha,
                title=result.get("title", ""),
                body=result.get("body", ""),
                commit_log=result.get("commit_log", []),
            )

            print(f"  ✓ {result.get('title', '')[:50]}...")
            success += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    print(f"\nDone: {success} processed, {skipped} skipped")


def main():
    parser = argparse.ArgumentParser(description="commit-refine")
    parser.add_argument("repo_path", nargs="?", default=".", help="Repo path")
    parser.add_argument("--commit", help="Single commit ID")
    parser.add_argument("--range", help="Commit range")
    parser.add_argument("--since", help="Since date")
    parser.add_argument("--until", help="Until date")
    parser.add_argument("--last", type=int, help="Last N commits")
    parser.add_argument("--force", action="store_true", help="Force reprocess")
    parser.add_argument("--output", default="data/commit_refine", help="Output directory")

    args = parser.parse_args()

    # TODO: 获取 executor
    executor = None

    commit_refine(
        repo_path=args.repo_path,
        commit_id=args.commit,
        commit_range=args.range,
        since=args.since,
        until=args.until,
        last=args.last,
        force=args.force,
        output_dir=args.output,
        executor=executor,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add skills/commit-refine/run.py
git commit -m "feat(commit-refine): 添加主入口 run.py"
```

---

## Task 6: 集成到 Skill 系统

**Files:**
- Modify: `skills/commit-refine/SKILL.md`

- [ ] **Step 1: 完善 SKILL.md 添加自然语言解析**

```markdown
## 参数映射

| 用户描述 | 转换参数 |
|---------|---------|
| 最近 N 个 commit | `last=N` |
| 最近一周 / 一个月 | `since="1 week ago"` |
| YYYY-MM-DD 到 YYYY-MM-DD | `since`, `until` |
| 强制重新生成 | `--force` |
```

- [ ] **Step 2: Commit**

```bash
git add skills/commit-refine/SKILL.md
git commit -m "feat(commit-refine): 完善 skill 定义"
```

---

## 总结

共 6 个 Task，完成后 `/commit-refine` skill 即可运行。

---

**Plan complete and saved to `docs/superpowers/plans/2026-03-21-commit-refine-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
