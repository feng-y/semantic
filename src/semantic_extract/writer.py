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
