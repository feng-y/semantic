"""
Tests for semantic review decision generation
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.apply_review import (
    convert_to_review_decision,
    generate_review_decisions,
    generate_stable_id,
    load_recommendations,
    main,
)


def test_load_recommendations():
    """Test loading recommendations.yaml"""
    recs_path = Path("docs/fact/recommendations.yaml")
    if not recs_path.exists():
        pytest.skip("recommendations.yaml not found")

    recs = load_recommendations(recs_path)
    if recs:
        assert isinstance(recs, dict)
        assert 'domains' in recs
        assert 'concepts' in recs
        assert 'rules' in recs
        assert 'demand_models' in recs

def test_generate_stable_id():
    """Test stable ID generation"""
    id1 = generate_stable_id("test_name", "domain")
    id2 = generate_stable_id("test_name", "domain")

    assert id1 == id2
    assert id1.startswith("review_domain_")

    id3 = generate_stable_id("different_name", "domain")
    assert id1 != id3

def test_convert_to_review_decision_keep():
    """Test converting recommendation with keep action"""
    rec = {
        'id': 'rec_domain_abc123',
        'name': 'Test Domain',
        'candidate_id': 'domain_abc123',
        'recommendation': {
            'status': 'recommend',
            'action': 'keep'
        },
        'evidence_refs': ['evidence1']
    }

    decision = convert_to_review_decision(rec, 'domain')

    assert decision['id'].startswith('review_domain_')
    assert decision['name'] == 'Test Domain'
    assert decision['final_action'] == 'keep'
    assert 'final_reason' in decision
    assert decision['source_recommendation_id'] == 'rec_domain_abc123'
    assert decision['source_candidate_id'] == 'domain_abc123'
    assert decision['evidence_refs'] == ['evidence1']

def test_convert_to_review_decision_verify_first():
    """Test converting recommendation with verify_first action"""
    rec = {
        'id': 'rec_concept_def456',
        'name': 'Test Concept',
        'candidate_id': 'concept_def456',
        'recommendation': {
            'status': 'recommend',
            'action': 'verify_first'
        },
        'evidence_refs': []
    }

    decision = convert_to_review_decision(rec, 'concept')

    assert decision['final_action'] == 'verify_first'
    assert 'verification' in decision['final_reason'].lower() or 'pending' in decision['final_reason'].lower()

def test_convert_to_review_decision_drop():
    """Test converting recommendation with drop action"""
    rec = {
        'id': 'rec_rule_ghi789',
        'name': 'Test Rule',
        'candidate_id': 'rule_ghi789',
        'recommendation': {
            'status': 'not_recommend',
            'action': 'drop'
        },
        'evidence_refs': []
    }

    decision = convert_to_review_decision(rec, 'rule')

    assert decision['final_action'] == 'drop'

def test_generate_review_decisions():
    """Test generating review decisions for all groups"""
    recs = {
        'domains': [
            {
                'id': 'rec_domain_1',
                'name': 'Domain 1',
                'candidate_id': 'domain_1',
                'recommendation': {'status': 'recommend', 'action': 'keep'},
                'evidence_refs': []
            }
        ],
        'concepts': [],
        'rules': [],
        'demand_models': []
    }

    decisions = generate_review_decisions(recs)

    assert 'domains' in decisions
    assert 'concepts' in decisions
    assert 'rules' in decisions
    assert 'demand_models' in decisions
    assert len(decisions['domains']) == 1
    assert decisions['domains'][0]['name'] == 'Domain 1'

def test_review_decisions_yaml_structure(tmp_path):
    """Test review-decisions.yaml structure validity"""
    recs_path = Path("docs/fact/recommendations.yaml")
    if not recs_path.exists():
        pytest.skip("recommendations.yaml not found")

    output_decisions = tmp_path / "review-decisions.yaml"
    output_checks = tmp_path / "evidence-checks.yaml"
    md_file = tmp_path / "review-note.md"

    sys.argv = [
        'apply_review.py',
        '--recommendations', str(recs_path),
        '--output-decisions', str(output_decisions),
        '--output-checks', str(output_checks),
        '--render-md', str(md_file)
    ]

    try:
        main()
    except SystemExit:
        pass

    assert output_decisions.exists()

    with open(output_decisions) as f:
        data = yaml.safe_load(f)

    assert 'domains' in data
    assert 'concepts' in data
    assert 'rules' in data
    assert 'demand_models' in data
    assert 'metadata' in data
    assert 'generated_at' in data['metadata']
    assert 'decision_count' in data['metadata']

def test_allowed_final_actions():
    """Test that only allowed final actions are used"""
    allowed_actions = {'keep', 'merge', 'drop', 'backlog', 'verify_first'}

    recs_path = Path("docs/fact/recommendations.yaml")
    if not recs_path.exists():
        pytest.skip("recommendations.yaml not found")

    recs = load_recommendations(recs_path)
    if not recs:
        pytest.skip("Could not load recommendations")

    decisions = generate_review_decisions(recs)

    for group in ['domains', 'concepts', 'rules', 'demand_models']:
        for decision in decisions.get(group, []):
            assert decision['final_action'] in allowed_actions

def test_traceability_preservation():
    """Test that recommendation traceability is preserved"""
    rec = {
        'id': 'rec_domain_abc123',
        'name': 'Test Domain',
        'candidate_id': 'domain_abc123',
        'recommendation': {'status': 'recommend', 'action': 'keep'},
        'evidence_refs': ['ev1', 'ev2']
    }

    decision = convert_to_review_decision(rec, 'domain')

    assert decision['source_recommendation_id'] == rec['id']
    assert decision['source_candidate_id'] == rec['candidate_id']
    assert decision['evidence_refs'] == rec['evidence_refs']

def test_merge_target_preservation():
    """Test that merge_target is preserved when present"""
    rec = {
        'id': 'rec_concept_merge',
        'name': 'Test Concept',
        'candidate_id': 'concept_merge',
        'recommendation': {'status': 'recommend', 'action': 'merge'},
        'merge_target': 'concept_target_123',
        'evidence_refs': []
    }

    decision = convert_to_review_decision(rec, 'concept')

    assert decision['final_action'] == 'merge'
    assert decision['merge_target'] == 'concept_target_123'
