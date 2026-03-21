"""
Tests for semantic evidence check generation
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.evidence_check import (
    create_evidence_check,
    generate_check_id,
    generate_evidence_checks,
)


def test_generate_check_id():
    """Test stable check ID generation"""
    id1 = generate_check_id("rec_domain_abc123")
    id2 = generate_check_id("rec_domain_abc123")

    assert id1 == id2
    assert id1.startswith("check_")

    id3 = generate_check_id("rec_domain_different")
    assert id1 != id3

def test_create_evidence_check():
    """Test creating evidence check from recommendation"""
    rec = {
        'id': 'rec_domain_abc123',
        'name': 'Test Domain',
        'candidate_id': 'domain_abc123',
        'evidence_gap': 'Medium confidence with limited evidence',
        'needs_evidence_check': True
    }

    check = create_evidence_check(rec, 'domain')

    assert check['id'].startswith('check_')
    assert check['target_id'] == 'rec_domain_abc123'
    assert check['target_type'] == 'domain'
    assert check['target_name'] == 'Test Domain'
    assert 'reason' in check
    assert 'required_evidence' in check
    assert isinstance(check['required_evidence'], list)
    assert check['status'] == 'pending'
    assert check['source_recommendation_id'] == 'rec_domain_abc123'
    assert check['source_candidate_id'] == 'domain_abc123'

def test_generate_evidence_checks_needs_check():
    """Test generating checks for recommendations with needs_evidence_check=true"""
    recs = {
        'domains': [
            {
                'id': 'rec_domain_1',
                'name': 'Domain 1',
                'candidate_id': 'domain_1',
                'needs_evidence_check': True,
                'evidence_gap': 'Needs verification',
                'recommendation': {'action': 'verify_first'}
            }
        ],
        'concepts': [],
        'rules': [],
        'demand_models': []
    }

    checks = generate_evidence_checks(recs)

    assert len(checks) == 1
    assert checks[0]['target_type'] == 'domain'
    assert checks[0]['target_name'] == 'Domain 1'

def test_generate_evidence_checks_verify_first():
    """Test generating checks for recommendations with action=verify_first"""
    recs = {
        'domains': [],
        'concepts': [
            {
                'id': 'rec_concept_1',
                'name': 'Concept 1',
                'candidate_id': 'concept_1',
                'needs_evidence_check': False,
                'recommendation': {'action': 'verify_first'}
            }
        ],
        'rules': [],
        'demand_models': []
    }

    checks = generate_evidence_checks(recs)

    assert len(checks) == 1
    assert checks[0]['target_type'] == 'concept'

def test_generate_evidence_checks_no_verification_needed():
    """Test that no checks are generated for keep/drop actions"""
    recs = {
        'domains': [
            {
                'id': 'rec_domain_1',
                'name': 'Domain 1',
                'candidate_id': 'domain_1',
                'needs_evidence_check': False,
                'recommendation': {'action': 'keep'}
            }
        ],
        'concepts': [],
        'rules': [],
        'demand_models': []
    }

    checks = generate_evidence_checks(recs)

    assert len(checks) == 0

def test_evidence_checks_yaml_structure(tmp_path):
    """Test evidence-checks.yaml structure validity"""
    from semantic.apply_review import main

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

    assert output_checks.exists()

    with open(output_checks) as f:
        data = yaml.safe_load(f)

    assert 'evidence_checks' in data
    assert 'metadata' in data
    assert isinstance(data['evidence_checks'], list)

def test_check_traceability():
    """Test that evidence checks preserve traceability"""
    rec = {
        'id': 'rec_domain_abc123',
        'name': 'Test Domain',
        'candidate_id': 'domain_abc123',
        'needs_evidence_check': True,
        'evidence_gap': 'Test gap'
    }

    check = create_evidence_check(rec, 'domain')

    assert check['source_recommendation_id'] == rec['id']
    assert check['source_candidate_id'] == rec['candidate_id']
    assert check['target_id'] == rec['id']

def test_deterministic_check_generation():
    """Test that same inputs produce same checks"""
    rec = {
        'id': 'rec_test_123',
        'name': 'Test',
        'candidate_id': 'test_123',
        'needs_evidence_check': True
    }

    check1 = create_evidence_check(rec, 'domain')
    check2 = create_evidence_check(rec, 'domain')

    assert check1['id'] == check2['id']
    assert check1['target_id'] == check2['target_id']
