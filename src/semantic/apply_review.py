"""
Semantic Review Decision Generation

Generates structured review decisions from semantic recommendations.
This is the fourth stage of the semantic layer.
"""

from pathlib import Path
import argparse
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

try:
    from semantic.feedback import FeedbackCollector
    _feedback_available = True
except ImportError:
    _feedback_available = False

def load_recommendations(recommendations_path: Path) -> Optional[Dict[str, Any]]:
    """Load recommendations.yaml (primary input)"""
    if not recommendations_path.exists():
        return None
    with open(recommendations_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_stable_id(name: str, type_prefix: str) -> str:
    """Generate stable ID from name"""
    hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"review_{type_prefix}_{hash_suffix}"

def convert_to_review_decision(recommendation: Dict[str, Any], rec_type: str) -> Dict[str, Any]:
    """
    Convert a recommendation into a review decision.
    
    Deterministic conversion:
    - final_action = recommendation.action
    - Preserve all traceability
    - Add review-specific fields
    """
    rec_action = recommendation.get('recommendation', {}).get('action', 'backlog')
    
    # Map recommendation action to final action (1:1 in deterministic mode)
    final_action = rec_action
    
    # Generate final reason
    rec_status = recommendation.get('recommendation', {}).get('status', 'defer')
    if rec_status == 'recommend' and rec_action == 'keep':
        final_reason = "Approved for inclusion in final semantic assets"
    elif rec_status == 'recommend' and rec_action == 'verify_first':
        final_reason = "Approved pending evidence verification"
    elif rec_status == 'not_recommend':
        final_reason = "Not recommended for inclusion"
    elif rec_status == 'defer':
        final_reason = "Deferred to future iteration"
    else:
        final_reason = f"Action: {rec_action}"
    
    decision = {
        'id': generate_stable_id(recommendation['name'], rec_type),
        'name': recommendation['name'],
        'final_action': final_action,
        'final_reason': final_reason,
        'source_recommendation_id': recommendation['id'],
        'source_candidate_id': recommendation.get('candidate_id'),
        'evidence_refs': recommendation.get('evidence_refs', []),
        'merge_target': recommendation.get('merge_target')
    }
    
    return decision

def generate_review_decisions(recommendations: Dict[str, Any]) -> Dict[str, Any]:
    """Generate review decisions for all recommendation groups"""
    decisions = {
        'domains': [],
        'concepts': [],
        'rules': [],
        'demand_models': []
    }
    
    # Process each recommendation group
    for group_name in ['domains', 'concepts', 'rules', 'demand_models']:
        recs = recommendations.get(group_name, [])
        rec_type = group_name.rstrip('s')  # domain, concept, rule, demand_model
        
        for rec in recs:
            decision = convert_to_review_decision(rec, rec_type)
            decisions[group_name].append(decision)
    
    return decisions

def render_review_note_markdown(
    decisions_data: Dict[str, Any],
    checks_data: Dict[str, Any],
    output_path: Path
):
    """Render review-note.md (human-readable view)"""
    lines = []
    
    # Header
    lines.append("# Semantic Review Note")
    lines.append("")
    lines.append(f"**Generated**: {decisions_data['metadata']['generated_at']}")
    lines.append(f"**Source**: {decisions_data['metadata']['recommendations_source']}")
    lines.append(f"**Total Decisions**: {decisions_data['metadata']['decision_count']}")
    lines.append(f"**Evidence Checks**: {checks_data['metadata']['check_count']}")
    lines.append("")
    
    # Domain Decisions
    lines.append("## Domain Review Decisions")
    lines.append("")
    if decisions_data['domains']:
        for decision in decisions_data['domains']:
            lines.append(f"### {decision['name']}")
            lines.append(f"- **ID**: `{decision['id']}`")
            lines.append(f"- **Final Action**: {decision['final_action']}")
            lines.append(f"- **Reason**: {decision['final_reason']}")
            lines.append(f"- **Source Recommendation**: `{decision['source_recommendation_id']}`")
            if decision.get('merge_target'):
                lines.append(f"- **Merge Target**: `{decision['merge_target']}`")
            lines.append("")
    else:
        lines.append("*(No domain decisions)*")
        lines.append("")
    
    # Concept Decisions
    lines.append("## Concept Review Decisions")
    lines.append("")
    if decisions_data['concepts']:
        for decision in decisions_data['concepts']:
            lines.append(f"### {decision['name']}")
            lines.append(f"- **ID**: `{decision['id']}`")
            lines.append(f"- **Final Action**: {decision['final_action']}")
            lines.append(f"- **Reason**: {decision['final_reason']}")
            lines.append("")
    else:
        lines.append("*(No concept decisions)*")
        lines.append("")
    
    # Rule Decisions
    lines.append("## Rule Review Decisions")
    lines.append("")
    if decisions_data['rules']:
        for decision in decisions_data['rules']:
            lines.append(f"### {decision['name']}")
            lines.append(f"- **ID**: `{decision['id']}`")
            lines.append(f"- **Final Action**: {decision['final_action']}")
            lines.append(f"- **Reason**: {decision['final_reason']}")
            lines.append("")
    else:
        lines.append("*(No rule decisions)*")
        lines.append("")
    
    # Demand Model Decisions
    lines.append("## Demand Model Review Decisions")
    lines.append("")
    if decisions_data['demand_models']:
        for decision in decisions_data['demand_models']:
            lines.append(f"### {decision['name']}")
            lines.append(f"- **ID**: `{decision['id']}`")
            lines.append(f"- **Final Action**: {decision['final_action']}")
            lines.append(f"- **Reason**: {decision['final_reason']}")
            lines.append("")
    else:
        lines.append("*(No demand model decisions)*")
        lines.append("")
    
    # Evidence Checks
    if checks_data['evidence_checks']:
        lines.append("## Evidence Verification Tasks")
        lines.append("")
        for check in checks_data['evidence_checks']:
            lines.append(f"### {check['target_name']}")
            lines.append(f"- **Check ID**: `{check['id']}`")
            lines.append(f"- **Target**: `{check['target_id']}` ({check['target_type']})")
            lines.append(f"- **Reason**: {check['reason']}")
            lines.append(f"- **Status**: {check['status']}")
            lines.append("")
    
    # Write markdown
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    parser = argparse.ArgumentParser(description="Generate semantic review decisions")
    parser.add_argument("--recommendations", required=True, help="Path to recommendations.yaml")
    parser.add_argument("--output-decisions", required=True, help="Path to output review-decisions.yaml")
    parser.add_argument("--output-checks", required=True, help="Path to output evidence-checks.yaml")
    parser.add_argument("--render-md", help="Path to output review-note.md")
    parser.add_argument("--feedback-log", default="", help="Path to JSONL feedback log (disabled if empty)")
    args = parser.parse_args()
    
    # Load recommendations
    recommendations = load_recommendations(Path(args.recommendations))
    if not recommendations:
        print(f"Error: Could not load {args.recommendations}")
        return 1
    
    # Generate review decisions
    decisions = generate_review_decisions(recommendations)
    
    # Build decisions output structure
    decisions_data = {
        'domains': decisions['domains'],
        'concepts': decisions['concepts'],
        'rules': decisions['rules'],
        'demand_models': decisions['demand_models'],
        'metadata': {
            'generated_at': datetime.now().astimezone().isoformat(),
            'recommendations_source': 'recommendations.yaml',
            'decision_count': sum(len(decisions[k]) for k in ['domains', 'concepts', 'rules', 'demand_models'])
        }
    }
    
    # Record feedback if log path is set
    if args.feedback_log and _feedback_available:
        _action_to_outcome = {
            'keep': 'accepted',
            'merge': 'accepted',
            'drop': 'rejected',
            'backlog': 'deferred',
            'verify_first': 'needs_evidence',
        }
        collector = FeedbackCollector(Path(args.feedback_log))
        for group in ['domains', 'concepts', 'rules', 'demand_models']:
            item_type = group.rstrip('s')
            for decision in decisions_data[group]:
                outcome = _action_to_outcome.get(decision['final_action'], 'deferred')
                collector.record(
                    stage='review',
                    item_type=item_type,
                    item_id=decision['id'],
                    item_name=decision['name'],
                    outcome=outcome,
                    confidence='',
                    reason=decision.get('final_reason'),
                )

    # Write decisions output
    output_decisions_path = Path(args.output_decisions)
    output_decisions_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_decisions_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(decisions_data, f, sort_keys=False, allow_unicode=True)
    
    # Generate evidence checks (delegate to evidence_check module)
    from semantic.evidence_check import generate_evidence_checks_with_metadata
    checks_data = generate_evidence_checks_with_metadata(recommendations, decisions_data)
    
    # Write checks output
    output_checks_path = Path(args.output_checks)
    output_checks_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_checks_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(checks_data, f, sort_keys=False, allow_unicode=True)
    
    # Render markdown view
    if args.render_md:
        render_review_note_markdown(decisions_data, checks_data, Path(args.render_md))
    
    # Print summary
    print(f"✓ Generated {decisions_data['metadata']['decision_count']} review decisions")
    print(f"  - Domains: {len(decisions['domains'])}")
    print(f"  - Concepts: {len(decisions['concepts'])}")
    print(f"  - Rules: {len(decisions['rules'])}")
    print(f"  - Demand models: {len(decisions['demand_models'])}")
    print(f"✓ Generated {checks_data['metadata']['check_count']} evidence checks")
    print(f"✓ Written to: {output_decisions_path}")
    print(f"✓ Written to: {output_checks_path}")
    if args.render_md:
        print(f"✓ Rendered view: {args.render_md}")

if __name__ == "__main__":
    main()
