"""
Unified pipeline runner for commit-semantic stages: collect, generate, export.

.. deprecated::
   This module is deprecated. Use ``skills/commit-semantic/run.py`` instead,
   which follows the Team Agent architecture (SKILL.md + prompts/*.md + Task tool).
   See docs/superpowers/ARCHITECTURE.md for the architecture pattern.
"""

import importlib.util
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

repo_root = Path(__file__).parent.parent.parent


def _load_skill(skill_name: str):
    module_path = repo_root / "skills" / skill_name / "run.py"
    spec = importlib.util.spec_from_file_location(f"{skill_name}.run", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load skill module: {skill_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PipelineStage(Enum):
    COLLECT = "collect"
    GENERATE = "generate"
    EXPORT = "export"


@dataclass
class PipelineContext:
    repo_path: str
    commit_range: str | None = None
    data_dir: str = "data"
    executor: Callable | None = None
    incremental: bool = False
    checkpoint_file: str = "data/.pipeline-checkpoint.json"
    exclude_paths: list[str] | None = None


@dataclass
class StageResult:
    stage: str
    success: bool
    duration_seconds: float
    output_dir: str


def _write_checkpoint(ctx: PipelineContext, stage: PipelineStage):
    checkpoint = {
        "last_completed_stage": stage.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_dir": ctx.data_dir,
    }
    Path(ctx.checkpoint_file).parent.mkdir(parents=True, exist_ok=True)
    with open(ctx.checkpoint_file, "w") as f:
        json.dump(checkpoint, f)


def _read_checkpoint(ctx: PipelineContext) -> str | None:
    try:
        with open(ctx.checkpoint_file) as f:
            return json.load(f).get("last_completed_stage")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


_STAGE_ORDER = [PipelineStage.COLLECT, PipelineStage.GENERATE, PipelineStage.EXPORT]


def _run_collect(ctx: PipelineContext) -> StageResult:
    output_dir = str(Path(ctx.data_dir) / "semantic_case_inputs")
    low_value_dir = str(Path(ctx.data_dir) / "low_value_cases")
    state_file = str(Path(ctx.data_dir) / ".commit-semantic-state.json")
    mod = _load_skill("commit-semantic-collect")
    start = time.monotonic()
    mod.collect_cases(
        repo_path=ctx.repo_path,
        commit_range=ctx.commit_range,
        output_dir=output_dir,
        low_value_dir=low_value_dir,
        incremental=ctx.incremental,
        state_file=state_file,
        exclude_paths=ctx.exclude_paths,
    )
    duration = time.monotonic() - start
    _write_checkpoint(ctx, PipelineStage.COLLECT)
    return StageResult(stage="collect", success=True, duration_seconds=duration, output_dir=output_dir)


def _run_generate(ctx: PipelineContext) -> StageResult:
    input_dir = str(Path(ctx.data_dir) / "semantic_case_inputs")
    output_dir = str(Path(ctx.data_dir) / "semantic_cases")
    invalid_dir = str(Path(ctx.data_dir) / "invalid_cases")
    mod = _load_skill("commit-semantic-generate")
    start = time.monotonic()
    mod.generate_semantics(
        input_dir=input_dir,
        output_dir=output_dir,
        invalid_dir=invalid_dir,
        executor=ctx.executor,
    )
    duration = time.monotonic() - start
    _write_checkpoint(ctx, PipelineStage.GENERATE)
    return StageResult(stage="generate", success=True, duration_seconds=duration, output_dir=output_dir)


def _run_export(ctx: PipelineContext) -> StageResult:
    input_dir = str(Path(ctx.data_dir) / "semantic_cases")
    output_dir = str(Path(ctx.data_dir) / "exports")
    invalid_dir = str(Path(ctx.data_dir) / "invalid_cases")
    low_value_dir = str(Path(ctx.data_dir) / "low_value_cases")
    mod = _load_skill("commit-semantic-export")
    start = time.monotonic()
    mod.export_cases(
        input_dir=input_dir,
        output_dir=output_dir,
        invalid_dir=invalid_dir,
        low_value_dir=low_value_dir,
        incremental=ctx.incremental,
    )
    duration = time.monotonic() - start
    _write_checkpoint(ctx, PipelineStage.EXPORT)
    return StageResult(stage="export", success=True, duration_seconds=duration, output_dir=output_dir)


_STAGE_RUNNERS = {
    PipelineStage.COLLECT: _run_collect,
    PipelineStage.GENERATE: _run_generate,
    PipelineStage.EXPORT: _run_export,
}


def _parse_stages(stages: str) -> list:
    if stages == "all":
        return list(_STAGE_ORDER)
    return [PipelineStage(s.strip()) for s in stages.split(",")]


def run_pipeline(
    repo_path: str,
    commit_range: str | None = None,
    stages: str = "all",
    resume: bool = True,
    data_dir: str = "data",
    executor: Callable | None = None,
    incremental: bool = False,
    exclude_paths: list[str] | None = None,
) -> dict:
    ctx = PipelineContext(
        repo_path=repo_path,
        commit_range=commit_range,
        data_dir=data_dir,
        executor=executor,
        incremental=incremental,
        checkpoint_file=str(Path(data_dir) / ".pipeline-checkpoint.json"),
        exclude_paths=exclude_paths,
    )

    requested = _parse_stages(stages)

    last_completed = _read_checkpoint(ctx) if resume else None
    skip_until = None
    if last_completed:
        completed_stage = PipelineStage(last_completed)
        if completed_stage in requested:
            idx = requested.index(completed_stage)
            skip_until = idx + 1

    results = []
    for i, stage in enumerate(requested):
        if skip_until is not None and i < skip_until:
            results.append({"stage": stage.value, "skipped": True})
            continue
        runner = _STAGE_RUNNERS[stage]
        result = runner(ctx)
        results.append({
            "stage": result.stage,
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "output_dir": result.output_dir,
        })

    return {"stages": results, "data_dir": data_dir}
