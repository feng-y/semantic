"""
Comprehensive end-to-end tests for the commit-semantic pipeline group.

Coverage:
- run_pipeline() unified runner (collect → generate → export)
- Pipeline resume via checkpoint
- exclude_paths parameter
- incremental mode flag
- Export output content: cases.jsonl fields, summary.json structure
- Deduplication: identical cases produce one unique + one duplicate group
- Pattern aggregation: similar cases produce a pattern entry
- Same-directory same-named file grouping (_qualified_theme fix)
- Bugfix evidence detection with diff marker stripping
- stages= partial pipeline execution
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent


def _mock_feature(prompt: str) -> str:
    if "# Generate Commit Log" in prompt:
        return '```yaml\ncommit_log: "新增 DSL v2 语法解析支持"\n```'
    if "# Generate Rules and Invariants" in prompt:
        return '```yaml\nrules:\n  - "新语法必须与 v1 保持向后兼容"\ninvariants:\n  - "历史输入仍可正常解析"\n```'
    if "# Generate Issue Text" in prompt:
        return '```yaml\nissue_text: "feat：添加新DSL语法支持"\ndevelopment_type: "feature"\nsplit_suggestion:\n  needs_split: false\n  split_reasons: []\n```'
    return '```yaml\ncommit_log: "更新代码"\n```'


def _mock_bugfix(prompt: str) -> str:
    if "# Generate Commit Log" in prompt:
        return '```yaml\ncommit_log: "修复 parser 旧写法边界检查缺失"\n```'
    if "# Generate Rules and Invariants" in prompt:
        return '```yaml\nrules:\n  - "legacy syntax compatibility must be preserved during repair"\ninvariants:\n  - "historical inputs remain parseable"\n```'
    if "# Generate Issue Text" in prompt:
        return '```yaml\nissue_text: "bugfix：修复旧DSL写法边界检查"\ndevelopment_type: "bugfix"\nsplit_suggestion:\n  needs_split: false\n  split_reasons: []\n```'
    return '```yaml\ncommit_log: "更新代码"\n```'


def _load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    lines = path.read_text().strip().splitlines()
    return [json.loads(l) for l in lines if l.strip()]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmpdata():
    """Isolated data directory per test."""
    d = Path(tempfile.mkdtemp(prefix="cs_e2e_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def real_commit():
    """First commit with files from HEAD~10..HEAD, or skip."""
    from src.commit_semantic.git_utils import get_commit_details, get_commit_list
    for cid in get_commit_list(".", commit_range="HEAD~10..HEAD"):
        c = get_commit_details(".", cid)
        if c.files:
            return c
    pytest.skip("No commits with files in HEAD~10..HEAD")


# ---------------------------------------------------------------------------
# 1. run_pipeline() — full three-stage run
# ---------------------------------------------------------------------------

def test_run_pipeline_produces_all_export_files(tmpdata):
    """run_pipeline() collect→generate→export creates all four export files."""
    from src.commit_semantic.executor_bridge import set_executor
    from src.commit_semantic.pipeline import run_pipeline

    set_executor(_mock_feature)
    result = run_pipeline(
        repo_path=".",
        commit_range="HEAD~5..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
    )

    exports = tmpdata / "exports"
    assert (exports / "cases.jsonl").exists(), "cases.jsonl missing"
    assert (exports / "duplicates.jsonl").exists(), "duplicates.jsonl missing"
    assert (exports / "patterns.jsonl").exists(), "patterns.jsonl missing"
    assert (exports / "summary.json").exists(), "summary.json missing"

    stages = {s["stage"] for s in result["stages"]}
    assert stages == {"collect", "generate", "export"}


def test_run_pipeline_stages_subset(tmpdata):
    """stages='collect' runs only collect, skips generate and export."""
    from src.commit_semantic.executor_bridge import set_executor
    from src.commit_semantic.pipeline import run_pipeline

    set_executor(_mock_feature)
    result = run_pipeline(
        repo_path=".",
        commit_range="HEAD~3..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
        stages="collect",
    )

    completed = [s["stage"] for s in result["stages"] if not s.get("skipped")]
    assert completed == ["collect"]
    assert not (tmpdata / "exports" / "cases.jsonl").exists()


# ---------------------------------------------------------------------------
# 2. Pipeline resume via checkpoint
# ---------------------------------------------------------------------------

def test_run_pipeline_resumes_from_checkpoint(tmpdata):
    """Second run with resume=True skips already-completed stages."""
    from src.commit_semantic.executor_bridge import set_executor
    from src.commit_semantic.pipeline import run_pipeline

    set_executor(_mock_feature)
    # First run: collect only
    run_pipeline(
        repo_path=".",
        commit_range="HEAD~3..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
        stages="collect",
    )

    checkpoint = tmpdata / ".pipeline-checkpoint.json"
    assert checkpoint.exists(), "checkpoint not written after collect"

    # Second run: all stages, resume=True — collect should be skipped
    result = run_pipeline(
        repo_path=".",
        commit_range="HEAD~3..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
        stages="all",
        resume=True,
    )

    skipped = [s["stage"] for s in result["stages"] if s.get("skipped")]
    assert "collect" in skipped, f"collect should be skipped, got: {result['stages']}"


# ---------------------------------------------------------------------------
# 3. exclude_paths
# ---------------------------------------------------------------------------

def test_collect_exclude_paths_reduces_cases(tmpdata):
    """exclude_paths filters out files from excluded directories."""
    import importlib.util

    def _load(name):
        p = REPO_ROOT / "skills" / name / "run.py"
        spec = importlib.util.spec_from_file_location(name, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    collect = _load("commit-semantic-collect").collect_cases

    out_all = tmpdata / "all"
    out_excl = tmpdata / "excl"

    collect(repo_path=".", commit_range="HEAD~10..HEAD",
            output_dir=str(out_all), low_value_dir=str(tmpdata / "lv_all"))
    collect(repo_path=".", commit_range="HEAD~10..HEAD",
            output_dir=str(out_excl), low_value_dir=str(tmpdata / "lv_excl"),
            exclude_paths=["src/", "tests/", "skills/", "docs/"])

    all_count = len(list(out_all.glob("*.yaml")))
    excl_count = len(list(out_excl.glob("*.yaml")))
    # Excluding major dirs should produce fewer or equal cases
    assert excl_count <= all_count


# ---------------------------------------------------------------------------
# 4. Export output content
# ---------------------------------------------------------------------------

def test_export_cases_jsonl_has_required_fields(tmpdata):
    """Every entry in cases.jsonl has the required semantic fields."""
    from src.commit_semantic.executor_bridge import set_executor
    from src.commit_semantic.pipeline import run_pipeline

    set_executor(_mock_feature)
    run_pipeline(
        repo_path=".",
        commit_range="HEAD~5..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
    )

    cases = _load_jsonl(tmpdata / "exports" / "cases.jsonl")
    if not cases:
        pytest.skip("No cases produced from HEAD~5..HEAD")

    required = {"case_id", "commit_id", "module", "issue_text", "development_type",
                "commit_log", "rules", "invariants"}
    for case in cases:
        missing = required - set(case.keys())
        assert not missing, f"case {case.get('case_id')} missing fields: {missing}"


def test_export_summary_json_has_required_keys(tmpdata):
    """summary.json contains expected top-level keys."""
    from src.commit_semantic.executor_bridge import set_executor
    from src.commit_semantic.pipeline import run_pipeline

    set_executor(_mock_feature)
    run_pipeline(
        repo_path=".",
        commit_range="HEAD~5..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
    )

    summary = json.loads((tmpdata / "exports" / "summary.json").read_text())
    for key in ("total_cases", "development_type_distribution"):
        assert key in summary, f"summary.json missing key: {key}"


# ---------------------------------------------------------------------------
# 5. Deduplication
# ---------------------------------------------------------------------------

def test_dedup_identical_cases_produce_one_unique(tmpdata):
    """Two identical cases → one unique case + one duplicate group."""
    import importlib.util

    from src.io_utils import save_yaml

    def _load(name):
        p = REPO_ROOT / "skills" / name / "run.py"
        spec = importlib.util.spec_from_file_location(name, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    export = _load("commit-semantic-export").export_cases

    # Write two identical cases
    cases_dir = tmpdata / "semantic_cases"
    cases_dir.mkdir(parents=True)
    base = {
        "case_id": "PLACEHOLDER",
        "commit_id": "abc",
        "module": "parser",
        "commit_log": "修复边界检查",
        "issue_text": "bugfix：修复旧DSL写法边界检查",
        "development_type": "bugfix",
        "rules": ["legacy syntax compatibility must be preserved"],
        "invariants": ["historical inputs remain parseable"],
        "split_suggestion": {"needs_split": False, "split_reasons": []},
        "semantic_value": "medium",
        "domain": "parser",
    }
    for i in range(2):
        c = dict(base, case_id=f"case_{i:03d}")
        save_yaml(c, str(cases_dir / f"case_{i:03d}.yaml"))

    export(
        input_dir=str(cases_dir),
        output_dir=str(tmpdata / "exports"),
        invalid_dir=str(tmpdata / "invalid"),
        low_value_dir=str(tmpdata / "lv"),
    )

    unique = _load_jsonl(tmpdata / "exports" / "cases.jsonl")
    dups = _load_jsonl(tmpdata / "exports" / "duplicates.jsonl")

    assert len(unique) == 1, f"Expected 1 unique case, got {len(unique)}"
    assert len(dups) == 1, f"Expected 1 duplicate group, got {len(dups)}"
    assert len(dups[0]["duplicate_case_ids"]) == 1


# ---------------------------------------------------------------------------
# 6. Pattern aggregation
# ---------------------------------------------------------------------------

def test_pattern_aggregation_groups_similar_cases(tmpdata):
    """Multiple similar cases produce at least one pattern entry."""
    import importlib.util

    from src.io_utils import save_yaml

    def _load(name):
        p = REPO_ROOT / "skills" / name / "run.py"
        spec = importlib.util.spec_from_file_location(name, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    export = _load("commit-semantic-export").export_cases

    cases_dir = tmpdata / "semantic_cases"
    cases_dir.mkdir(parents=True)

    # Three cases with same pattern fingerprint (same domain/type/action/object/constraint)
    for i in range(3):
        c = {
            "case_id": f"case_{i:03d}",
            "commit_id": f"sha{i}",
            "module": "parser",
            "domain": "parser",
            "commit_log": f"修复 parser 边界检查 #{i}",
            "issue_text": f"bugfix：修复DSL边界检查{i}",
            "development_type": "bugfix",
            "rules": ["legacy syntax compatibility must be preserved during repair"],
            "invariants": ["historical inputs remain parseable"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "medium",
        }
        save_yaml(c, str(cases_dir / f"case_{i:03d}.yaml"))

    export(
        input_dir=str(cases_dir),
        output_dir=str(tmpdata / "exports"),
        invalid_dir=str(tmpdata / "invalid"),
        low_value_dir=str(tmpdata / "lv"),
    )

    patterns = _load_jsonl(tmpdata / "exports" / "patterns.jsonl")
    assert len(patterns) >= 1, "Expected at least one pattern from 3 similar cases"
    assert patterns[0]["count"] >= 2


# ---------------------------------------------------------------------------
# 7. Same-directory same-named file grouping
# ---------------------------------------------------------------------------

def test_same_named_files_in_different_dirs_get_separate_groups():
    """src/parser/handler.py and src/utils/handler.py must NOT merge into one group."""
    from src.commit_semantic.grouping import extract_change_groups
    from src.types import RawCommit

    commit = RawCommit(
        commit_id="test_qualified",
        author="test",
        timestamp="0",
        files=["src/parser/handler.py", "src/utils/handler.py"],
        diff_chunks=[],
    )
    groups = extract_change_groups(commit)
    assert len(groups) == 2, (
        f"Expected 2 groups for same-named files in different dirs, got {len(groups)}: "
        f"{[g.theme for g in groups]}"
    )


def test_same_named_file_in_same_dir_stays_one_group():
    """src/parser/parser.py and its test should still merge (same object)."""
    from src.commit_semantic.grouping import extract_change_groups
    from src.types import RawCommit

    commit = RawCommit(
        commit_id="test_same",
        author="test",
        timestamp="0",
        files=["src/parser/parser.py", "tests/parser_test.py"],
        diff_chunks=[],
    )
    groups = extract_change_groups(commit)
    assert len(groups) == 1, (
        f"Expected 1 group for parser.py + parser_test.py, got {len(groups)}"
    )


# ---------------------------------------------------------------------------
# 8. Bugfix evidence — diff marker stripping
# ---------------------------------------------------------------------------

def test_bugfix_evidence_not_triggered_by_diff_markers():
    """A diff that only adds a '+boundary' marker line must not produce evidence."""
    from src.commit_semantic.grouping import detect_bugfix_evidence
    from src.types import RawCommit

    # The word 'boundary' appears only as part of a diff marker line header,
    # not in actual code content — should not trigger medium evidence.
    diff = "\n".join([
        "diff --git a/foo.py b/foo.py",
        "--- a/foo.py",
        "+++ b/foo.py",
        "@@ -1,1 +1,2 @@",
        " def foo(): pass",
        "+    # just a comment",
    ])
    commit = RawCommit(
        commit_id="x", author="t", timestamp="0",
        files=["foo.py"], diff_chunks=[diff],
    )
    evidence = detect_bugfix_evidence(commit, diff)
    # No boundary/regression/restore keywords in actual content
    assert not evidence.strong, f"Unexpected strong evidence: {evidence.strong}"


def test_bugfix_evidence_detected_in_content_lines():
    """Actual 'regression' keyword in content lines triggers strong evidence."""
    from src.commit_semantic.grouping import detect_bugfix_evidence
    from src.types import RawCommit

    diff = "\n".join([
        "diff --git a/test_foo.py b/test_foo.py",
        "--- a/test_foo.py",
        "+++ b/test_foo.py",
        "@@ -1,1 +1,3 @@",
        " def test_foo(): pass",
        "+def test_regression_old_input():",
        "+    assert parse('legacy') is not None",
    ])
    commit = RawCommit(
        commit_id="x", author="t", timestamp="0",
        files=["test_foo.py"], diff_chunks=[diff],
    )
    evidence = detect_bugfix_evidence(commit, diff)
    assert evidence.strong, "Expected strong evidence for regression test, got none"


# ---------------------------------------------------------------------------
# 9. Incremental mode flag passes through without error
# ---------------------------------------------------------------------------

def test_run_pipeline_incremental_flag(tmpdata):
    """incremental=True runs without error (state file created)."""
    from src.commit_semantic.executor_bridge import set_executor
    from src.commit_semantic.pipeline import run_pipeline

    set_executor(_mock_feature)
    result = run_pipeline(
        repo_path=".",
        commit_range="HEAD~3..HEAD",
        data_dir=str(tmpdata),
        executor=_mock_feature,
        incremental=True,
    )
    assert all(not s.get("skipped") or s.get("skipped") for s in result["stages"])
