"""Git 操作工具"""
import subprocess
from typing import Any


def get_commit_list(
    repo_path: str,
    commit_range: str | None = None,
    since: str | None = None,
    until: str | None = None,
    last: int | None = None,
    author: str | None = None,
) -> list[str]:
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


def get_commit_details(repo_path: str, commit_id: str) -> dict[str, Any]:
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
