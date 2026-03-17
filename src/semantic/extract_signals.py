"""
Semantic Signals Extraction

Extracts semantic signals from FACT layer inputs.
This is the first stage of the semantic layer.
"""

from pathlib import Path
import argparse
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

def load_fact_canonical(fact_root: Path) -> Optional[Dict[str, Any]]:
    """Load FACT canonical YAML (primary hard input)"""
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    if not canonical_path.exists():
        return None
    with open(canonical_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_fact_working_summary(fact_root: Path) -> Optional[Dict[str, Any]]:
    """Load FACT working summary YAML (auxiliary soft input)"""
    working_path = fact_root / "fact_working_summary_sample.yaml"
    if not working_path.exists():
        return None
    with open(working_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def extract_domain_signals(canonical: Dict[str, Any], working: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract domain boundary indicator signals"""
    signals = []

    # From canonical: module grouping patterns
    if canonical and 'modules' in canonical:
        modules = canonical['modules']
        if len(modules) > 0:
            signals.append({
                'signal_type': 'module_grouping',
                'source': 'fact_canonical:modules',
                'evidence': f"{len(modules)} modules observed",
                'confidence': 'high',
                'summary': f"Repository contains {len(modules)} distinct modules"
            })

    # From working summary: domain proposals
    if working and 'domain_proposals' in working:
        proposals = working['domain_proposals']
        if proposals:
            signals.append({
                'signal_type': 'domain_proposal',
                'source': 'fact_working_summary:domain_proposals',
                'evidence': f"{len(proposals)} domain proposals",
                'confidence': 'medium',
                'summary': f"Working summary proposes {len(proposals)} domains"
            })

    return signals

def extract_concept_signals(canonical: Dict[str, Any], working: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract concept definition indicator signals"""
    signals = []

    # From canonical: core entities
    if canonical and 'core_entities' in canonical:
        entities = canonical['core_entities']
        if len(entities) > 0:
            signals.append({
                'signal_type': 'entity_definition',
                'source': 'fact_canonical:core_entities',
                'evidence': f"{len(entities)} entities observed",
                'confidence': 'high',
                'summary': f"Repository defines {len(entities)} core entities"
            })

    # From working summary: concepts
    if working and 'concepts' in working:
        concepts = working['concepts']
        if concepts:
            signals.append({
                'signal_type': 'concept_identification',
                'source': 'fact_working_summary:concepts',
                'evidence': f"{len(concepts)} concepts identified",
                'confidence': 'medium',
                'summary': f"Working summary identifies {len(concepts)} concepts"
            })

    return signals

def extract_rule_signals(canonical: Dict[str, Any], working: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract business rule indicator signals"""
    signals = []

    # From canonical: validation patterns in modules
    if canonical and 'modules' in canonical:
        validation_modules = [m for m in canonical['modules'] if 'validation' in m.get('name', '').lower()]
        if validation_modules:
            signals.append({
                'signal_type': 'validation_logic',
                'source': 'fact_canonical:modules',
                'evidence': f"{len(validation_modules)} validation modules",
                'confidence': 'high',
                'summary': f"Repository contains {len(validation_modules)} validation modules"
            })

    return signals

def extract_demand_pattern_signals(canonical: Dict[str, Any], working: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract demand model structure indicator signals"""
    signals = []

    # From canonical: change analysis patterns
    if canonical and 'modules' in canonical:
        change_modules = [m for m in canonical['modules'] if 'change' in m.get('name', '').lower()]
        if change_modules:
            signals.append({
                'signal_type': 'change_analysis_pattern',
                'source': 'fact_canonical:modules',
                'evidence': f"{len(change_modules)} change-related modules",
                'confidence': 'medium',
                'summary': f"Repository contains {len(change_modules)} change analysis modules"
            })

    return signals

def render_signals_markdown(signals_data: Dict[str, Any], output_path: Path):
    """Render signals as markdown view"""
    lines = ["# Semantic Signals", ""]
    lines.append(f"**Generated**: {signals_data.get('metadata', {}).get('generated_at', 'unknown')}")
    lines.append(f"**Source**: {signals_data.get('metadata', {}).get('fact_source', 'unknown')}")
    lines.append("")

    for group_name in ['domain_signals', 'concept_signals', 'rule_signals', 'demand_pattern_signals']:
        signals = signals_data.get(group_name, [])
        group_title = group_name.replace('_', ' ').title()
        lines.append(f"## {group_title} ({len(signals)})")
        lines.append("")

        if not signals:
            lines.append("*(No signals extracted)*")
            lines.append("")
        else:
            for sig in signals:
                lines.append(f"### {sig.get('signal_type', 'unknown')}")
                lines.append(f"- **Source**: {sig.get('source', 'unknown')}")
                lines.append(f"- **Evidence**: {sig.get('evidence', 'none')}")
                lines.append(f"- **Confidence**: {sig.get('confidence', 'unknown')}")
                if sig.get('summary'):
                    lines.append(f"- **Summary**: {sig.get('summary')}")
                lines.append("")

    output_path.write_text('\n'.join(lines), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Extract semantic signals from FACT inputs")
    parser.add_argument("--fact-root", required=True, help="Path to FACT inputs directory")
    parser.add_argument("--output", required=True, help="Path to output signals.yaml")
    parser.add_argument("--render-md", help="Path to output signals.md (optional)")
    args = parser.parse_args()

    fact_root = Path(args.fact_root)
    output_path = Path(args.output)

    # Load FACT inputs
    canonical = load_fact_canonical(fact_root)
    if not canonical:
        print("ERROR: fact_canonical_sample.yaml not found (required primary input)")
        return 1

    working = load_fact_working_summary(fact_root)
    if not working:
        print("WARNING: fact_working_summary_sample.yaml not found (auxiliary input missing)")

    # Extract signals
    domain_signals = extract_domain_signals(canonical, working)
    concept_signals = extract_concept_signals(canonical, working)
    rule_signals = extract_rule_signals(canonical, working)
    demand_pattern_signals = extract_demand_pattern_signals(canonical, working)

    # Build output structure
    signals_data = {
        'domain_signals': domain_signals,
        'concept_signals': concept_signals,
        'rule_signals': rule_signals,
        'demand_pattern_signals': demand_pattern_signals,
        'metadata': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'fact_source': 'fact_canonical_sample.yaml',
            'signal_count': len(domain_signals) + len(concept_signals) + len(rule_signals) + len(demand_pattern_signals)
        }
    }

    # Write canonical YAML output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(signals_data, f, sort_keys=False, allow_unicode=True)

    print(f"✓ Extracted {signals_data['metadata']['signal_count']} signals")
    print(f"  - Domain signals: {len(domain_signals)}")
    print(f"  - Concept signals: {len(concept_signals)}")
    print(f"  - Rule signals: {len(rule_signals)}")
    print(f"  - Demand pattern signals: {len(demand_pattern_signals)}")
    print(f"✓ Written to: {output_path}")

    # Render markdown view if requested
    if args.render_md:
        render_path = Path(args.render_md)
        render_signals_markdown(signals_data, render_path)
        print(f"✓ Rendered view: {render_path}")

    return 0

if __name__ == "__main__":
    exit(main())
