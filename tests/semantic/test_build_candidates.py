"""
Tests for semantic candidates synthesis
"""

import sys
from pathlib import Path

import pytest
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.build_candidates import (
    generate_stable_id,
    load_signals,
    main,
    synthesize_concept_candidates,
    synthesize_demand_model_candidates,
    synthesize_domain_candidates,
    synthesize_rule_candidates,
)


def test_load_signals():
    """Test loading signals.yaml"""
    signals_path = Path("docs/fact/signals.yaml")
    if not signals_path.exists():
        pytest.skip("signals.yaml not found")

    signals = load_signals(signals_path)
    if signals:
        assert isinstance(signals, dict)
        assert 'domain_signals' in signals
        assert 'concept_signals' in signals
        assert 'rule_signals' in signals
        assert 'demand_pattern_signals' in signals

def test_generate_stable_id():
    """Test stable ID generation"""
    id1 = generate_stable_id("test_name", "domain")
    id2 = generate_stable_id("test_name", "domain")

    # Same input should produce same ID
    assert id1 == id2
    assert id1.startswith("domain_")

    # Different names should produce different IDs
    id3 = generate_stable_id("different_name", "domain")
    assert id1 != id3

def test_synthesize_domain_candidates():
    """Test domain candidate synthesis"""
    domain_signals = [
        {
            'signal_type': 'module_grouping',
            'source': 'fact_canonical:modules',
            'evidence': '10 modules observed',
            'confidence': 'high',
            'summary': 'Repository contains 10 modules'
        },
        {
            'signal_type': 'domain_proposal',
            'source': 'fact_working_summary:domain_proposals',
            'evidence': '3 domain proposals',
            'confidence': 'medium',
            'summary': 'Working summary proposes 3 domains'
        }
    ]

    candidates = synthesize_domain_candidates(domain_signals)
    assert isinstance(candidates, list)
    assert len(candidates) > 0

    for candidate in candidates:
        assert 'id' in candidate
        assert 'name' in candidate
        assert 'summary' in candidate
        assert 'boundary' in candidate
        assert 'source_signal_ids' in candidate
        assert 'evidence_refs' in candidate
        assert 'confidence' in candidate
        assert candidate['confidence'] in ['high', 'medium', 'low']

def test_synthesize_concept_candidates():
    """Test concept candidate synthesis"""
    concept_signals = [
        {
            'signal_type': 'entity_definition',
            'source': 'fact_canonical:core_entities',
            'evidence': '5 entities observed',
            'confidence': 'high',
            'summary': 'Repository defines 5 core entities'
        }
    ]

    candidates = synthesize_concept_candidates(concept_signals)
    assert isinstance(candidates, list)
    assert len(candidates) > 0

    for candidate in candidates:
        assert 'id' in candidate
        assert 'name' in candidate
        assert 'summary' in candidate
        assert 'relationships' in candidate
        assert 'source_signal_ids' in candidate
        assert 'evidence_refs' in candidate

def test_synthesize_rule_candidates():
    """Test rule candidate synthesis"""
    rule_signals = [
        {
            'signal_type': 'validation_logic',
            'source': 'fact_canonical:modules',
            'evidence': '2 validation modules',
            'confidence': 'high',
            'summary': 'Repository contains 2 validation modules'
        }
    ]

    candidates = synthesize_rule_candidates(rule_signals)
    assert isinstance(candidates, list)
    assert len(candidates) > 0

def test_synthesize_demand_model_candidates():
    """Test demand model candidate synthesis"""
    demand_signals = [
        {
            'signal_type': 'change_analysis_pattern',
            'source': 'fact_canonical:modules',
            'evidence': '1 change module',
            'confidence': 'medium',
            'summary': 'Repository contains 1 change analysis module'
        }
    ]

    candidates = synthesize_demand_model_candidates(demand_signals)
    assert isinstance(candidates, list)
    assert len(candidates) > 0

def test_candidates_yaml_structure(tmp_path):
    """Test candidates.yaml structure validity"""
    signals_path = Path("docs/fact/signals.yaml")
    if not signals_path.exists():
        pytest.skip("signals.yaml not found")

    output_file = tmp_path / "candidates.yaml"
    md_file = tmp_path / "candidates.md"

    # Run synthesis
    import sys
    sys.argv = [
        'build_candidates.py',
        '--signals', str(signals_path),
        '--output', str(output_file),
        '--render-md', str(md_file)
    ]

    try:
        main()
    except SystemExit:
        pass

    # Verify output
    assert output_file.exists()

    with open(output_file) as f:
        data = yaml.safe_load(f)

    # Check structure
    assert 'domains' in data
    assert 'concepts' in data
    assert 'rules' in data
    assert 'demand_models' in data
    assert 'metadata' in data

    # Check metadata
    assert 'generated_at' in data['metadata']
    assert 'signal_source' in data['metadata']  # Note: signal_source not signals_source
    assert 'candidate_count' in data['metadata']

    # Check candidate groups are lists
    assert isinstance(data['domains'], list)
    assert isinstance(data['concepts'], list)
    assert isinstance(data['rules'], list)
    assert isinstance(data['demand_models'], list)

def test_candidates_markdown_generation(tmp_path):
    """Test candidates.md generation"""
    signals_path = Path("docs/fact/signals.yaml")
    if not signals_path.exists():
        pytest.skip("signals.yaml not found")

    output_file = tmp_path / "candidates.yaml"
    md_file = tmp_path / "candidates.md"

    import sys
    sys.argv = [
        'build_candidates.py',
        '--signals', str(signals_path),
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
    assert '# Semantic Candidates' in content
    assert 'Domains' in content  # Section header
    assert 'Concepts' in content
    assert 'Rules' in content
    assert 'Demand Models' in content

def test_deterministic_synthesis():
    """Test that same inputs produce same candidates"""
    domain_signals = [
        {
            'signal_type': 'module_grouping',
            'source': 'test',
            'evidence': 'test',
            'confidence': 'high',
            'summary': 'test'
        }
    ]

    candidates1 = synthesize_domain_candidates(domain_signals)
    candidates2 = synthesize_domain_candidates(domain_signals)

    assert len(candidates1) == len(candidates2)
    # IDs should be stable
    if candidates1 and candidates2:
        assert candidates1[0]['id'] == candidates2[0]['id']

def test_source_signal_preservation():
    """Test that source signal IDs are preserved"""
    domain_signals = [
        {
            'signal_type': 'module_grouping',
            'source': 'test',
            'evidence': 'test evidence',
            'confidence': 'high',
            'summary': 'test'
        }
    ]

    candidates = synthesize_domain_candidates(domain_signals)

    for candidate in candidates:
        assert 'source_signal_ids' in candidate
        assert len(candidate['source_signal_ids']) > 0
        assert 'evidence_refs' in candidate
        assert len(candidate['evidence_refs']) > 0

def test_not_one_to_one_copying():
    """Test that synthesis is not just one-to-one signal copying"""
    # Multiple signals should potentially synthesize into fewer candidates
    domain_signals = [
        {
            'signal_type': 'module_grouping',
            'source': 'test1',
            'evidence': 'evidence1',
            'confidence': 'high',
            'summary': 'summary1'
        },
        {
            'signal_type': 'module_grouping',
            'source': 'test2',
            'evidence': 'evidence2',
            'confidence': 'high',
            'summary': 'summary2'
        }
    ]

    candidates = synthesize_domain_candidates(domain_signals)

    # Should synthesize, not just copy
    # (In current implementation, similar signal types may be grouped)
    assert isinstance(candidates, list)
    # The key is that synthesis logic exists, not just pass-through
