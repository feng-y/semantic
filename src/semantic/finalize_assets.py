"""Semantic Finalization - Generate final semantic asset maps"""
from pathlib import Path
import argparse, yaml, hashlib
from typing import Dict, List, Any
from datetime import datetime

def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def check_unresolved_verifications(checks: Dict) -> List[str]:
    """Return list of unresolved verify_first items"""
    unresolved = []
    for check in checks.get('evidence_checks', []):
        if check.get('status') == 'pending':
            unresolved.append(check['target_name'])
    return unresolved

def generate_final_id(name: str, type_prefix: str) -> str:
    return f"{type_prefix}_{hashlib.md5(name.encode()).hexdigest()[:8]}"

def finalize_domain(decision: Dict) -> Dict:
    return {
        'id': generate_final_id(decision['name'], 'domain'),
        'name': decision['name'],
        'summary': f"Domain: {decision['name']}",
        'evidence_refs': decision.get('evidence_refs', []),
        'source_decision_id': decision['id']
    }

def finalize_concept(decision: Dict) -> Dict:
    return {
        'id': generate_final_id(decision['name'], 'concept'),
        'name': decision['name'],
        'summary': f"Concept: {decision['name']}",
        'boundary': {},
        'evidence_refs': decision.get('evidence_refs', []),
        'source_decision_id': decision['id']
    }

def finalize_rule(decision: Dict) -> Dict:
    return {
        'id': generate_final_id(decision['name'], 'rule'),
        'name': decision['name'],
        'statement': f"Rule: {decision['name']}",
        'validation': {'type': 'semantic', 'status': 'active'},
        'evidence_refs': decision.get('evidence_refs', []),
        'source_decision_id': decision['id']
    }

def finalize_demand_model(decision: Dict) -> Dict:
    return {
        'id': generate_final_id(decision['name'], 'demand_model'),
        'name': decision['name'],
        'summary': f"Demand Model: {decision['name']}",
        'related_domains': [],
        'related_concepts': [],
        'related_rules': [],
        'evidence_refs': decision.get('evidence_refs', []),
        'source_decision_id': decision['id']
    }

def build_change_log(decisions: Dict) -> Dict:
    added, merged, dropped, deferred = [], [], [], []
    
    for group in ['domains', 'concepts', 'rules', 'demand_models']:
        for dec in decisions.get(group, []):
            action = dec['final_action']
            entry = {'name': dec['name'], 'type': group.rstrip('s'), 'reason': dec['final_reason']}
            if action == 'keep': added.append(entry)
            elif action == 'merge': merged.append({**entry, 'target': dec.get('merge_target')})
            elif action == 'drop': dropped.append(entry)
            elif action in ['backlog', 'verify_first']: deferred.append(entry)
    
    return {
        'added': added, 'merged': merged, 'dropped': dropped, 'deferred': deferred,
        'metadata': {'generated_at': datetime.now().isoformat(), 'total_changes': len(added)+len(merged)+len(dropped)+len(deferred)}
    }

def render_markdown(data: Dict, title: str, output_path: Path):
    lines = [f"# {title}\n", f"**Generated**: {data.get('metadata', {}).get('generated_at', 'N/A')}\n"]
    
    items_key = 'domains' if 'domains' in data else 'concepts' if 'concepts' in data else 'rules' if 'rules' in data else 'demand_models' if 'demand_models' in data else None
    if items_key:
        lines.append(f"**Total**: {len(data.get(items_key, []))}\n")
        for item in data.get(items_key, []):
            lines.append(f"## {item['name']}\n- **ID**: `{item['id']}`\n")
    
    output_path.write_text('\n'.join(lines))

def main():
    parser = argparse.ArgumentParser(description="Finalize semantic assets")
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--checks", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    decisions = load_yaml(Path(args.decisions))
    checks = load_yaml(Path(args.checks))

    # Check for unresolved verifications
    unresolved = check_unresolved_verifications(checks)
    if unresolved:
        print(f"⚠ Unresolved verify_first items: {', '.join(unresolved)}")
        print("Finalization blocked. Resolve evidence checks first.")
        import sys
        sys.exit(1)  # Exit with error code

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build final assets - include both 'keep' and 'merge' actions
    domain_map = {'domains': [finalize_domain(d) for d in decisions.get('domains', []) if d['final_action'] in ('keep', 'merge')], 'metadata': {'generated_at': datetime.now().isoformat()}}
    concept_map = {'concepts': [finalize_concept(c) for c in decisions.get('concepts', []) if c['final_action'] in ('keep', 'merge')], 'metadata': {'generated_at': datetime.now().isoformat()}}
    rule_map = {'rules': [finalize_rule(r) for r in decisions.get('rules', []) if r['final_action'] in ('keep', 'merge')], 'metadata': {'generated_at': datetime.now().isoformat()}}
    demand_model_map = {'demand_models': [finalize_demand_model(dm) for dm in decisions.get('demand_models', []) if dm['final_action'] in ('keep', 'merge')], 'metadata': {'generated_at': datetime.now().isoformat()}}
    change_log = build_change_log(decisions)

    # Write outputs
    for name, data in [('domain-map', domain_map), ('concept-map', concept_map), ('rule-map', rule_map), ('demand-model-map', demand_model_map), ('change-log', change_log)]:
        yaml_path = output_dir / f"{name}.yaml"
        md_path = output_dir / f"{name}.md"
        with open(yaml_path, 'w') as f:
            yaml.safe_dump(data, f, sort_keys=False)
        render_markdown(data, name.replace('-', ' ').title(), md_path)
        print(f"✓ {yaml_path}")

    print(f"✓ Finalized {len(domain_map['domains'])} domains, {len(concept_map['concepts'])} concepts, {len(rule_map['rules'])} rules, {len(demand_model_map['demand_models'])} demand models")

if __name__ == "__main__":
    main()
