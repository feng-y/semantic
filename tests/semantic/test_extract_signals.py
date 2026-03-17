"""
Tests for semantic signals extraction
"""

import pytest
from pathlib import Path
import yaml
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.extract_signals import (
    load_fact_canonical,
    load_fact_working_summary,
    extract_domain_signals,
    extract_concept_signals,
    extract_rule_signals,
    extract_demand_pattern_signals,
    main
)

def test_load_fact_canonical():
    """Test loading FACT canonical YAML"""
    fact_root = Path("docs/fact")
    if not fact_root.exists():
        pytest.skip("FACT root not found")

    canonical = load_fact_canonical(fact_root)
    if canonical:
        assert isinstance(canonical, dict)
        assert 'modules' in canonical or 'repo_identity' in canonical

def test_load_fact_working_summary():
    """Test loading FACT working summary YAML"""
    fact_root = Path("docs/fact")
    if not fact_root.exists():
        pytest.skip("FACT root not found")

    working = load_fact_working_summary(fact_root)
    if working:
        assert isinstance(working, dict)

def test_extract_domain_signals():
    """Test domain signal extraction"""
    canonical = {
        'modules': [
            {'name': 'module1', 'path': 'src/module1.py'},
            {'name': 'module2', 'path': 'src/module2.py'}
        ]
    }
    working = {
        'domain_proposals': [
            {'name': 'domain1'},
            {'name': 'domain2'}
        ]
    }

    signals = extract_domain_signals(canonical, working)
    assert isinstance(signals, list)
    assert len(signals) > 0

    for sig in signals:
        assert 'signal_type' in sig
        assert 'source' in sig
        assert 'evidence' in sig
        assert 'confidence' in sig
        assert sig['confidence'] in ['high', 'medium', 'low']

def test_extract_concept_signals():
    """Test concept signal extraction"""
    canonical = {
        'core_entities': [
            {'name': 'Entity1', 'type': 'class'},
            {'name': 'Entity2', 'type': 'class'}
        ]
    }
    working = {
        'concepts': [
            {'name': 'Concept1'},
            {'name': 'Concept2'}
        ]
    }

    signals = extract_concept_signals(canonical, working)
    assert isinstance(signals, list)
    assert len(signals) > 0

def test_extract_rule_signals():
    """Test rule signal extraction"""
    canonical = {
        'modules': [
            {'name': 'artifact_validation', 'path': 'src/artifact_validation.py'},
            {'name': 'other_module', 'path': 'src/other.py'}
        ]
    }

    signals = extract_rule_signals(canonical, None)
    assert isinstance(signals, list)

def test_extract_demand_pattern_signals():
    """Test demand pattern signal extraction"""
    canonical = {
        'modules': [
            {'name': 'change_analysis_generation', 'path': 'src/change_analysis_generation.py'},
            {'name': 'other_module', 'path': 'src/other.py'}
        ]
    }

    signals = extract_demand_pattern_signals(canonical, None)
    assert isinstance(signals, list)

def test_signals_yaml_structure(tmp_path):
    """Test signals.yaml structure validity"""
    output_file = tmp_path / "signals.yaml"
    md_file = tmp_path / "signals.md"

    # Create minimal test data
    fact_root = Path("docs/semantic-foundation/fact")
    if not fact_root.exists():
        pytest.skip("FACT root not found")

    # Run extraction
    import sys
    sys.argv = [
        'extract_signals.py',
        '--fact-root', str(fact_root),
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
    assert 'domain_signals' in data
    assert 'concept_signals' in data
    assert 'rule_signals' in data
    assert 'demand_pattern_signals' in data
    assert 'metadata' in data

    # Check metadata
    assert 'generated_at' in data['metadata']
    assert 'fact_source' in data['metadata']
    assert 'signal_count' in data['metadata']

    # Check signal groups are lists
    assert isinstance(data['domain_signals'], list)
    assert isinstance(data['concept_signals'], list)
    assert isinstance(data['rule_signals'], list)
    assert isinstance(data['demand_pattern_signals'], list)

def test_signals_markdown_generation(tmp_path):
    """Test signals.md generation"""
    output_file = tmp_path / "signals.yaml"
    md_file = tmp_path / "signals.md"

    fact_root = Path("docs/semantic-foundation/fact")
    if not fact_root.exists():
        pytest.skip("FACT root not found")

    import sys
    sys.argv = [
        'extract_signals.py',
        '--fact-root', str(fact_root),
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
    assert '# Semantic Signals' in content
    assert 'Domain Signals' in content
    assert 'Concept Signals' in content
    assert 'Rule Signals' in content
    assert 'Demand Pattern Signals' in content

def test_deterministic_extraction():
    """Test that same inputs produce same signals"""
    canonical = {
        'modules': [
            {'name': 'module1', 'path': 'src/module1.py'}
        ]
    }

    signals1 = extract_domain_signals(canonical, None)
    signals2 = extract_domain_signals(canonical, None)

    assert signals1 == signals2

def test_evidence_preservation():
    """Test that evidence refs are preserved"""
    canonical = {
        'modules': [
            {'name': 'module1', 'path': 'src/module1.py', 'evidence': 'src/module1.py:1-100'}
        ]
    }

    signals = extract_domain_signals(canonical, None)

    for sig in signals:
        assert 'evidence' in sig
        assert sig['evidence'] is not None
        assert len(sig['evidence']) > 0
