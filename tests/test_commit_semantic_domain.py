"""Tests for commit-semantic domain utilities and pipeline stages."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

# Ensure src is importable
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.domain_utils import (
    assign_domain_by_path,
    build_sha_file_map,
    build_units_summary,
    choose_domain_winner,
    classify_unit_locally,
    compute_fingerprint,
    fingerprint_matches,
    normalize_domains,
    parse_llm_classifications,
    parse_llm_domains,
    score_unit_for_domain,
    should_merge_domains,
)


# ---------------------------------------------------------------
# T7-T11: build_sha_file_map
# ---------------------------------------------------------------

class TestBuildShaFileMap:
    """Tests for build_sha_file_map."""

    def test_normal_commit(self, tmp_path):
        """T7: Normal commit returns correct file list."""
        # Use the actual repo
        repo = str(Path(__file__).parent.parent)
        result = subprocess.run(
            ["git", "log", "--format=%H", "-1"],
            capture_output=True, text=True, cwd=repo,
        )
        if result.returncode != 0:
            pytest.skip("Not in a git repo")
        sha = result.stdout.strip()
        sha_map, ok = build_sha_file_map(repo, [sha])
        assert ok is True
        assert sha in sha_map
        assert isinstance(sha_map[sha], list)

    def test_empty_shas(self):
        """Empty SHA list returns empty map."""
        sha_map, ok = build_sha_file_map(".", [])
        assert sha_map == {}
        assert ok is True

    def test_missing_sha(self):
        """T10: Non-existent SHA — git may fail or return empty, either is acceptable."""
        repo = str(Path(__file__).parent.parent)
        sha_map, ok = build_sha_file_map(repo, ["0" * 40])
        # git log --no-walk with invalid SHA returns rc=128, which is a git failure
        # Either ok=True with empty map, or ok=False with fallback — both acceptable
        if ok:
            assert "0" * 40 not in sha_map or sha_map["0" * 40] == []
        else:
            assert sha_map == {"0" * 40: []}

    def test_git_failure(self, tmp_path):
        """T11: git failure returns empty lists + success=False."""
        sha_map, ok = build_sha_file_map(str(tmp_path), ["abc123"])
        assert ok is False
        assert sha_map == {"abc123": []}


# ---------------------------------------------------------------
# T12-T14: assign_domain_by_path
# ---------------------------------------------------------------

SAMPLE_DOMAINS = [
    {"domain": "semantic", "paths": ["src/semantic/"], "keywords": ["semantic"]},
    {"domain": "commit", "paths": ["src/commit_semantic/", "skills/commit-"], "keywords": ["commit"]},
    {"domain": "demand", "paths": ["src/demand/"], "keywords": ["demand"]},
]


class TestAssignDomainByPath:
    """Tests for assign_domain_by_path."""

    def test_single_domain(self):
        """T12: All files in same domain → returns that domain."""
        result = assign_domain_by_path(
            ["src/semantic/signals.py", "src/semantic/candidates.py"],
            SAMPLE_DOMAINS,
        )
        assert result == "semantic"

    def test_mixed_domains(self):
        """T13: Files span multiple domains → returns None."""
        result = assign_domain_by_path(
            ["src/semantic/signals.py", "src/demand/pipeline.py"],
            SAMPLE_DOMAINS,
        )
        assert result is None

    def test_no_match(self):
        """Files match no domain → returns None."""
        result = assign_domain_by_path(
            ["README.md", "setup.py"],
            SAMPLE_DOMAINS,
        )
        assert result is None

    def test_empty_paths(self):
        """Empty file paths → returns None."""
        assert assign_domain_by_path([], SAMPLE_DOMAINS) is None

    def test_empty_domains(self):
        """Empty domain list → returns None."""
        assert assign_domain_by_path(["src/foo.py"], []) is None

    def test_longest_prefix_wins(self):
        """Longest prefix match wins over shorter."""
        domains = [
            {"domain": "broad", "paths": ["src/"], "keywords": []},
            {"domain": "specific", "paths": ["src/semantic/"], "keywords": []},
        ]
        result = assign_domain_by_path(["src/semantic/foo.py"], domains)
        assert result == "specific"


# ---------------------------------------------------------------
# T1-T6: discover (parse_llm_domains, fingerprint)
# ---------------------------------------------------------------

class TestDeterministicClassification:
    """Tests for deterministic unit scoring and classification."""

    DOMAINS = [
        {
            "domain": "auth",
            "description": "Authentication and sessions",
            "paths": ["src/auth/"],
            "keywords": ["auth", "login", "session", "token"],
        },
        {
            "domain": "demand",
            "description": "Issue and demand mapping",
            "paths": ["src/demand/"],
            "keywords": ["demand", "issue", "requirement"],
        },
    ]

    def test_scoring_weights(self):
        unit = {
            "section_name": "Auth token refresh",
            "theme": "auth-session",
            "summary": "Add login session refresh token flow",
            "file_paths": ["src/auth/login.py"],
        }

        score = score_unit_for_domain(unit, self.DOMAINS[0])

        assert score == 13

    def test_repeated_hits_do_not_stack_per_signal_type(self):
        unit = {
            "section_name": "Auth auth auth",
            "theme": "auth auth auth",
            "summary": "auth auth login session token",
            "file_paths": ["src/auth/login.py", "src/auth/session.py"],
        }

        score = score_unit_for_domain(unit, self.DOMAINS[0])

        assert score == 13

    def test_minimum_score_gate(self):
        unit = {
            "section_name": "Minor cleanup",
            "theme": "maintenance",
            "summary": "Adjust token naming",
            "file_paths": [],
        }

        assert classify_unit_locally(unit, self.DOMAINS) is None

    def test_ambiguity_gate(self):
        unit = {
            "section_name": "Update",
            "theme": "auth issue",
            "summary": "Refine handling",
            "file_paths": [],
        }
        domains = [
            self.DOMAINS[0],
            {
                "domain": "issue-triage",
                "description": "Issue processing",
                "paths": [],
                "keywords": ["issue", "routing", "auth"],
            },
        ]

        assert classify_unit_locally(unit, domains) is None

    def test_disable_path_scoring_after_multi_domain_failure(self):
        unit = {
            "section_name": "Auth rollout",
            "theme": "maintenance",
            "summary": "Refactor helpers",
            "file_paths": ["src/auth/login.py"],
        }

        assert classify_unit_locally(unit, self.DOMAINS, allow_path_scoring=False) is None


class TestParseLlmDomains:
    """Tests for parse_llm_domains."""

    def test_valid_json(self):
        """T1: Valid JSON array of domains."""
        raw = json.dumps([
            {"domain": "core", "description": "Core module", "paths": ["src/"], "keywords": ["core"]},
            {"domain": "test", "description": "Tests", "paths": ["tests/"], "keywords": ["test"]},
        ])
        result = parse_llm_domains(raw)
        assert len(result) == 2
        assert result[0]["domain"] == "core"

    def test_with_code_fences(self):
        """Handles markdown code fences."""
        raw = '```json\n[{"domain": "x", "description": "y"}]\n```'
        result = parse_llm_domains(raw)
        assert len(result) == 1

    def test_invalid_json(self):
        """T5: Invalid JSON returns empty list."""
        assert parse_llm_domains("not json") == []

    def test_not_a_list(self):
        """Non-list JSON returns empty list."""
        assert parse_llm_domains('{"domain": "x"}') == []

    def test_missing_domain_key(self):
        """Items without 'domain' key are skipped."""
        raw = json.dumps([{"description": "no domain key"}, {"domain": "ok", "description": "has it"}])
        result = parse_llm_domains(raw)
        assert len(result) == 1
        assert result[0]["domain"] == "ok"

    def test_schema_validation(self):
        """T2: Output has required fields."""
        raw = json.dumps([{"domain": "x", "description": "y", "paths": ["a/"], "keywords": ["k"]}])
        result = parse_llm_domains(raw)
        assert "domain" in result[0]
        assert "description" in result[0]
        assert "paths" in result[0]
        assert "keywords" in result[0]


class TestFingerprint:
    """Tests for compute_fingerprint and fingerprint_matches."""

    def test_fingerprint_computation(self, tmp_path):
        """Fingerprint changes when file content changes."""
        f = tmp_path / "units.jsonl"
        f.write_text('{"a": 1}\n')
        fp1 = compute_fingerprint(f)

        f.write_text('{"a": 1}\n{"b": 2}\n')
        fp2 = compute_fingerprint(f)

        assert fp1["units_hash"] != fp2["units_hash"]

    def test_fingerprint_matches_true(self, tmp_path):
        """T3: Fingerprint matches when content unchanged."""
        f = tmp_path / "units.jsonl"
        f.write_text('{"a": 1}\n')
        fp = compute_fingerprint(f)
        data = {"_fingerprint": fp, "domains": []}
        assert fingerprint_matches(data, fp) is True

    def test_fingerprint_matches_false(self, tmp_path):
        """T4: Fingerprint doesn't match when content changed."""
        f = tmp_path / "units.jsonl"
        f.write_text('{"a": 1}\n')
        fp_old = compute_fingerprint(f)
        data = {"_fingerprint": fp_old, "domains": []}

        f.write_text('{"a": 1}\n{"b": 2}\n')
        fp_new = compute_fingerprint(f)
        assert fingerprint_matches(data, fp_new) is False

    def test_arch_file_included(self, tmp_path):
        """Architecture file hash is included when present."""
        units = tmp_path / "units.jsonl"
        units.write_text("{}\n")
        arch = tmp_path / "ARCH.md"
        arch.write_text("# Architecture\n")

        fp_with = compute_fingerprint(units, arch)
        fp_without = compute_fingerprint(units)

        assert fp_with["arch_hash"] is not None
        assert fp_without["arch_hash"] is None


# ---------------------------------------------------------------
# T14: parse_llm_classifications
# ---------------------------------------------------------------

class TestParseLlmClassifications:
    """Tests for parse_llm_classifications."""

    def test_valid_response(self):
        """T14 partial: Valid classification response."""
        raw = json.dumps([
            {"id": "0", "domain": "semantic"},
            {"id": "1", "domain": "commit"},
        ])
        result = parse_llm_classifications(raw)
        assert result == {"0": "semantic", "1": "commit"}

    def test_invalid_json(self):
        """LLM failure returns empty dict."""
        assert parse_llm_classifications("broken") == {}

    def test_with_code_fences(self):
        """Handles markdown fences."""
        raw = '```json\n[{"id": "0", "domain": "x"}]\n```'
        result = parse_llm_classifications(raw)
        assert result == {"0": "x"}


# ---------------------------------------------------------------
# build_units_summary
# ---------------------------------------------------------------

class TestBuildUnitsSummary:
    """Tests for build_units_summary."""

    def test_basic_summary(self):
        """Produces readable summary with theme and op distribution."""
        units = [
            {"theme": "auth", "op": "feature", "summary": "Add login"},
            {"theme": "auth", "op": "bugfix", "summary": "Fix token"},
            {"theme": "test", "op": "feature", "summary": "Add test"},
        ]
        result = build_units_summary(units)
        assert "Total units: 3" in result
        assert "auth: 2" in result
        assert "feature: 2" in result

    def test_empty_units(self):
        """Empty units list produces valid summary."""
        result = build_units_summary([])
        assert "Total units: 0" in result


class TestDomainNormalization:
    """Tests for discover-stage domain normalization helpers."""

    def test_singular_plural_merge_prefers_plural_tests(self):
        domains = [
            {
                "domain": "test",
                "description": "Single test utilities",
                "paths": ["tests/unit/"],
                "keywords": ["pytest", "fixture"],
            },
            {
                "domain": "tests",
                "description": "Test infrastructure",
                "paths": ["tests/e2e/"],
                "keywords": ["pytest", "integration"],
            },
        ]

        assert normalize_domains(domains) == [
            {
                "domain": "tests",
                "description": "Test infrastructure",
                "paths": ["tests/e2e/", "tests/unit/"],
                "keywords": ["fixture", "integration", "pytest"],
            }
        ]

    def test_exact_duplicate_merge(self):
        domains = [
            {
                "domain": "auth",
                "description": "Authentication",
                "paths": ["src/auth/"],
                "keywords": ["login", "token"],
            },
            {
                "domain": "auth",
                "description": "Authentication and sessions",
                "paths": ["src/auth/", "src/session/"],
                "keywords": ["login", "token", "session"],
            },
        ]

        assert normalize_domains(domains) == [
            {
                "domain": "auth",
                "description": "Authentication and sessions",
                "paths": ["src/auth/", "src/session/"],
                "keywords": ["login", "session", "token"],
            }
        ]

    def test_keyword_overlap_merge_threshold(self):
        left = {
            "domain": "auth",
            "description": "Authentication flows",
            "paths": ["src/auth/"],
            "keywords": ["auth", "login", "token"],
        }
        right = {
            "domain": "authentication",
            "description": "Authentication and sessions",
            "paths": ["src/session/"],
            "keywords": ["auth", "login", "session"],
        }
        other = {
            "domain": "billing",
            "description": "Billing",
            "paths": ["src/billing/"],
            "keywords": ["invoice", "payment", "refund"],
        }

        assert should_merge_domains(left, right) is True
        assert should_merge_domains(left, other) is False

    def test_path_overlap_merge_threshold(self):
        left = {
            "domain": "demand",
            "description": "Demand cards",
            "paths": ["src/demand/", "tests/demand/"],
            "keywords": ["demand", "issue"],
        }
        right = {
            "domain": "demands",
            "description": "Demand processing",
            "paths": ["src/demand/", "tests/demand/", "docs/demand/"],
            "keywords": ["requirements"],
        }
        other = {
            "domain": "commit",
            "description": "Commit pipeline",
            "paths": ["src/commit_semantic/"],
            "keywords": ["commit"],
        }

        assert should_merge_domains(left, right) is True
        assert should_merge_domains(left, other) is False

    def test_noise_filtering(self):
        domains = [
            {"domain": "misc", "description": "noise", "paths": [], "keywords": ["misc"]},
            {"domain": "other", "description": "noise", "paths": [], "keywords": ["other"]},
            {"domain": "general", "description": "noise", "paths": [], "keywords": ["general"]},
            {"domain": "auth", "description": "Authentication", "paths": ["src/auth/"], "keywords": ["login"]},
        ]

        assert normalize_domains(domains) == [
            {
                "domain": "auth",
                "description": "Authentication",
                "paths": ["src/auth/"],
                "keywords": ["login"],
            }
        ]

    def test_winner_selection_priority(self):
        singular = {
            "domain": "test",
            "description": "Short description",
            "paths": ["tests/unit/"],
            "keywords": ["pytest"],
        }
        plural = {
            "domain": "tests",
            "description": "Longer and more specific test infrastructure domain",
            "paths": ["tests/unit/", "tests/e2e/"],
            "keywords": ["pytest", "fixture", "integration"],
        }

        assert choose_domain_winner(singular, plural)["domain"] == "tests"


# ---------------------------------------------------------------
# T26: state compatibility
# ---------------------------------------------------------------

class TestStateCompat:
    """Tests for state compatibility detection."""

    def _make_runner_and_state(self, completed: list[str]):
        """Create a CommitSemanticRunner and HarnessState with given completed stages."""
        from src.harness_state import HarnessState
        sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "commit-semantic"))
        # Import directly from the module file
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "commit_semantic_run",
            Path(__file__).parent.parent / "skills" / "commit-semantic" / "run.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="test",
            metadata={
                "completed_stages": completed,
                "artifacts_written": [],
                "status": "ok",
            },
        )
        return runner, state

    def test_old_4stage_detected(self):
        """T26: Old 4-stage completed_stages triggers reset."""
        runner, state = self._make_runner_and_state(
            completed=["ingest", "aggregate", "distill", "export"]
        )
        new_state = runner._check_state_compat(state)
        assert new_state.metadata.get("completed_stages") == []

    def test_new_5stage_preserved(self):
        """New 5-stage state is preserved."""
        runner, state = self._make_runner_and_state(
            completed=["discover", "ingest"]
        )
        new_state = runner._check_state_compat(state)
        assert new_state.metadata.get("completed_stages") == ["discover", "ingest"]

    def test_empty_state_preserved(self):
        """Fresh state is preserved."""
        runner, state = self._make_runner_and_state(completed=[])
        new_state = runner._check_state_compat(state)
        assert new_state.metadata.get("completed_stages") == []

