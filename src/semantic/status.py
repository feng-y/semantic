"""
Semantic pipeline status reporter.
Reads run-state.yaml and recommends next action.
"""
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

STAGE_SEQUENCE = [
    "step1_signals",
    "step2_candidates",
    "step3_recommend",
    "step4_review",
    "step5_finalize",
]

NEXT_ACTION_MAP = {
    None: "run semantic-signals",
    "step1_signals": "run semantic-candidates",
    "step2_candidates": "run semantic-recommend",
    "step3_recommend": "run semantic-review",
    "step4_review": "run semantic-finalize",
    "step5_finalize": "pipeline complete",
}

@dataclass
class StatusReport:
    current_stage: str | None
    next_action: str
    blocked: bool
    blocked_reason: str | None
    completed: list[str] = field(default_factory=list)

def get_status(workspace: Path) -> StatusReport:
    """Read run-state.yaml and return current status + next action recommendation."""
    state_path = workspace / "run-state.yaml"

    if not state_path.exists():
        return StatusReport(
            current_stage=None,
            next_action="run semantic-signals",
            blocked=False,
            blocked_reason=None,
            completed=[],
        )

    state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    completed = state.get("completed_stages", [])
    current = state.get("current_stage")
    blocked_reason = state.get("blocked_reason")
    blocked = bool(blocked_reason)

    if blocked:
        next_action = f"resolve: {blocked_reason}"
    else:
        # Find last completed stage
        last_completed = completed[-1] if completed else None
        next_action = NEXT_ACTION_MAP.get(last_completed, "run semantic-signals")

    return StatusReport(
        current_stage=current,
        next_action=next_action,
        blocked=blocked,
        blocked_reason=blocked_reason,
        completed=completed,
    )

def main():
    parser = argparse.ArgumentParser(description="Show semantic pipeline status")
    parser.add_argument("--workspace", required=True, help="Workspace directory")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    report = get_status(workspace)

    print(f"Current stage:  {report.current_stage or 'none'}")
    print(f"Completed:      {', '.join(report.completed) or 'none'}")
    print(f"Blocked:        {report.blocked}")
    if report.blocked_reason:
        print(f"Blocked reason: {report.blocked_reason}")
    print(f"Next action:    {report.next_action}")

    return 1 if report.blocked else 0

if __name__ == "__main__":
    sys.exit(main())
