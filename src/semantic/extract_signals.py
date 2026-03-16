from pathlib import Path
import argparse, yaml

def main():
    parser = argparse.ArgumentParser(description="Extract semantic signals")
    parser.add_argument("--semantic-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--render-md")
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "domain_signals": [],
        "concept_signals": [],
        "rule_signals": [],
        "demand_pattern_signals": [],
    }
    out.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if args.render_md:
        Path(args.render_md).write_text("# Signals\n\n- (empty)\n", encoding="utf-8")
    print("PASS: step1 scaffold ran")

if __name__ == "__main__":
    main()
