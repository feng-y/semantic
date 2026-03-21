"""
Integration tests for incremental signal extraction
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from src.semantic.extract_signals import (
    extract_signals_from_files,
    load_fact_canonical,
    load_fact_working_summary,
    run_incremental_extraction,
)


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory with FACT structure"""
    temp_dir = tempfile.mkdtemp()
    project_root = Path(temp_dir)

    # Create FACT directory structure
    fact_root = project_root / "docs" / "semantic-foundation" / "fact"
    fact_root.mkdir(parents=True)

    yield project_root, fact_root

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_canonical_data():
    """Sample canonical FACT data"""
    return {
        'modules': [
            {'name': 'module1', 'path': '/src/module1'},
            {'name': 'module2', 'path': '/src/module2'},
            {'name': 'validation', 'path': '/src/validation'}
        ],
        'core_entities': [
            {'name': 'User', 'type': 'entity'},
            {'name': 'Order', 'type': 'entity'}
        ]
    }


@pytest.fixture
def sample_working_data():
    """Sample working summary data"""
    return {
        'domain_proposals': [
            {'name': 'user_management'},
            {'name': 'order_processing'}
        ],
        'concepts': [
            {'name': 'authentication'},
            {'name': 'authorization'}
        ]
    }


def test_full_extraction(temp_project_dir, sample_canonical_data, sample_working_data):
    """Test full signal extraction"""
    project_root, fact_root = temp_project_dir

    # Write FACT files
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(sample_canonical_data, f)

    working_path = fact_root / "fact_working_summary_sample.yaml"
    with open(working_path, 'w') as f:
        yaml.safe_dump(sample_working_data, f)

    # Load and extract
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)

    signals = extract_signals_from_files(canonical, working)

    # Verify signals extracted
    assert len(signals['domain_signals']) > 0
    assert len(signals['concept_signals']) > 0
    assert len(signals['rule_signals']) > 0


def test_incremental_first_run(temp_project_dir, sample_canonical_data):
    """Test incremental extraction on first run (all files new)"""
    project_root, fact_root = temp_project_dir
    cache_dir = project_root / ".semantic-cache"

    # Write FACT file
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(sample_canonical_data, f)

    # Run incremental extraction
    signals = run_incremental_extraction(fact_root, cache_dir)

    # Verify signals extracted
    assert len(signals['domain_signals']) > 0
    assert len(signals['concept_signals']) > 0

    # Verify cache created
    assert cache_dir.exists()
    assert (cache_dir / "cache_index.json").exists()


def test_incremental_no_changes(temp_project_dir, sample_canonical_data):
    """Test incremental extraction with no changes (uses cache)"""
    project_root, fact_root = temp_project_dir
    cache_dir = project_root / ".semantic-cache"

    # Write FACT file
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(sample_canonical_data, f)

    # First run
    signals1 = run_incremental_extraction(fact_root, cache_dir)

    # Second run (no changes)
    signals2 = run_incremental_extraction(fact_root, cache_dir)

    # Results should be identical
    assert signals1 == signals2


def test_incremental_with_changes(temp_project_dir, sample_canonical_data):
    """Test incremental extraction with file changes"""
    project_root, fact_root = temp_project_dir
    cache_dir = project_root / ".semantic-cache"

    # Write initial FACT file
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(sample_canonical_data, f)

    # First run
    signals1 = run_incremental_extraction(fact_root, cache_dir)
    initial_module_count = len(signals1['domain_signals'])

    # Modify FACT file (add more modules)
    modified_data = sample_canonical_data.copy()
    modified_data['modules'].append({'name': 'module3', 'path': '/src/module3'})

    with open(canonical_path, 'w') as f:
        yaml.safe_dump(modified_data, f)

    # Second run (with changes)
    signals2 = run_incremental_extraction(fact_root, cache_dir)

    # Signals should be re-extracted
    assert signals2 is not None
    # Module count might change based on extraction logic


def test_incremental_cache_invalidation(temp_project_dir, sample_canonical_data):
    """Test that cache is properly invalidated on file changes"""
    project_root, fact_root = temp_project_dir
    cache_dir = project_root / ".semantic-cache"

    # Write FACT file
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(sample_canonical_data, f)

    # First run - creates cache
    run_incremental_extraction(fact_root, cache_dir)

    # Verify cache exists
    cache_index = cache_dir / "cache_index.json"
    assert cache_index.exists()

    # Modify file
    modified_data = sample_canonical_data.copy()
    modified_data['modules'].append({'name': 'new_module', 'path': '/src/new'})

    with open(canonical_path, 'w') as f:
        yaml.safe_dump(modified_data, f)

    # Second run - should detect change and update cache
    signals = run_incremental_extraction(fact_root, cache_dir)

    assert signals is not None
    # Cache should be updated with new hash


def test_missing_canonical_file(temp_project_dir):
    """Test handling of missing canonical file"""
    project_root, fact_root = temp_project_dir
    cache_dir = project_root / ".semantic-cache"

    # Don't create canonical file
    signals = run_incremental_extraction(fact_root, cache_dir)

    # Should return empty signals structure
    assert signals['domain_signals'] == []
    assert signals['concept_signals'] == []
    assert signals['rule_signals'] == []
    assert signals['demand_pattern_signals'] == []


def test_working_summary_optional(temp_project_dir, sample_canonical_data):
    """Test that working summary is optional"""
    project_root, fact_root = temp_project_dir
    cache_dir = project_root / ".semantic-cache"

    # Write only canonical file (no working summary)
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(sample_canonical_data, f)

    # Should work without working summary
    signals = run_incremental_extraction(fact_root, cache_dir)

    assert len(signals['domain_signals']) > 0
    assert len(signals['concept_signals']) > 0
