"""
Tests for src/commit_semantic/pipeline.py
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.commit_semantic.pipeline import (
    PipelineContext,
    PipelineStage,
    _run_collect,
    _run_export,
    _run_generate,
    run_pipeline,
)


def mock_executor(prompt: str) -> str:
    return "mock response"


# ---------------------------------------------------------------------------
# Dataclass / enum basics
# ---------------------------------------------------------------------------

def test_pipeline_context_defaults():
    ctx = PipelineContext(repo_path="/repo")
    assert ctx.commit_range is None
    assert ctx.data_dir == "data"
    assert ctx.executor is None
    assert ctx.incremental is False
    assert ctx.checkpoint_file == "data/.pipeline-checkpoint.json"


def test_pipeline_stages_enum():
    assert PipelineStage.COLLECT.value == "collect"
    assert PipelineStage.GENERATE.value == "generate"
    assert PipelineStage.EXPORT.value == "export"


# ---------------------------------------------------------------------------
# Individual stage runners
# ---------------------------------------------------------------------------

def test_run_collect_stage(tmp_path):
    ctx = PipelineContext(
        repo_path=str(tmp_path),
        data_dir=str(tmp_path / "data"),
        checkpoint_file=str(tmp_path / "data" / ".pipeline-checkpoint.json"),
    )
    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        result = _run_collect(ctx)

    mock_mod.collect_cases.assert_called_once()
    call_kwargs = mock_mod.collect_cases.call_args.kwargs
    assert call_kwargs["repo_path"] == str(tmp_path)
    assert "semantic_case_inputs" in call_kwargs["output_dir"]
    assert result.stage == "collect"
    assert result.success is True


def test_run_generate_stage(tmp_path):
    ctx = PipelineContext(
        repo_path=str(tmp_path),
        data_dir=str(tmp_path / "data"),
        executor=mock_executor,
        checkpoint_file=str(tmp_path / "data" / ".pipeline-checkpoint.json"),
    )
    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        result = _run_generate(ctx)

    mock_mod.generate_semantics.assert_called_once()
    call_kwargs = mock_mod.generate_semantics.call_args.kwargs
    assert "semantic_case_inputs" in call_kwargs["input_dir"]
    assert "semantic_cases" in call_kwargs["output_dir"]
    assert call_kwargs["executor"] is mock_executor
    assert result.stage == "generate"
    assert result.success is True


def test_run_export_stage(tmp_path):
    ctx = PipelineContext(
        repo_path=str(tmp_path),
        data_dir=str(tmp_path / "data"),
        checkpoint_file=str(tmp_path / "data" / ".pipeline-checkpoint.json"),
    )
    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        result = _run_export(ctx)

    mock_mod.export_cases.assert_called_once()
    call_kwargs = mock_mod.export_cases.call_args.kwargs
    assert "semantic_cases" in call_kwargs["input_dir"]
    assert "exports" in call_kwargs["output_dir"]
    assert result.stage == "export"
    assert result.success is True


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def test_full_pipeline_with_mock(tmp_path):
    data_dir = str(tmp_path / "data")
    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        result = run_pipeline(
            repo_path=str(tmp_path),
            data_dir=data_dir,
            executor=mock_executor,
            resume=False,
        )

    stages = [s["stage"] for s in result["stages"]]
    assert stages == ["collect", "generate", "export"]
    assert all(s["success"] for s in result["stages"])
    assert mock_mod.collect_cases.call_count == 1
    assert mock_mod.generate_semantics.call_count == 1
    assert mock_mod.export_cases.call_count == 1


# ---------------------------------------------------------------------------
# Checkpoint read/write
# ---------------------------------------------------------------------------

def test_pipeline_checkpoint_written(tmp_path):
    ctx = PipelineContext(
        repo_path=str(tmp_path),
        data_dir=str(tmp_path / "data"),
        checkpoint_file=str(tmp_path / "data" / ".pipeline-checkpoint.json"),
    )
    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        _run_collect(ctx)

    checkpoint_path = Path(ctx.checkpoint_file)
    assert checkpoint_path.exists()
    data = json.loads(checkpoint_path.read_text())
    assert data["last_completed_stage"] == "collect"
    assert data["data_dir"] == ctx.data_dir


def test_pipeline_resume_skips_completed(tmp_path):
    data_dir = str(tmp_path / "data")
    checkpoint_file = str(tmp_path / "data" / ".pipeline-checkpoint.json")

    # Pre-write a checkpoint marking collect as done
    Path(checkpoint_file).parent.mkdir(parents=True, exist_ok=True)
    Path(checkpoint_file).write_text(
        json.dumps({"last_completed_stage": "collect", "data_dir": data_dir})
    )

    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        result = run_pipeline(
            repo_path=str(tmp_path),
            data_dir=data_dir,
            resume=True,
        )

    stages = result["stages"]
    collect_entry = next(s for s in stages if s.get("stage") == "collect" or s.get("stage") is None)
    # collect should be skipped
    skipped = [s for s in stages if s.get("skipped")]
    assert len(skipped) == 1
    assert skipped[0]["stage"] == "collect"
    # generate and export should have run
    assert mock_mod.generate_semantics.call_count == 1
    assert mock_mod.export_cases.call_count == 1


# ---------------------------------------------------------------------------
# Selective stages
# ---------------------------------------------------------------------------

def test_pipeline_selective_stages(tmp_path):
    data_dir = str(tmp_path / "data")
    mock_mod = MagicMock()
    with patch("src.commit_semantic.pipeline._load_skill", return_value=mock_mod):
        result = run_pipeline(
            repo_path=str(tmp_path),
            data_dir=data_dir,
            stages="collect,generate",
            resume=False,
        )

    stages = [s["stage"] for s in result["stages"]]
    assert stages == ["collect", "generate"]
    assert mock_mod.collect_cases.call_count == 1
    assert mock_mod.generate_semantics.call_count == 1
    assert mock_mod.export_cases.call_count == 0
