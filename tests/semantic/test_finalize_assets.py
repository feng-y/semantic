"""Tests for semantic finalization"""
import pytest, sys, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.finalize_assets import (
    load_yaml, check_unresolved_verifications, generate_final_id,
    finalize_domain, finalize_concept, finalize_rule, finalize_demand_model,
    build_change_log, main
)

def test_generate_final_id():
    id1 = generate_final_id("Test", "domain")
    id2 = generate_final_id("Test", "domain")
    assert id1 == id2
    assert id1.startswith("domain_")

def test_finalize_domain():
    dec = {'id': 'review_1', 'name': 'Test Domain', 'evidence_refs': ['ev1']}
    asset = finalize_domain(dec)
    assert 'id' in asset
    assert asset['name'] == 'Test Domain'
    assert 'evidence_refs' in asset

def test_finalize_concept():
    dec = {'id': 'review_2', 'name': 'Test Concept', 'evidence_refs': []}
    asset = finalize_concept(dec)
    assert 'boundary' in asset

def test_finalize_rule():
    dec = {'id': 'review_3', 'name': 'Test Rule', 'evidence_refs': []}
    asset = finalize_rule(dec)
    assert 'validation' in asset
    assert asset['validation']['type'] == 'semantic'

def test_check_unresolved_verifications():
    checks = {'evidence_checks': [{'status': 'pending', 'target_name': 'Test'}]}
    unresolved = check_unresolved_verifications(checks)
    assert len(unresolved) == 1

def test_build_change_log():
    decisions = {
        'domains': [
            {'name': 'D1', 'final_action': 'keep', 'final_reason': 'Approved'},
            {'name': 'D2', 'final_action': 'drop', 'final_reason': 'Not needed'}
        ],
        'concepts': [], 'rules': [], 'demand_models': []
    }
    log = build_change_log(decisions)
    assert len(log['added']) == 1
    assert len(log['dropped']) == 1

def test_finalize_execution(tmp_path):
    decisions_path = tmp_path / "decisions.yaml"
    checks_path = tmp_path / "checks.yaml"
    
    decisions = {
        'domains': [{'id': 'r1', 'name': 'D1', 'final_action': 'keep', 'final_reason': 'OK', 'evidence_refs': []}],
        'concepts': [], 'rules': [], 'demand_models': []
    }
    checks = {'evidence_checks': [], 'metadata': {}}
    
    decisions_path.write_text(yaml.dump(decisions))
    checks_path.write_text(yaml.dump(checks))
    
    sys.argv = ['finalize_assets.py', '--decisions', str(decisions_path), '--checks', str(checks_path), '--output-dir', str(tmp_path)]
    
    try:
        main()
    except SystemExit:
        pass
    
    assert (tmp_path / "domain-map.yaml").exists()
    assert (tmp_path / "change-log.yaml").exists()
