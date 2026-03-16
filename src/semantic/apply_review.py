from pathlib import Path
import argparse, yaml

def main():
    parser = argparse.ArgumentParser(description="Generate review skeleton")
    parser.add_argument("--input", required=True)
    parser.add_argument("--review-output", required=True)
    parser.add_argument("--review-md")
    args = parser.parse_args()
    data = {"decisions": []}
    Path(args.review_output).write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if args.review_md:
        Path(args.review_md).write_text("# Review Note\n\n## keep\n- (empty)\n", encoding="utf-8")
    print("PASS: step4 review scaffold ran")

if __name__ == "__main__":
    main()
