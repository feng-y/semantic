"""
Tests for FeedbackCollector
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.feedback import FeedbackCollector, FeedbackEntry


def test_record_creates_file(tmp_path):
    log = tmp_path / "feedback.jsonl"
    collector = FeedbackCollector(log)
    collector.record('review', 'domain', 'id1', 'Domain A', 'accepted', 'high')
    assert log.exists()


def test_record_appends_entries(tmp_path):
    log = tmp_path / "feedback.jsonl"
    collector = FeedbackCollector(log)
    collector.record('review', 'domain', 'id1', 'Domain A', 'accepted', 'high')
    collector.record('review', 'concept', 'id2', 'Concept B', 'rejected', 'low')
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first['item_name'] == 'Domain A'
    second = json.loads(lines[1])
    assert second['item_name'] == 'Concept B'


def test_load_all_returns_entries(tmp_path):
    log = tmp_path / "feedback.jsonl"
    collector = FeedbackCollector(log)
    collector.record('review', 'rule', 'id3', 'Rule C', 'deferred', 'medium', reason='needs more data')
    entries = collector.load_all()
    assert len(entries) == 1
    assert isinstance(entries[0], FeedbackEntry)
    assert entries[0].item_name == 'Rule C'
    assert entries[0].reason == 'needs more data'


def test_load_empty_returns_empty(tmp_path):
    log = tmp_path / "nonexistent.jsonl"
    collector = FeedbackCollector(log)
    assert collector.load_all() == []


def test_summary_acceptance_rate(tmp_path):
    log = tmp_path / "feedback.jsonl"
    collector = FeedbackCollector(log)
    collector.record('review', 'domain', 'id1', 'A', 'accepted', 'high')
    collector.record('review', 'domain', 'id2', 'B', 'accepted', 'high')
    collector.record('review', 'domain', 'id3', 'C', 'rejected', 'low')
    summary = collector.summary()
    assert summary['total'] == 3
    assert summary['accepted'] == 2
    assert summary['rejected'] == 1
    assert abs(summary['acceptance_rate'] - 66.666) < 0.1


def test_summary_by_confidence(tmp_path):
    log = tmp_path / "feedback.jsonl"
    collector = FeedbackCollector(log)
    collector.record('review', 'domain', 'id1', 'A', 'accepted', 'high')
    collector.record('review', 'domain', 'id2', 'B', 'rejected', 'high')
    collector.record('review', 'domain', 'id3', 'C', 'accepted', 'low')
    summary = collector.summary()
    assert summary['by_confidence']['high']['accepted'] == 1
    assert summary['by_confidence']['high']['rejected'] == 1
    assert summary['by_confidence']['low']['accepted'] == 1


def test_corrupt_line_skipped(tmp_path):
    log = tmp_path / "feedback.jsonl"
    collector = FeedbackCollector(log)
    collector.record('review', 'domain', 'id1', 'A', 'accepted', 'high')
    # Append a corrupt line
    with open(log, 'a') as f:
        f.write('not valid json\n')
    collector.record('review', 'domain', 'id2', 'B', 'rejected', 'low')
    entries = collector.load_all()
    assert len(entries) == 2
    assert entries[0].item_name == 'A'
    assert entries[1].item_name == 'B'
