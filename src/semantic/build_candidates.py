from pathlib import Path
import argparse, yaml

def main():
    parser = argparse.ArgumentParser(description="Build candidates from signals")
    parser.add_argument("--input", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--cluster-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--render-md")
    args = parser.parse_args()

    clusters = {
        "domain_candidate_clusters": [],
        "concept_candidate_clusters": [],
        "rule_candidate_clusters": [],
        "demand_model_candidate_clusters": [],
    }
    candidates = {
        "domains": [],
        "concepts": [],
        "rules": [],
        "demand_models": [],
    }
    Path(args.cluster_output).write_text(yaml.safe_dump(clusters, sort_keys=False, allow_unicode=True), encoding="utf-8")
    Path(args.output).write_text(yaml.safe_dump(candidates, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if args.render_md:
        Path(args.render_md).write_text("# Candidates\n\n- (empty)\n", encoding="utf-8")
    print("PASS: step2 scaffold ran")

if __name__ == "__main__":
    main()
