# Artifact Versioning Rules

Discovery and review artifacts are versioned.

Examples:
- repo-facts.v1.md
- repo-facts.v2.md
- repo-understanding.v1.md
- review-summary.v1.md

Retention policy:
- keep latest 3 working versions by default
- keep latest accepted baseline version
- do not delete versions explicitly marked as accepted or checkpointed

Recommended policy:
- discovery/: rolling window of 3 versions
- review/: rolling window of 3 versions
- baseline/: retain accepted versions
