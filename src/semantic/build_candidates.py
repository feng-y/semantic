"""
Semantic Candidates Synthesis

Synthesizes semantic candidates from signal inputs.
This is the second stage of the semantic layer.
"""

import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def load_signals(signals_path: Path) -> dict[str, Any] | None:
    """Load signals.yaml (primary input)"""
    if not signals_path.exists():
        return None
    with open(signals_path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_stable_id(name: str, type_prefix: str) -> str:
    """Generate a stable ID from name and type prefix"""
    content = f"{type_prefix}:{name}".encode()
    return f"{type_prefix}_{hashlib.sha256(content).hexdigest()[:12]}"

def synthesize_domain_candidates(domain_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Synthesize domain candidates from domain signals"""
    candidates = []

    # Group signals by type
    module_grouping_signals = [s for s in domain_signals if s.get('signal_type') == 'module_grouping']
    domain_proposal_signals = [s for s in domain_signals if s.get('signal_type') == 'domain_proposal']

    # Synthesize from module grouping signals
    for signal in module_grouping_signals:
        candidate = {
            'id': generate_stable_id('repository_structure', 'domain'),
            'name': 'Repository Structure',
            'summary': 'Core repository organization and module structure',
            'boundary': {
                'modules': ['all_modules']
            },
            'source_signal_ids': [signal.get('signal_type', 'unknown')],
            'evidence_refs': [signal.get('evidence', '')],
            'confidence': signal.get('confidence', 'medium')
        }
        candidates.append(candidate)

    # Synthesize from domain proposal signals
    for signal in domain_proposal_signals:
        candidate = {
            'id': generate_stable_id('proposed_domains', 'domain'),
            'name': 'Proposed Domains',
            'summary': signal.get('summary', 'Domain proposals from working summary'),
            'boundary': {
                'modules': ['to_be_determined']
            },
            'source_signal_ids': [signal.get('signal_type', 'unknown')],
            'evidence_refs': [signal.get('evidence', '')],
            'confidence': signal.get('confidence', 'medium')
        }
        candidates.append(candidate)

    return candidates

def synthesize_concept_candidates(concept_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Synthesize concept candidates from concept signals"""
    candidates = []

    # Group signals by type
    entity_signals = [s for s in concept_signals if s.get('signal_type') == 'entity_definition']
    concept_id_signals = [s for s in concept_signals if s.get('signal_type') == 'concept_identification']

    # Synthesize from entity definition signals
    for signal in entity_signals:
        candidate = {
            'id': generate_stable_id('core_entities', 'concept'),
            'name': 'Core Entities',
            'summary': signal.get('summary', 'Core data structures and entities'),
            'relationships': ['domain_models', 'data_structures'],
            'source_signal_ids': [signal.get('signal_type', 'unknown')],
            'evidence_refs': [signal.get('evidence', '')],
            'confidence': signal.get('confidence', 'medium')
        }
        candidates.append(candidate)

    # Synthesize from concept identification signals
    for signal in concept_id_signals:
        candidate = {
            'id': generate_stable_id('identified_concepts', 'concept'),
            'name': 'Identified Concepts',
            'summary': signal.get('summary', 'Concepts identified from working summary'),
            'relationships': ['domain_concepts'],
            'source_signal_ids': [signal.get('signal_type', 'unknown')],
            'evidence_refs': [signal.get('evidence', '')],
            'confidence': signal.get('confidence', 'medium')
        }
        candidates.append(candidate)

    return candidates

def synthesize_rule_candidates(rule_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Synthesize rule candidates from rule signals"""
    candidates = []

    # Synthesize from validation logic signals
    for signal in rule_signals:
        if signal.get('signal_type') == 'validation_logic':
            candidate = {
                'id': generate_stable_id('validation_rules', 'rule'),
                'name': 'Validation Rules',
                'summary': signal.get('summary', 'Validation and constraint enforcement rules'),
                'source_signal_ids': [signal.get('signal_type', 'unknown')],
                'evidence_refs': [signal.get('evidence', '')],
                'confidence': signal.get('confidence', 'medium')
            }
            candidates.append(candidate)

    return candidates

def synthesize_demand_model_candidates(demand_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Synthesize demand model candidates from demand pattern signals"""
    candidates = []

    # Synthesize from change analysis pattern signals
    for signal in demand_signals:
        if signal.get('signal_type') == 'change_analysis_pattern':
            candidate = {
                'id': generate_stable_id('change_analysis', 'demand'),
                'name': 'Change Analysis Model',
                'summary': signal.get('summary', 'Change analysis and impact assessment structure'),
                'source_signal_ids': [signal.get('signal_type', 'unknown')],
                'evidence_refs': [signal.get('evidence', '')],
                'confidence': signal.get('confidence', 'medium')
            }
            candidates.append(candidate)

    return candidates

def render_candidates_markdown(candidates_data: dict[str, Any], output_path: Path):
    """Render candidates as markdown view"""
    lines = ["# Semantic Candidates", ""]
    lines.append(f"**Generated**: {candidates_data.get('metadata', {}).get('generated_at', 'unknown')}")
    lines.append(f"**Source**: {candidates_data.get('metadata', {}).get('signal_source', 'unknown')}")
    lines.append("")

    for group_name in ['domains', 'concepts', 'rules', 'demand_models']:
        candidates = candidates_data.get(group_name, [])
        group_title = group_name.replace('_', ' ').title()
        lines.append(f"## {group_title} ({len(candidates)})")
        lines.append("")

        if not candidates:
            lines.append("*(No candidates synthesized)*")
            lines.append("")
        else:
            for cand in candidates:
                lines.append(f"### {cand.get('name', 'Unnamed')}")
                lines.append(f"- **ID**: {cand.get('id', 'unknown')}")
                lines.append(f"- **Summary**: {cand.get('summary', 'No summary')}")

                if 'boundary' in cand:
                    modules = cand['boundary'].get('modules', [])
                    lines.append(f"- **Boundary**: {', '.join(modules)}")

                if 'relationships' in cand:
                    rels = cand.get('relationships', [])
                    lines.append(f"- **Relationships**: {', '.join(rels)}")

                source_signals = cand.get('source_signal_ids', [])
                lines.append(f"- **Source Signals**: {', '.join(source_signals)}")

                evidence = cand.get('evidence_refs', [])
                if evidence:
                    lines.append(f"- **Evidence**: {evidence[0]}")

                lines.append(f"- **Confidence**: {cand.get('confidence', 'unknown')}")
                lines.append("")

    output_path.write_text('\n'.join(lines), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Build semantic candidates from signals")
    parser.add_argument("--signals", required=True, help="Path to signals.yaml")
    parser.add_argument("--output", required=True, help="Path to output candidates.yaml")
    parser.add_argument("--render-md", help="Path to output candidates.md")
    parser.add_argument("--cache-dir", default=".semantic-cache/stages", help="Cache directory")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache entirely")
    parser.add_argument("--export-json", help="Path to export candidates as JSON")
    parser.add_argument("--export-graphql", help="Path to export candidates as GraphQL schema")
    args = parser.parse_args()

    try:
        from semantic.stage_cache import StageCache
    except ImportError:
        from stage_cache import StageCache

    try:
        from semantic.export import export_graphql, export_json
    except ImportError:
        from export import export_graphql, export_json

    # Load signals
    signals_path = Path(args.signals)
    signals_data = load_signals(signals_path)

    if not signals_data:
        print(f"✗ Failed to load signals from {signals_path}")
        return 1

    # Cache lookup
    cache = StageCache(Path(args.cache_dir)) if not args.no_cache else None
    input_hash = cache.hash_file(signals_path) if cache else ""

    if cache and input_hash:
        cached = cache.get('build_candidates', input_hash)
        if cached is not None:
            print("✓ Using cached candidates (input unchanged)")
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(cached, f, sort_keys=False, allow_unicode=True)
            if args.render_md:
                render_candidates_markdown(cached, Path(args.render_md))
            if args.export_json:
                export_json(cached, Path(args.export_json))
                print(f"✓ JSON export: {args.export_json}")
            if args.export_graphql:
                export_graphql(cached, Path(args.export_graphql))
                print(f"✓ GraphQL schema: {args.export_graphql}")
            return 0

    # Extract signal groups
    domain_signals = signals_data.get('domain_signals', [])
    concept_signals = signals_data.get('concept_signals', [])
    rule_signals = signals_data.get('rule_signals', [])
    demand_signals = signals_data.get('demand_pattern_signals', [])

    # Synthesize candidates
    domains = synthesize_domain_candidates(domain_signals)
    concepts = synthesize_concept_candidates(concept_signals)
    rules = synthesize_rule_candidates(rule_signals)
    demand_models = synthesize_demand_model_candidates(demand_signals)

    # Build output structure
    candidates_data = {
        'domains': domains,
        'concepts': concepts,
        'rules': rules,
        'demand_models': demand_models,
        'metadata': {
            'generated_at': datetime.now().astimezone().isoformat(),
            'signal_source': 'signals.yaml',
            'candidate_count': len(domains) + len(concepts) + len(rules) + len(demand_models)
        }
    }

    # Store in cache
    if cache and input_hash:
        cache.put('build_candidates', input_hash, candidates_data)

    # Write canonical output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(candidates_data, f, sort_keys=False, allow_unicode=True)

    # Render view output
    if args.render_md:
        render_candidates_markdown(candidates_data, Path(args.render_md))

    # Export formats
    if args.export_json:
        export_json(candidates_data, Path(args.export_json))
        print(f"✓ JSON export: {args.export_json}")
    if args.export_graphql:
        export_graphql(candidates_data, Path(args.export_graphql))
        print(f"✓ GraphQL schema: {args.export_graphql}")

    # Print summary
    print(f"✓ Synthesized {candidates_data['metadata']['candidate_count']} candidates")
    print(f"  - Domains: {len(domains)}")
    print(f"  - Concepts: {len(concepts)}")
    print(f"  - Rules: {len(rules)}")
    print(f"  - Demand models: {len(demand_models)}")
    print(f"✓ Written to: {output_path}")
    if args.render_md:
        print(f"✓ Rendered view: {args.render_md}")

if __name__ == "__main__":
    main()
