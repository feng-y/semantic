"""Stage registry for demand pipeline execution."""

STAGES = [
    "normalize_issue",
    "map_semantics",
    "match_development_type",
    "build_demand_card",
    "validate_demand_card",
]


def next_stage(completed: list[str]) -> str | None:
    """Return the next pipeline stage based on completed stage names."""
    for stage in STAGES:
        if stage not in completed:
            return stage
    return None
