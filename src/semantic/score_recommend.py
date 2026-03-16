"""
Semantic Recommendation Generation

Generates structured recommendations from semantic candidates.
This is the third stage of the semantic layer.
"""

from pathlib import Path
import argparse
import yaml
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

def load_candidates(candidates_path: Path) -> Optional[Dict[str, Any]]:
    """Load candidates.yaml (primary input)"""
    if not candidates_path.exists():
        return None
    with open(candidates_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_stable_id(name: str, type_prefix: str) -> str:
    """Generate stable ID from name"""
    hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"rec_{type_prefix}_{hash_suffix}"

def evaluate_semantic_validity(candidate: Dict[str, Any], candidate_type: str) -> Tuple[str, str]:
    """
    Evaluate semantic validity of a candidate.
    Returns (validity, reason)

    Deterministic rules:
    - PASS if confidence is high
    - PASS if confidence is medium and has evidence
    - FAIL if confidence is low
    - FAIL if missing required fields
    """
    confidence = candidate.get('confidence', 'low')
    evidence_refs = candidate.get('evidence_refs', [])

    # Check required fields
    required_fields = ['id', 'name', 'summary']
    missing_fields = [f for f in required_fields if not candidate.get(f)]
    if missing_fields:
        return 'fail', f"Missing required fields: {', '.join(missing_fields)}"

    # Evaluate based on confidence and evidence
    if confidence == 'high':
        return 'pass', 'High confidence with strong evidence'
    elif confidence == 'medium':
        if evidence_refs:
            return 'pass', 'Medium confidence with supporting evidence'
        else:
            return 'fail', 'Medium confidence but lacks evidence'
    else:  # low confidence
        return 'fail', 'Low confidence, needs more evidence'

def compute_scores(candidate: Dict[str, Any], candidate_type: str) -> Tuple[float, float]:
    """
    Compute business_score and value_score.
    Returns (business_score, value_score)

    Deterministic scoring based on:
    - Confidence level
    - Evidence strength
    - Source signal quality
    """
    confidence = candidate.get('confidence', 'low')
    evidence_refs = candidate.get('evidence_refs', [])
    source_signal_ids = candidate.get('source_signal_ids', [])

    # Base scores by confidence
    confidence_scores = {
        'high': 8.0,
        'medium': 6.0,
        'low': 3.0
    }
    base_score = confidence_scores.get(confidence, 3.0)

    # Adjust for evidence strength
    evidence_bonus = min(len(evidence_refs) * 0.5, 2.0)

    # Adjust for signal quality
    signal_bonus = min(len(source_signal_ids) * 0.3, 1.0)

    # Business score: base + evidence
    business_score = min(base_score + evidence_bonus, 10.0)

    # Value score: base + signals
    value_score = min(base_score + signal_bonus, 10.0)

    return round(business_score, 1), round(value_score, 1)

def determine_recommendation(
    validity: str,
    business_score: float,
    value_score: float,
    candidate: Dict[str, Any],
    candidate_type: str
) -> Dict[str, Any]:
    """
    Determine recommendation status and action.
    Returns recommendation body dict.

    Rules:
    - If validity=fail: not_recommend + drop
    - If priority >= 7.0: recommend + keep
    - If priority >= 5.0: recommend + verify_first
    - If priority < 5.0: defer + backlog
    """
    priority = max(business_score, value_score)

    # Map candidate type to asset type
    asset_type_map = {
        'domain': 'domain_map',
        'concept': 'concept_map',
        'rule': 'rule_map',
        'demand_model': 'demand_model_map'
    }
    target_asset_type = asset_type_map.get(candidate_type, 'none')

    if validity == 'fail':
        return {
            'status': 'not_recommend',
            'action': 'drop',
            'target_layer': 'candidate_pool',
            'target_asset_type': 'none'
        }

    if priority >= 7.0:
        return {
            'status': 'recommend',
            'action': 'keep',
            'target_layer': 'final_asset',
            'target_asset_type': target_asset_type
        }
    elif priority >= 5.0:
        return {
            'status': 'recommend',
            'action': 'verify_first',
            'target_layer': 'candidate_pool',
            'target_asset_type': target_asset_type
        }
    else:
        return {
            'status': 'defer',
            'action': 'backlog',
            'target_layer': 'candidate_pool',
            'target_asset_type': 'none'
        }

def generate_reasons(
    validity: str,
    business_score: float,
    value_score: float,
    candidate: Dict[str, Any],
    recommendation: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Generate recommended_reasons and not_recommended_reasons.
    Returns (recommended_reasons, not_recommended_reasons)
    """
    recommended = []
    not_recommended = []

    confidence = candidate.get('confidence', 'low')
    evidence_refs = candidate.get('evidence_refs', [])

    if validity == 'pass':
        recommended.append(f"Semantic validity passed")
        if confidence == 'high':
            recommended.append(f"High confidence level")
        if evidence_refs:
            recommended.append(f"Strong evidence support ({len(evidence_refs)} refs)")
        if business_score >= 7.0:
            recommended.append(f"High business value (score: {business_score})")
        if value_score >= 7.0:
            recommended.append(f"High technical value (score: {value_score})")
    else:
        not_recommended.append(f"Semantic validity failed")
        if confidence == 'low':
            not_recommended.append(f"Low confidence level")
        if not evidence_refs:
            not_recommended.append(f"Insufficient evidence")

    return recommended, not_recommended

def check_evidence_needs(
    candidate: Dict[str, Any],
    validity: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if evidence verification is needed.
    Returns (needs_check, gap_description)
    """
    evidence_refs = candidate.get('evidence_refs', [])
    confidence = candidate.get('confidence', 'low')

    if validity == 'fail':
        return False, None  # Already failed, no need to check

    if confidence == 'medium' and len(evidence_refs) < 2:
        return True, "Medium confidence with limited evidence - needs verification"

    if confidence == 'high' and not evidence_refs:
        return True, "High confidence claimed but no evidence provided"

    return False, None

def generate_recommendation_item(
    candidate: Dict[str, Any],
    candidate_type: str
) -> Dict[str, Any]:
    """Generate a single recommendation item from a candidate"""

    # Step 1: Evaluate validity
    validity, validity_reason = evaluate_semantic_validity(candidate, candidate_type)

    # Step 2: Compute scores
    business_score, value_score = compute_scores(candidate, candidate_type)

    # Step 3: Compute priority (max of scores)
    priority = max(business_score, value_score)

    # Step 4: Determine recommendation
    recommendation = determine_recommendation(
        validity, business_score, value_score, candidate, candidate_type
    )

    # Step 5: Generate reasons
    recommended_reasons, not_recommended_reasons = generate_reasons(
        validity, business_score, value_score, candidate, recommendation
    )

    # Step 6: Check evidence needs
    needs_evidence_check, evidence_gap = check_evidence_needs(candidate, validity)

    # Step 7: Build recommendation item
    rec_id = generate_stable_id(candidate['name'], candidate_type)

    return {
        'id': rec_id,
        'name': candidate['name'],
        'candidate_id': candidate['id'],
        'semantic_validity': validity,
        'validity_reason': validity_reason,
        'business_score': business_score,
        'value_score': value_score,
        'priority': priority,
        'recommendation': recommendation,
        'recommended_reasons': recommended_reasons,
        'not_recommended_reasons': not_recommended_reasons,
        'needs_evidence_check': needs_evidence_check,
        'evidence_gap': evidence_gap,
        'merge_target': None,  # Not implemented in this deterministic version
        'source_candidate_ids': [candidate['id']],
        'evidence_refs': candidate.get('evidence_refs', [])
    }

def generate_domain_recommendations(domains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate recommendations for domain candidates"""
    return [generate_recommendation_item(d, 'domain') for d in domains]

def generate_concept_recommendations(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate recommendations for concept candidates"""
    return [generate_recommendation_item(c, 'concept') for c in concepts]

def generate_rule_recommendations(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate recommendations for rule candidates"""
    return [generate_recommendation_item(r, 'rule') for r in rules]

def generate_demand_model_recommendations(demand_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate recommendations for demand model candidates"""
    return [generate_recommendation_item(dm, 'demand_model') for dm in demand_models]

def render_recommendations_markdown(recommendations_data: Dict[str, Any], output_path: Path):
    """Render recommendations as markdown"""
    lines = []
    lines.append("# Semantic Recommendations")
    lines.append("")
    lines.append(f"**Generated**: {recommendations_data['metadata']['generated_at']}")
    lines.append(f"**Source**: {recommendations_data['metadata']['candidates_source']}")
    lines.append(f"**Total Recommendations**: {recommendations_data['metadata']['recommendation_count']}")
    lines.append("")

    # Domains
    lines.append("## Domain Recommendations")
    lines.append("")
    if recommendations_data['domains']:
        for rec in recommendations_data['domains']:
            lines.append(f"### {rec['name']}")
            lines.append(f"- **ID**: `{rec['id']}`")
            lines.append(f"- **Candidate ID**: `{rec['candidate_id']}`")
            lines.append(f"- **Validity**: {rec['semantic_validity']} - {rec['validity_reason']}")
            lines.append(f"- **Scores**: Business={rec['business_score']}, Value={rec['value_score']}, Priority={rec['priority']}")
            lines.append(f"- **Recommendation**: {rec['recommendation']['status']} → {rec['recommendation']['action']}")
            if rec['recommended_reasons']:
                lines.append(f"- **Recommended**: {', '.join(rec['recommended_reasons'])}")
            if rec['not_recommended_reasons']:
                lines.append(f"- **Not Recommended**: {', '.join(rec['not_recommended_reasons'])}")
            if rec['needs_evidence_check']:
                lines.append(f"- **Evidence Check Needed**: {rec['evidence_gap']}")
            lines.append("")
    else:
        lines.append("*(No domain recommendations)*")
        lines.append("")

    # Concepts
    lines.append("## Concept Recommendations")
    lines.append("")
    if recommendations_data['concepts']:
        for rec in recommendations_data['concepts']:
            lines.append(f"### {rec['name']}")
            lines.append(f"- **ID**: `{rec['id']}`")
            lines.append(f"- **Candidate ID**: `{rec['candidate_id']}`")
            lines.append(f"- **Validity**: {rec['semantic_validity']} - {rec['validity_reason']}")
            lines.append(f"- **Scores**: Business={rec['business_score']}, Value={rec['value_score']}, Priority={rec['priority']}")
            lines.append(f"- **Recommendation**: {rec['recommendation']['status']} → {rec['recommendation']['action']}")
            if rec['recommended_reasons']:
                lines.append(f"- **Recommended**: {', '.join(rec['recommended_reasons'])}")
            if rec['not_recommended_reasons']:
                lines.append(f"- **Not Recommended**: {', '.join(rec['not_recommended_reasons'])}")
            lines.append("")
    else:
        lines.append("*(No concept recommendations)*")
        lines.append("")

    # Rules
    lines.append("## Rule Recommendations")
    lines.append("")
    if recommendations_data['rules']:
        for rec in recommendations_data['rules']:
            lines.append(f"### {rec['name']}")
            lines.append(f"- **ID**: `{rec['id']}`")
            lines.append(f"- **Candidate ID**: `{rec['candidate_id']}`")
            lines.append(f"- **Validity**: {rec['semantic_validity']} - {rec['validity_reason']}")
            lines.append(f"- **Scores**: Business={rec['business_score']}, Value={rec['value_score']}, Priority={rec['priority']}")
            lines.append(f"- **Recommendation**: {rec['recommendation']['status']} → {rec['recommendation']['action']}")
            if rec['recommended_reasons']:
                lines.append(f"- **Recommended**: {', '.join(rec['recommended_reasons'])}")
            lines.append("")
    else:
        lines.append("*(No rule recommendations)*")
        lines.append("")

    # Demand Models
    lines.append("## Demand Model Recommendations")
    lines.append("")
    if recommendations_data['demand_models']:
        for rec in recommendations_data['demand_models']:
            lines.append(f"### {rec['name']}")
            lines.append(f"- **ID**: `{rec['id']}`")
            lines.append(f"- **Candidate ID**: `{rec['candidate_id']}`")
            lines.append(f"- **Validity**: {rec['semantic_validity']} - {rec['validity_reason']}")
            lines.append(f"- **Scores**: Business={rec['business_score']}, Value={rec['value_score']}, Priority={rec['priority']}")
            lines.append(f"- **Recommendation**: {rec['recommendation']['status']} → {rec['recommendation']['action']}")
            if rec['recommended_reasons']:
                lines.append(f"- **Recommended**: {', '.join(rec['recommended_reasons'])}")
            lines.append("")
    else:
        lines.append("*(No demand model recommendations)*")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    parser = argparse.ArgumentParser(description="Generate semantic recommendations from candidates")
    parser.add_argument("--candidates", required=True, help="Path to candidates.yaml")
    parser.add_argument("--output", required=True, help="Path to output recommendations.yaml")
    parser.add_argument("--render-md", help="Path to output recommendations.md")
    args = parser.parse_args()

    # Load candidates
    candidates_path = Path(args.candidates)
    candidates = load_candidates(candidates_path)

    if not candidates:
        print(f"ERROR: Could not load candidates from {candidates_path}")
        return

    # Extract candidate groups
    domains = candidates.get('domains', [])
    concepts = candidates.get('concepts', [])
    rules = candidates.get('rules', [])
    demand_models = candidates.get('demand_models', [])

    # Generate recommendations
    domain_recs = generate_domain_recommendations(domains)
    concept_recs = generate_concept_recommendations(concepts)
    rule_recs = generate_rule_recommendations(rules)
    demand_model_recs = generate_demand_model_recommendations(demand_models)

    # Build output structure
    recommendations_data = {
        'domains': domain_recs,
        'concepts': concept_recs,
        'rules': rule_recs,
        'demand_models': demand_model_recs,
        'metadata': {
            'generated_at': datetime.now().astimezone().isoformat(),
            'candidates_source': 'candidates.yaml',
            'recommendation_count': len(domain_recs) + len(concept_recs) + len(rule_recs) + len(demand_model_recs)
        }
    }

    # Write canonical output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(recommendations_data, f, sort_keys=False, allow_unicode=True)

    # Render view output
    if args.render_md:
        render_recommendations_markdown(recommendations_data, Path(args.render_md))

    # Print summary
    print(f"✓ Generated {recommendations_data['metadata']['recommendation_count']} recommendations")
    print(f"  - Domains: {len(domain_recs)}")
    print(f"  - Concepts: {len(concept_recs)}")
    print(f"  - Rules: {len(rule_recs)}")
    print(f"  - Demand models: {len(demand_model_recs)}")
    print(f"✓ Written to: {output_path}")
    if args.render_md:
        print(f"✓ Rendered view: {args.render_md}")

if __name__ == "__main__":
    main()
