"""JSONL 写入工具"""
import json
from datetime import datetime
from pathlib import Path


def get_output_filename(commit_date: str) -> str:
    """根据 commit 日期生成月份文件名"""
    # commit_date 格式: 2026-03-12T15:51:37+08:00
    if "T" in commit_date:
        date_part = commit_date.split("T")[0]  # 2026-03-12
        year_month = "-".join(date_part.split("-")[:2])  # 2026-03
        return f"commits_{year_month}.jsonl"
    return f"commits_{datetime.now().strftime('%Y_%m')}.jsonl"


def load_existing_shas(output_dir: Path) -> set[str]:
    """读取现有文件，返回 sha 集合"""
    shas: set[str] = set()
    if not output_dir.exists():
        return shas

    for jsonl_file in output_dir.glob("*.jsonl"):
        with open(jsonl_file, encoding="utf-8") as f:
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
    commit_log: list[str],
    commit_date: str | None = None,
) -> None:
    """追加一条 commit 到 JSONL 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 用 commit date 确定月份
    if commit_date:
        filename = get_output_filename(commit_date)
    else:
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
