"""
Tests for semantic recommendation generation
"""

import pytest
from pathlib import Path
import yaml
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.score_recommend import (
    load_candidates,
    evaluate_semantic_validity,
    compute_scores,
    determine_recommendation,
    generate_reasons,
    check_evidence_needs,
    generate_recommendation_item,
    generate_stable_id,
    main
)

def test_load_candidates():
    """Test loading candidates.yaml"""
    candidates_path = Path("docs/semantic-foundation/semantic/candidates.yaml")
    if not candidates_path.exists():
        pytest.skip("candidates.yaml not found")

    candidates = load_candidates(candidates_path)
    if candidates:
        assert isinstance(candidates, dict)
        assert 'domains' in candidates
        assert 'concepts' in candidates
        assert 'rules' in candidates
        assert 'demand_models' in candidates

def test_generate_stable_id():
    """Test stable ID generation"""
    id1 = generate_stable_id("test_name", "domain")
    id2 = generate_stable_id("test_name", "domain")

    # Same input should produce same ID
    assert id1 == id2
    assert id1.startswith("rec_domain_")

    # Different names should produce different IDs
    id3 = generate_stable_id("different_name", "domain")
    assert id1 != id3

def test_evaluate_semantic_validity_high_confidence():
    """Test validity evaluation for high confidence candidate"""
    candidate = {
        'id': 'test_id',
        'name': 'Test',
        'summary': 'Test summary',
        'confidence': 'high',
        'evidence_refs': ['evidence1']
    }

    validity, reason = evaluate_semantic_validity(candidate, 'domain')
    assert validity == 'pass'
    assert 'high confidence' in reason.lower()

def test_evaluate_semantic_validity_medium_with_evidence():
    """Test validity evaluation for medium confidence with evidence"""
    candidate = {
        'id': 'test_id',
        'name': 'Test',
        'summary': 'Test summary',
        'confidence': 'medium',
        'evidence_refs': ['evidence1']
    }

    validity, reason = evaluate_semantic_validity(candidate, 'domain')
    assert validity == 'pass'
    assert 'medium confidence' in reason.lower()

def test_evaluate_semantic_validity_medium_without_evidence():
    """Test validity evaluation for medium confidence without evidence"""
    candidate = {
        'id': 'test_id',
        'name': 'Test',
        'summary': 'Test summary',
        'confidence': 'medium',
        'evidence_refs': []
    }

    validity, reason = evaluate_semantic_validity(candidate, 'domain')
    assert validity == 'fail'
    assert 'lacks evidence' in reason.lower()

def test_evaluate_semantic_validity_low_confidence():
    """Test validity evaluation for low confidence"""
    candidate = {
        'id': 'test_id',
        'name': 'Test',
        'summary': 'Test summary',
        'confidence': 'low',
        'evidence_refs': ['evidence1']
    }

    validity, reason = evaluate_semantic_validity(candidate, 'domain')
    assert validity == 'fail'
    assert 'low confidence' in reason.lower()

def test_evaluate_semantic_validity_missing_fields():
    """Test validity evaluation with missing required fields"""
    candidate = {
        'id': 'test_id',
        'confidence': 'high'
    }

    validity, reason = evaluate_semantic_validity(candidate, 'domain')
    assert validity == 'fail'
    assert 'missing required fields' in reason.lower()

def test_compute_scores_high_confidence():
    """Test score computation for high confidence candidate"""
    candidate = {
        'confidence': 'high',
        'evidence_refs': ['ev1', 'ev2'],
        'source_signal_ids': ['sig1']
    }

    business_score, value_score = compute_scores(candidate, 'domain')
    assert 1.0 <= business_score <= 10.0
    assert 1.0 <= value_score <= 10.0
    assert business_score >= 8.0  # High confidence base

def test_compute_scores_medium_confidence():
    """Test score computation for medium confidence candidate"""
    candidate = {
        'confidence': 'medium',
        'evidence_refs': ['ev1'],
        'source_signal_ids': ['sig1']
    }

    business_score, value_score = compute_scores(candidate, 'domain')
    assert 1.0 <= business_score <= 10.0
    assert 1.0 <= value_score <= 10.0
    assert business_score >= 6.0  # Medium confidence base

def test_determine_recommendation_fail_validity():
    """Test recommendation for failed validity"""
    rec = determine_recommendation('fail', 8.0, 8.0, {}, 'domain')

    assert rec['status'] == 'not_recommend'
    assert rec['action'] == 'drop'
    assert rec['target_layer'] == 'candidate_pool'
    assert rec['target_asset_type'] == 'none'

def test_determine_recommendation_high_priority():
    """Test recommendation for high priority (>= 7.0)"""
    rec = determine_recommendation('pass', 8.0, 7.5, {}, 'domain')

    assert rec['status'] == 'recommend'
    assert rec['action'] == 'keep'
    assert rec['target_layer'] == 'final_asset'
    assert rec['target_asset_type'] == 'domain_map'

def test_determine_recommendation_medium_priority():
    """Test recommendation for medium priority (5.0-7.0)"""
    rec = determine_recommendation('pass', 6.0, 5.5, {}, 'concept')

    assert rec['status'] == 'recommend'
    assert rec['action'] == 'verify_first'
    assert rec['target_layer'] == 'candidate_pool'
    assert rec['target_asset_type'] == 'concept_map'

def test_determine_recommendation_low_priority():
    """Test recommendation for low priority (< 5.0)"""
    rec = determine_recommendation('pass', 4.0, 3.5, {}, 'rule')

    assert rec['status'] == 'defer'
    assert rec['action'] == 'backlog'
    assert rec['target_layer'] == 'candidate_pool'
    assert rec['target_asset_type'] == 'none'

def test_generate_reasons_pass():
    """Test reason generation for passed validity"""
    candidate = {
        'confidence': 'high',
        'evidence_refs': ['ev1', 'ev2']
    }
    rec = {'status': 'recommend', 'action': 'keep'}

    recommended, not_recommended = generate_reasons('pass', 8.0, 7.5, candidate, rec)

    assert len(recommended) > 0
    assert 'Semantic validity passed' in recommended
    assert len(not_recommended) == 0

def test_generate_reasons_fail():
    """Test reason generation for failed validity"""
    candidate = {
        'confidence': 'low',
        'evidence_refs': []
    }
    rec = {'status': 'not_recommend', 'action': 'drop'}

    recommended, not_recommended = generate_reasons('fail', 3.0, 3.0, candidate, rec)

    assert len(recommended) == 0
    assert len(not_recommended) > 0
    assert 'Semantic validity failed' in not_recommended

def test_check_evidence_needs_medium_confidence():
    """Test evidence check for medium confidence"""
    candidate = {
        'confidence': 'medium',
        'evidence_refs': ['ev1']
    }

    needs_check, gap = check_evidence_needs(candidate, 'pass')
    assert isinstance(needs_check, bool)
    if needs_check:
        assert gap is not None

def test_generate_recommendation_complete():
    """Test complete recommendation generation"""
    candidate = {
        'id': 'domain_abc123',
        'name': 'Test Domain',
        'summary': 'Test summary',
        'confidence': 'high',
        'evidence_refs': ['evidence1'],
        'source_signal_ids': ['signal1'],
        'boundary': {'modules': ['mod1']}
    }

    rec = generate_recommendation_item(candidate, 'domain')

    # Check required fields
    assert 'id' in rec
    assert 'name' in rec
    assert 'candidate_id' in rec
    assert 'semantic_validity' in rec
    assert 'validity_reason' in rec
    assert 'business_score' in rec
    assert 'value_score' in rec
    assert 'priority' in rec
    assert 'recommendation' in rec
    assert 'recommended_reasons' in rec
    assert 'not_recommended_reasons' in rec
    assert 'needs_evidence_check' in rec
    assert 'source_candidate_ids' in rec
    assert 'evidence_refs' in rec

    # Check priority rule
    assert rec['priority'] == max(rec['business_score'], rec['value_score'])

    # Check recommendation structure
    assert 'status' in rec['recommendation']
    assert 'action' in rec['recommendation']
    assert 'target_layer' in rec['recommendation']
    assert 'target_asset_type' in rec['recommendation']

def test_recommendations_yaml_structure(tmp_path):
    """Test recommendations.yaml structure validity"""
    candidates_path = Path("docs/semantic-foundation/semantic/candidates.yaml")
    if not candidates_path.exists():
        pytest.skip("candidates.yaml not found")

    output_file = tmp_path / "recommendations.yaml"
    md_file = tmp_path / "recommendations.md"

    # Run recommendation generation
    import sys
    sys.argv = [
        'score_recommend.py',
        '--candidates', str(candidates_path),
        '--output', str(output_file),
        '--render-md', str(md_file)
    ]

    try:
        main()
    except SystemExit:
        pass

    # Verify output
    assert output_file.exists()

    with open(output_file, 'r') as f:
        data = yaml.safe_load(f)

    # Check structure
    assert 'domains' in data
    assert 'concepts' in data
    assert 'rules' in data
    assert 'demand_models' in data
    assert 'metadata' in data

    # Check metadata
    assert 'generated_at' in data['metadata']
    assert 'candidates_source' in data['metadata']
    assert 'recommendation_count' in data['metadata']

    # Check recommendation groups are lists
    assert isinstance(data['domains'], list)
    assert isinstance(data['concepts'], list)
    assert isinstance(data['rules'], list)
    assert isinstance(data['demand_models'], list)

def test_recommendations_markdown_generation(tmp_path):
    """Test recommendations.md generation"""
    candidates_path = Path("docs/semantic-foundation/semantic/candidates.yaml")
    if not candidates_path.exists():
        pytest.skip("candidates.yaml not found")

    output_file = tmp_path / "recommendations.yaml"
    md_file = tmp_path / "recommendations.md"

    import sys
    sys.argv = [
        'score_recommend.py',
        '--candidates', str(candidates_path),
        '--output', str(output_file),
        '--render-md', str(md_file)
    ]

    try:
        main()
    except SystemExit:
        pass

    # Verify markdown output
    assert md_file.exists()

    content = md_file.read_text()
    assert '# Semantic Recommendations' in content
    assert 'Domain' in content
    assert 'Concept' in content
    assert 'Rule' in content
    assert 'Demand Model' in content

def test_deterministic_recommendation():
    """Test that same inputs produce same recommendations"""
    candidate = {
        'id': 'test_id',
        'name': 'Test',
        'summary': 'Test summary',
        'confidence': 'high',
        'evidence_refs': ['ev1'],
        'source_signal_ids': ['sig1']
    }

    rec1 = generate_recommendation_item(candidate, 'domain')
    rec2 = generate_recommendation_item(candidate, 'domain')

    assert rec1['id'] == rec2['id']
    assert rec1['business_score'] == rec2['business_score']
    assert rec1['value_score'] == rec2['value_score']
    assert rec1['priority'] == rec2['priority']
    assert rec1['recommendation']['status'] == rec2['recommendation']['status']

def test_priority_computation():
    """Test that priority is always max(business_score, value_score)"""
    candidates_path = Path("docs/semantic-foundation/semantic/candidates.yaml")
    if not candidates_path.exists():
        pytest.skip("candidates.yaml not found")

    candidates = load_candidates(candidates_path)
    if not candidates:
        pytest.skip("Could not load candidates")

    # Test all candidate types
    for candidate_type in ['domains', 'concepts', 'rules', 'demand_models']:
        for candidate in candidates.get(candidate_type, []):
            rec = generate_recommendation_item(candidate, candidate_type.rstrip('s'))
            expected_priority = max(rec['business_score'], rec['value_score'])
            assert rec['priority'] == expected_priority, \
                f"Priority mismatch for {candidate['name']}: {rec['priority']} != {expected_priority}"

def test_traceability_preservation():
    """Test that candidate traceability is preserved"""
    candidate = {
        'id': 'domain_abc123',
        'name': 'Test Domain',
        'summary': 'Test summary',
        'confidence': 'high',
        'evidence_refs': ['evidence1', 'evidence2'],
        'source_signal_ids': ['signal1']
    }

    rec = generate_recommendation_item(candidate, 'domain')

    assert rec['candidate_id'] == candidate['id']
    assert candidate['id'] in rec['source_candidate_ids']
    assert all(ev in rec['evidence_refs'] for ev in candidate['evidence_refs'])

def test_valid_status_values():
    """Test that only valid status values are used"""
    valid_statuses = {'recommend', 'not_recommend', 'defer'}

    candidates_path = Path("docs/semantic-foundation/semantic/candidates.yaml")
    if not candidates_path.exists():
        pytest.skip("candidates.yaml not found")

    candidates = load_candidates(candidates_path)
    if not candidates:
        pytest.skip("Could not load candidates")

    for candidate_type in ['domains', 'concepts', 'rules', 'demand_models']:
        for candidate in candidates.get(candidate_type, []):
            rec = generate_recommendation_item(candidate, candidate_type.rstrip('s'))
            assert rec['recommendation']['status'] in valid_statuses

def test_valid_action_values():
    """Test that only valid action values are used"""
    valid_actions = {'keep', 'merge', 'drop', 'backlog', 'verify_first'}

    candidates_path = Path("docs/semantic-foundation/semantic/candidates.yaml")
    if not candidates_path.exists():
        pytest.skip("candidates.yaml not found")

    candidates = load_candidates(candidates_path)
    if not candidates:
        pytest.skip("Could not load candidates")

    for candidate_type in ['domains', 'concepts', 'rules', 'demand_models']:
        for candidate in candidates.get(candidate_type, []):
            rec = generate_recommendation_item(candidate, candidate_type.rstrip('s'))
            assert rec['recommendation']['action'] in valid_actions
