"""JSONL writer for semantic extract outputs."""

import json
from datetime import datetime, timezone
from pathlib import Path


def _year_month(commit_date: str) -> str:
    """Extract YYYY-MM from commit date."""
    date_part = commit_date[:10]
    return "-".join(date_part.split("-")[:2])


def _filename(prefix: str, commit_date: str) -> str:
    """Generate {prefix}_YYYY-MM.jsonl filename."""
    return f"{prefix}_{_year_month(commit_date)}.jsonl"


def get_commit_filename(commit_date: str) -> str:
    """Generate commits_YYYY-MM.jsonl filename."""
    return _filename("commits", commit_date)


def get_rules_filename(commit_date: str) -> str:
    """Generate rules_YYYY-MM.jsonl filename."""
    return _filename("rules", commit_date)


def load_existing_shas(output_dir: str, prefix: str) -> set[str]:
    """Load existing SHAs from JSONL files to avoid duplicates."""
    shas: set[str] = set()
    dir_path = Path(output_dir)
    if not dir_path.exists():
        return shas

    for f in dir_path.glob(f"{prefix}_*.jsonl"):
        with open(f) as fp:
            for line in fp:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if sha := record.get("sha"):
                            shas.add(sha)
                    except json.JSONDecodeError:
                        continue
    return shas


def load_all_existing_shas() -> tuple[set[str], set[str]]:
    """Load SHAs from both commit_refine and rules_invariants directories."""
    commit_shas = load_existing_shas("data/commit_refine", "commits")
    rules_shas = load_existing_shas("data/rules_invariants", "rules")
    return commit_shas, rules_shas


def append_commit(sha: str, title: str, body: str, commit_log: list[str], commit_date: str):
    """Append commit record to JSONL."""
    output_dir = Path("data/commit_refine")
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / get_commit_filename(commit_date)

    record = {
        "sha": sha,
        "title": title,
        "body": body,
        "commit_log": commit_log,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(filepath, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_rules_invariants(sha: str, rules: list[str], invariants: list[str], commit_date: str):
    """Append rules/invariants record to JSONL."""
    output_dir = Path("data/rules_invariants")
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / get_rules_filename(commit_date)

    record = {
        "sha": sha,
        "rules": rules,
        "invariants": invariants,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(filepath, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
