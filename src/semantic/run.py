from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from src.semantic.runner_models import RunState

try:
    from .validate import validate_stage
except ImportError:
    from validate import validate_stage as _validate_stage  # noqa: F401

STAGES = [
    "step1_signals",
    "step2_candidates",
    "step3_recommend",
    "step4_review",
    "step5_finalize",
]


def load_state(path: Path, mode: str) -> RunState:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        # Validate mode is a known Literal value; fallback to param if not
        loaded_mode = data.pop("mode", mode)
        if loaded_mode not in ("next", "all", "resume", "reset"):
            loaded_mode = mode
        return RunState(**data, mode=loaded_mode)
    return RunState(mode=mode)  # type: ignore[arg-type]


def save_state(path: Path, state: RunState):
    path.write_text(
        yaml.safe_dump(state.model_dump(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def next_stage(completed):
    for s in STAGES:
        if s not in completed:
            return s
    return None


def check_finalize_guard(workspace: Path) -> tuple[bool, str]:
    """Returns (is_blocked, reason). is_blocked=True means finalize should not proceed."""
    review = workspace / "review-decisions.yaml"
    evidence = workspace / "evidence-checks.yaml"
    if not review.exists():
        return False, ""
    data = yaml.safe_load(review.read_text(encoding="utf-8")) or {}
    has_verify_first = any(
        any(d.get("final_action") == "verify_first" for d in data.get(group, []))
        for group in ["domains", "concepts", "rules", "demand_models"]
    )
    if not has_verify_first:
        return False, ""
    if not evidence.exists():
        return True, "verify_first exists but evidence-checks.yaml is missing"
    evidence_data = yaml.safe_load(evidence.read_text(encoding="utf-8")) or {}
    checks = evidence_data.get("evidence_checks", [])
    if any(c.get("status") == "pending" for c in checks):
        return True, "verify_first items have unresolved evidence checks"
    return False, ""


def main():
    parser = argparse.ArgumentParser(description="semantic runner")
    parser.add_argument("mode", choices=["next", "all", "resume", "reset"])
    parser.add_argument("--semantic-root", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip post-stage validation (for debugging)")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    state_path = workspace / "run-state.yaml"
    skip_validation = args.skip_validation

    if args.mode == "reset":
        if state_path.exists():
            state_path.unlink()
        print("RESET")
        return

    state = load_state(state_path, args.mode)

    if args.mode in ("next", "resume"):
        stage = next_stage(state.completed_stages)
        if stage is None:
            print("DONE")
            return

        if stage == "step5_finalize":
            is_blocked, reason = check_finalize_guard(workspace)
            if is_blocked:
                state.blocked_reason = reason
                save_state(state_path, state)
                raise SystemExit("BLOCKED")

        state.completed_stages.append(stage)
        state.current_stage = stage
        save_state(state_path, state)
        print(f"PASS: {stage}")
        return

    # all mode
    while True:
        stage = next_stage(state.completed_stages)
        if stage is None:
            break
        if stage == "step5_finalize":
            is_blocked, reason = check_finalize_guard(workspace)
            if is_blocked:
                state.blocked_reason = reason
                save_state(state_path, state)
                raise SystemExit("BLOCKED")

        state.completed_stages.append(stage)
        state.current_stage = stage
        save_state(state_path, state)
        if not skip_validation:
            result = validate_stage(stage, workspace)
            if not result.passed:
                state.blocked_reason = f"Validation failed for {stage}: {'; '.join(result.errors)}"
                save_state(state_path, state)
                raise SystemExit("VALIDATION_FAILED")

    print("DONE")


if __name__ == "__main__":
    main()
