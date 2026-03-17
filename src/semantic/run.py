from pathlib import Path
import argparse
import yaml

STAGES = [
    "step1_signals",
    "step2_candidates",
    "step3_recommend",
    "step4_review",
    "step5_finalize",
]

def load_state(path: Path, mode: str):
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "mode": mode,
        "current_stage": None,
        "completed_stages": [],
        "artifacts": {},
        "errors": [],
        "warnings": [],
        "blocked_reason": None,
    }

def save_state(path: Path, state: dict):
    path.write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")

def next_stage(completed):
    for s in STAGES:
        if s not in completed:
            return s
    return None

def main():
    parser = argparse.ArgumentParser(description="semantic runner")
    parser.add_argument("mode", choices=["next", "all"])
    parser.add_argument("--semantic-root", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    state_path = workspace / "run-state.yaml"
    state = load_state(state_path, args.mode)

    if args.mode == "next":
        stage = next_stage(state.get("completed_stages", []))
        if stage is None:
            print("DONE")
            return
        state["completed_stages"].append(stage)
        state["current_stage"] = stage
        save_state(state_path, state)
        print(f"PASS: {stage}")
        return

    # all mode
    while True:
        stage = next_stage(state.get("completed_stages", []))
        if stage is None:
            break
        if stage == "step5_finalize":
            review = workspace / "review-decisions.yaml"
            evidence = workspace / "evidence-checks.yaml"
            if review.exists():
                data = yaml.safe_load(review.read_text(encoding="utf-8")) or {}
                # Check all decision groups for verify_first
                has_verify_first = False
                for group in ["domains", "concepts", "rules", "demand_models"]:
                    decisions = data.get(group, [])
                    if any(d.get("final_action") == "verify_first" for d in decisions):
                        has_verify_first = True
                        break

                if has_verify_first:
                    # Check if evidence checks exist and are resolved
                    if not evidence.exists():
                        state["blocked_reason"] = "verify_first exists but evidence-checks.yaml is missing"
                        save_state(state_path, state)
                        raise SystemExit("BLOCKED")

                    # Check if any evidence checks are still pending
                    evidence_data = yaml.safe_load(evidence.read_text(encoding="utf-8")) or {}
                    checks = evidence_data.get("evidence_checks", [])
                    if any(c.get("status") == "pending" for c in checks):
                        state["blocked_reason"] = "verify_first items have unresolved evidence checks"
                        save_state(state_path, state)
                        raise SystemExit("BLOCKED")

        state["completed_stages"].append(stage)
        state["current_stage"] = stage
        save_state(state_path, state)

    print("DONE")

if __name__ == "__main__":
    main()
