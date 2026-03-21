# Semantic Extract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement unified semantic extraction command that extracts both commit semantics and rules/invariants from git history.

**Architecture:** Single command with `--view` parameter to select output mode (both/commit/rules). Reuses existing git_utils from commit_semantic module. Two separate JSONL outputs for deduplication.

**Tech Stack:** Python, git CLI, LLM (via existing executor pattern)

---

## File Structure

```
prompts/
  └── commit-semantic/
      ├── extract.md              # NEW - rules/invariants prompt (添加到现有目录)
      └── refine.md               # NEW - commit prompt (添加到现有目录)

skills/
  └── semantic-extract/              # NEW - skill directory
      └── SKILL.md                    # NEW - skill definition

src/
  └── semantic_extract/              # NEW - core module
      ├── __init__.py                # NEW
      ├── writer.py                  # NEW - JSONL writer
      └── executor.py                # NEW - LLM executor (reuse prompt_runner)

data/
  ├── commit_refine/                 # NEW - commit JSONL output
  └── rules_invariants/              # NEW - rules JSONL output
```

---

## Task 1: Create Skill Structure

**Files:**
- Create: `prompts/commit-semantic/extract.md`
- Create: `prompts/commit-semantic/refine.md`
- Create: `skills/semantic-extract/SKILL.md`
- Create: `skills/semantic-extract/run.py`
- Create: `src/semantic_extract/__init__.py`

- [ ] **Step 1: Create prompts/commit-semantic/extract.md**

```markdown
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
```

- [ ] **Step 2: Create prompts/commit-semantic/refine.md**

```markdown
# Commit Refinement Prompt

## Context

You are refining a git commit message into conventional commit format.

## Task

Analyze the original commit message and diff, then generate:
- **title**: Conventional commit title (type: short description)
- **body**: Detailed description of the change
- **commit_log**: Key changes as a list

## Types

- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- perf: Performance improvement
- docs: Documentation
- test: Tests
- chore: Maintenance

## Output Format

Return JSON:
```json
{
  "title": "feat: add user authentication",
  "body": "Detailed description...",
  "commit_log": ["line1", "line2"]
}
```
```

- [ ] **Step 3: Create SKILL.md**

```yaml
---
name: semantic-extract
description: Extract semantic information from git commits - both commit_log and rules/invariants
---

# semantic-extract

Extract semantic information from git history with two views:
- **commit view**: functional semantics (what the change does)
- **rules view**: engineering constraints (what must not be broken)

## Usage

/semantic-extract --last 10 --view both
/semantic-extract --last 5 --view rules
/semantic-extract --since 2026-01-01 --view commit

## Parameters

- `--last N`: Process last N commits
- `--since YYYY-MM-DD`: Process commits since date
- `--until YYYY-MM-DD`: Process commits until date
- `--range SHA1..SHA2`: Process commit range
- `--view both|commit|rules`: Which view to extract (default: both)
- `--dry-run`: Preview without writing
- `--incremental`: Skip already processed commits
```

- [ ] **Step 2: Create prompts/extract.md**

```markdown
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
```

- [ ] **Step 3: Create src/semantic_extract/__init__.py**

```python
"""Semantic extract module."""

from .executor import extract_rules_invariants
from .writer import append_commit, append_rules_invariants, load_existing_shas

__all__ = [
    "extract_rules_invariants",
    "append_commit",
    "append_rules_invariants",
    "load_existing_shas",
]
```

- [ ] **Step 4: Commit**

```bash
git add skills/semantic-extract/ src/semantic_extract/
git commit -m "feat(semantic-extract): create skill structure"
```

---

## Task 2: Implement Writer Module

**Files:**
- Create: `src/semantic_extract/writer.py`

- [ ] **Step 1: Write writer.py**

```python
"""JSONL writer for semantic extract outputs."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Set


def get_commit_filename(commit_date: str) -> str:
    """Generate commits_YYYY-MM.jsonl filename."""
    date_part = commit_date[:10] if "T" in commit_date else commit_date[:10]
    year_month = "-".join(date_part.split("-")[:2])
    return f"commits_{year_month}.jsonl"


def get_rules_filename(commit_date: str) -> str:
    """Generate rules_YYYY-MM.jsonl filename."""
    date_part = commit_date[:10] if "T" in commit_date else commit_date[:10]
    year_month = "-".join(date_part.split("-")[:2])
    return f"rules_{year_month}.jsonl"


def load_existing_shas(output_dir: str, prefix: str) -> Set[str]:
    """Load existing SHAs from JSONL files to avoid duplicates."""
    shas: Set[str] = set()
    dir_path = Path(output_dir)
    if not dir_path.exists():
        return shas

    for f in dir_path.glob(f"{prefix}_*.jsonl"):
        with open(f) as fp:
            for line in fp:
                if line.strip():
                    try:
                        record = json.loads(line)
                        shas.add(record.get("sha", ""))
                    except json.JSONDecodeError:
                        continue
    return shas


def load_all_existing_shas() -> tuple[Set[str], Set[str]]:
    """Load SHAs from both commit_refine and rules_invariants directories."""
    commit_shas = load_existing_shas("data/commit_refine", "commits")
    rules_shas = load_existing_shas("data/rules_invariants", "rules")
    return commit_shas, rules_shas


def append_commit(sha: str, title: str, body: str, commit_log: List[str], commit_date: str):
    """Append commit record to JSONL."""
    output_dir = Path("data/commit_refine")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = get_commit_filename(commit_date)
    filepath = output_dir / filename

    record = {
        "sha": sha,
        "title": title,
        "body": body,
        "commit_log": commit_log,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

    with open(filepath, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_rules_invariants(sha: str, rules: List[str], invariants: List[str], commit_date: str):
    """Append rules/invariants record to JSONL."""
    output_dir = Path("data/rules_invariants")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = get_rules_filename(commit_date)
    filepath = output_dir / filename

    record = {
        "sha": sha,
        "rules": rules,
        "invariants": invariants,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

    with open(filepath, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

- [ ] **Step 2: Commit**

```bash
git add src/semantic_extract/writer.py
git commit -m "feat(semantic-extract): add JSONL writer module"
```

---

## Task 3: Implement Executor Module

**Files:**
- Create: `src/semantic_extract/executor.py`

- [ ] **Step 1: Write executor.py**

```python
"""LLM executor for semantic extract."""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def load_prompt(prompt_name: str) -> str:
    """Load prompt template from prompts/commit-semantic directory."""
    # Reuse existing prompt_loader from commit_semantic
    from src.commit_semantic.prompt_runner import load_prompt as _load_prompt
    return _load_prompt(prompt_name)


def build_rules_prompt(diff: str, commit_msg: str = "") -> str:
    """Build prompt for rules/invariants extraction."""
    template = load_prompt("extract")

    prompt = f"""## Git Commit Message
```
{commit_msg}
```

## Diff
```
{diff[:15000]}
```

{template}

Now extract rules and invariants from this diff:"""

    return prompt


def build_commit_prompt(diff: str, commit_msg: str = "") -> str:
    """Build prompt for commit semantic extraction."""
    template = load_prompt("refine")

    prompt = f"""## Original Commit Message
```
{commit_msg}
```

## Diff
```
{diff[:15000]}
```

{template}

Now generate the refined commit:"""

    return prompt


def parse_rules_response(response: str) -> Tuple[List[str], List[str]]:
    """Parse LLM response for rules/invariants."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            rules = data.get("rules", [])
            invariants = data.get("invariants", [])
            return rules, invariants
        except json.JSONDecodeError:
            pass

    # Fallback: try direct JSON
    try:
        data = json.loads(response)
        return data.get("rules", []), data.get("invariants", [])
    except json.JSONDecodeError:
        return [], []


def parse_commit_response(response: str) -> Tuple[str, str, List[str]]:
    """Parse LLM response for commit refinement."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            title = data.get("title", "")
            body = data.get("body", "")
            commit_log = data.get("commit_log", [])
            return title, body, commit_log
        except json.JSONDecodeError:
            pass

    # Fallback
    return "", "", []


def extract_rules_invariants(diff: str, commit_msg: str, executor_fn) -> Tuple[List[str], List[str]]:
    """Extract rules/invariants using LLM."""
    prompt = build_rules_prompt(diff, commit_msg)

    try:
        response = executor_fn(prompt)
        return parse_rules_response(response)
    except Exception as e:
        print(f"Error extracting rules: {e}")
        return [], []


def extract_commit_semantics(diff: str, commit_msg: str, executor_fn) -> Tuple[str, str, List[str]]:
    """Extract commit semantics using LLM."""
    prompt = build_commit_prompt(diff, commit_msg)

    try:
        response = executor_fn(prompt)
        return parse_commit_response(response)
    except Exception as e:
        print(f"Error extracting commit: {e}")
        return "", "", []
```

- [ ] **Step 2: Commit**

```bash
git add src/semantic_extract/executor.py
git commit -m "feat(semantic-extract): add LLM executor module"
```

---

## Task 4: Implement Main Run.py

**Files:**
- Modify: `skills/semantic-extract/run.py`

- [ ] **Step 1: Write run.py**

```python
#!/usr/bin/env python3
"""semantic-extract skill implementation.

Extracts semantic information from git commits - both commit_log and rules/invariants.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.commit_semantic.git_utils import get_commit_list, get_commit_details, get_commit_message
from src.semantic_extract.writer import (
    load_all_existing_shas,
    append_commit,
    append_rules_invariants,
)
from src.semantic_extract.executor import (
    extract_rules_invariants,
    extract_commit_semantics,
)


def process_commits(
    repo_path: str,
    commit_ids: list,
    view: str = "both",
    incremental: bool = False,
    dry_run: bool = False,
    executor_fn=None,
):
    """Process commits and extract semantic information."""

    # Load existing SHAs for deduplication
    commit_shas, rules_shas = load_all_existing_shas() if incremental else (set(), set())

    stats = {
        "total": len(commit_ids),
        "commit_processed": 0,
        "commit_skipped": 0,
        "commit_errors": 0,
        "rules_processed": 0,
        "rules_skipped": 0,
        "rules_errors": 0,
    }

    for idx, commit_id in enumerate(commit_ids):
        print(f"Processing {idx + 1}/{len(commit_ids)}: {commit_id[:8]}...")

        try:
            # Get commit details
            commit = get_commit_details(repo_path, commit_id)
            diff = "\n".join(commit.diff_chunks)

            # Get commit message
            commit_msg = get_commit_message(repo_path, commit_id)

            # Convert Unix timestamp to ISO format for filename
            from datetime import datetime
            commit_date = datetime.fromtimestamp(int(commit.timestamp)).isoformat()

            # Extract commit view
            if view in ("both", "commit"):
                if commit_id in commit_shas:
                    stats["commit_skipped"] += 1
                    print(f"  [SKIP] commit already exists")
                else:
                    try:
                        title, body, commit_log = extract_commit_semantics(
                            diff, commit_msg, executor_fn
                        )
                        if not dry_run:
                            append_commit(commit_id, title, body, commit_log, commit_date)
                        stats["commit_processed"] += 1
                        print(f"  [OK] commit: {title[:50]}...")
                    except Exception as e:
                        stats["commit_errors"] += 1
                        print(f"  [ERROR] commit: {e}")

            # Extract rules view
            if view in ("both", "rules"):
                if commit_id in rules_shas:
                    stats["rules_skipped"] += 1
                    print(f"  [SKIP] rules already exists")
                else:
                    try:
                        rules, invariants = extract_rules_invariants(
                            diff, commit_msg, executor_fn
                        )
                        if not dry_run:
                            append_rules_invariants(commit_id, rules, invariants, commit_date)
                        stats["rules_processed"] += 1
                        print(f"  [OK] rules: {len(rules)} rules, {len(invariants)} invariants")
                    except Exception as e:
                        stats["rules_errors"] += 1
                        print(f"  [ERROR] rules: {e}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            stats["commit_errors"] += 1
            stats["rules_errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Extract semantic information from git commits")
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--last", type=int, help="Process last N commits")
    parser.add_argument("--since", help="Process commits since date (YYYY-MM-DD)")
    parser.add_argument("--until", help="Process commits until date (YYYY-MM-DD)")
    parser.add_argument("--range", help="Process commit range (SHA1..SHA2)")
    parser.add_argument("--view", choices=["both", "commit", "rules"], default="both",
                       help="Which view to extract")
    parser.add_argument("--incremental", action="store_true",
                       help="Skip already processed commits")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview without writing")

    args = parser.parse_args()

    # Get commit list
    commit_ids = get_commit_list(
        repo_path=args.repo_path,
        commit_range=args.range,
        since=args.since,
        until=args.until,
    )

    if args.last:
        commit_ids = commit_ids[:args.last]

    print(f"Found {len(commit_ids)} commits to process")

    # TODO: Wire up executor (injected by Claude Code)
    def default_executor(prompt: str) -> str:
        print("ERROR: No executor configured. Please run via Claude Code with executor injection.")
        sys.exit(1)

    executor_fn = default_executor  # Will be replaced with actual executor

    start_time = time.time()

    stats = process_commits(
        repo_path=args.repo_path,
        commit_ids=commit_ids,
        view=args.view,
        incremental=args.incremental,
        dry_run=args.dry_run,
        executor_fn=executor_fn,
    )

    elapsed = time.time() - start_time

    # Print summary
    print("\n=== Semantic Extract Summary ===")
    print(f"Total commits: {stats['total']}")
    print(f"Commit view: processed={stats['commit_processed']}, skipped={stats['commit_skipped']}, errors={stats['commit_errors']}")
    print(f"Rules view: processed={stats['rules_processed']}, skipped={stats['rules_skipped']}, errors={stats['rules_errors']}")
    print(f"Time elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add skills/semantic-extract/run.py
git commit -m "feat(semantic-extract): add main run.py"
```

---

## Task 5: Test the Implementation

**Files:**
- Test: Run with --dry-run to verify

- [ ] **Step 1: Test with dry-run**

```bash
cd skills/semantic-extract
python run.py . --last 3 --view both --dry-run
```

Expected: Should print commit list and show what would be processed (no files written)

- [ ] **Step 2: Verify data directories created**

```bash
ls -la data/commit_refine/ data/rules_invariants/
```

Expected: Directories should exist (empty if dry-run)

- [ ] **Step 3: Commit**

```bash
git add data/
git commit -m "feat(semantic-extract): add data directories"
```

---

## Acceptance Criteria

- [ ] Single command supports --view both/commit/rules
- [ ] Outputs to data/commit_refine/commits_*.jsonl
- [ ] Outputs to data/rules_invariants/rules_*.jsonl
- [ ] Deduplication works via SHA checking
- [ ] --dry-run shows preview without writing
- [ ] Stats summary printed after completion
- [ ] Reuses git_utils from commit_semantic module
