"""
Semantic stage validation.
Validates that each stage produced the expected output artifacts.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ValidationResult:
    stage: str
    passed: bool
    errors: list[str] = field(default_factory=list)


def _load_yaml(path: Path, errors: list[str]):
    """Load a YAML file, appending to errors on failure. Returns None on error."""
    if not path.exists():
        errors.append(f"{path.name} not found")
        return None
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        errors.append(f"{path.name} is not valid YAML")
        return None


def _check_key(data: dict, key: str, filename: str, errors: list[str]) -> bool:
    if key not in data:
        errors.append(f"{filename} missing required key '{key}'")
        return False
    return True


def validate_stage(stage_name: str, workspace: Path) -> ValidationResult:
    """Validate that a stage produced its expected output artifacts."""
    errors: list[str] = []

    if stage_name == "step1_signals":
        data = _load_yaml(workspace / "signals.yaml", errors)
        if data is not None:
            _check_key(data, "domain_signals", "signals.yaml", errors)

    elif stage_name == "step2_candidates":
        data = _load_yaml(workspace / "candidates.yaml", errors)
        if data is not None:
            _check_key(data, "candidates", "candidates.yaml", errors)

    elif stage_name == "step3_recommend":
        data = _load_yaml(workspace / "recommendations.yaml", errors)
        if data is not None:
            _check_key(data, "recommendations", "recommendations.yaml", errors)

    elif stage_name == "step4_review":
        data = _load_yaml(workspace / "review-decisions.yaml", errors)
        if data is not None:
            required_keys = {"domains", "concepts", "rules", "demand_models"}
            if not any(k in data for k in required_keys):
                errors.append(
                    "review-decisions.yaml missing required key "
                    "'domains'/'concepts'/'rules'/'demand_models'"
                )

    elif stage_name == "step5_finalize":
        report = workspace / "finalize-report.yaml"
        assets = workspace / "finalize-assets"
        if not report.exists() and not assets.is_dir():
            errors.append("finalize-report.yaml not found")

    # Unknown stages pass by default

    return ValidationResult(stage=stage_name, passed=len(errors) == 0, errors=errors)
