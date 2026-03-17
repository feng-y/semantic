"""Test that reset clears the current FACT snapshot to prevent version_skew."""

from pathlib import Path
import tempfile
import json

from src import dispatcher


def test_reset_clears_fact_snapshot():
    """Regression test: reset must clear docs/fact/semantic_snapshot.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Setup: create FACT snapshot
        snapshot_path = root / "docs" / "fact" / "semantic_snapshot.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps({"test": "data"}))

        assert snapshot_path.exists(), "Setup failed: snapshot should exist"

        # Execute: reset
        result = dispatcher.dispatch("reset", root)

        # Verify: snapshot removed
        assert result["status"] == "ok"
        assert not snapshot_path.exists(), "Reset should remove docs/fact/semantic_snapshot.json"
        assert str(snapshot_path.relative_to(root)) in result["removed"]


def test_reset_clears_legacy_snapshot():
    """Reset should also clear legacy docs/semantic/semantic_snapshot.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Setup: create legacy snapshot
        legacy_path = root / "docs" / "semantic" / "semantic_snapshot.json"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(json.dumps({"legacy": "data"}))

        assert legacy_path.exists(), "Setup failed: legacy snapshot should exist"

        # Execute: reset
        result = dispatcher.dispatch("reset", root)

        # Verify: legacy snapshot removed
        assert result["status"] == "ok"
        assert not legacy_path.exists(), "Reset should remove legacy snapshot"
        assert str(legacy_path.relative_to(root)) in result["removed"]


def test_reset_clears_both_snapshots():
    """Reset should clear both current and legacy snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Setup: create both snapshots
        fact_snap = root / "docs" / "fact" / "semantic_snapshot.json"
        fact_snap.parent.mkdir(parents=True, exist_ok=True)
        fact_snap.write_text(json.dumps({"current": "data"}))

        legacy_snap = root / "docs" / "semantic" / "semantic_snapshot.json"
        legacy_snap.parent.mkdir(parents=True, exist_ok=True)
        legacy_snap.write_text(json.dumps({"legacy": "data"}))

        # Execute: reset
        result = dispatcher.dispatch("reset", root)

        # Verify: both removed
        assert result["status"] == "ok"
        assert not fact_snap.exists()
        assert not legacy_snap.exists()
        assert len(result["removed"]) >= 2
