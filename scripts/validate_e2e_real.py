#!/usr/bin/env python3
"""
End-to-end validation using real Claude API as executor.
Runs collect → generate → export on this repo's recent commits.
"""
import sys
import json
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import anthropic

client = anthropic.Anthropic()

def claude_executor(prompt: str) -> str:
    """Real Claude API executor."""
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    # Skip thinking blocks, return first text block
    for block in msg.content:
        if hasattr(block, 'text'):
            return block.text
    raise ValueError(f"No text block in response: {msg.content}")


from src.commit_semantic.pipeline import run_pipeline

print("Running commit-semantic pipeline on this repo (HEAD~3..HEAD)...")
result = run_pipeline(
    repo_path=str(repo_root),
    commit_range="HEAD~3..HEAD",
    data_dir="/tmp/cs_real_test",
    executor=claude_executor,
    resume=False,
)

print("\n=== Pipeline Result ===")
for stage in result["stages"]:
    status = "skipped" if stage.get("skipped") else f"{stage['duration_seconds']:.1f}s"
    print(f"  {stage['stage']}: {status}")

exports = Path("/tmp/cs_real_test/exports")
cases = [json.loads(l) for l in (exports / "cases.jsonl").read_text().splitlines() if l.strip()]
summary = json.loads((exports / "summary.json").read_text())

print(f"\n=== Output ===")
print(f"  cases: {len(cases)}")
print(f"  development_type distribution: {summary.get('development_type_distribution', {})}")
print(f"  patterns: {summary.get('pattern_count', 0)}")
print(f"  invalid: {summary.get('invalid_count', 0)}")

print("\n=== Sample case ===")
if cases:
    c = cases[0]
    print(f"  commit_log: {c.get('commit_log')}")
    print(f"  issue_text: {c.get('issue_text')}")
    print(f"  development_type: {c.get('development_type')}")
    print(f"  rules: {c.get('rules', [])[:1]}")
