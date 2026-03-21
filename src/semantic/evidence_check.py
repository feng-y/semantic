"""
Semantic Evidence Check Generation

Generates evidence check tasks from recommendations that need verification.
"""

import hashlib
from typing import Any

_SINGULAR = {
    'domains': 'domain',
    'concepts': 'concept',
    'rules': 'rule',
    'demand_models': 'demand_model',
}

def generate_check_id(target_id: str) -> str:
    """Generate stable check ID from target ID"""
    hash_suffix = hashlib.sha256(target_id.encode()).hexdigest()[:12]
    return f"check_{hash_suffix}"

def create_evidence_check(recommendation: dict[str, Any], rec_type: str) -> dict[str, Any]:
    """
    Create an evidence check entry for a recommendation that needs verification.
    
    Returns evidence check dict with:
    - id
    - target_id
    - target_type
    - target_name
    - reason
    - required_evidence
    - status
    - source_recommendation_id
    - source_candidate_id
    """
    check = {
        'id': generate_check_id(recommendation['id']),
        'target_id': recommendation['id'],
        'target_type': rec_type,
        'target_name': recommendation['name'],
        'reason': recommendation.get('evidence_gap', 'Requires verification'),
        'required_evidence': [
            "Validate evidence references",
            "Confirm boundary/relationships",
            "Verify confidence level"
        ],
        'status': 'pending',
        'source_recommendation_id': recommendation['id'],
        'source_candidate_id': recommendation.get('candidate_id')
    }

    return check

def generate_evidence_checks(recommendations: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Generate evidence checks for recommendations that need verification.
    
    Identifies recommendations with:
    - needs_evidence_check: true
    - action: verify_first
    """
    checks = []

    # Process each recommendation group
    for group_name in ['domains', 'concepts', 'rules', 'demand_models']:
        recs = recommendations.get(group_name, [])
        rec_type = _SINGULAR.get(group_name, group_name.rstrip('s'))

        for rec in recs:
            # Check if verification is needed
            needs_check = rec.get('needs_evidence_check', False)
            action = rec.get('recommendation', {}).get('action')

            if needs_check or action == 'verify_first':
                check = create_evidence_check(rec, rec_type)
                checks.append(check)

    return checks

def generate_evidence_checks_with_metadata(recommendations: dict[str, Any], decisions_data: dict[str, Any]) -> dict[str, Any]:
    """
    Generate evidence checks with metadata structure.
    Wrapper that adds metadata to the checks list.
    """
    checks = generate_evidence_checks(recommendations)

    return {
        'evidence_checks': checks,
        'metadata': {
            'generated_at': decisions_data['metadata']['generated_at'],
            'recommendations_source': decisions_data['metadata']['recommendations_source'],
            'check_count': len(checks)
        }
    }
