"""
Semantic Signals Extraction

Extracts semantic signals from FACT layer inputs.
This is the first stage of the semantic layer.

Supports both full and incremental extraction modes:
- Full mode (default): Extracts all signals from scratch
- Incremental mode (--incremental): Only re-extracts signals from changed files
"""

from pathlib import Path
import argparse
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .change_detector import ChangeDetector
from .signal_cache import SignalCache

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
    """Extract rule/constraint indicator signals"""
    signals = []

    # From canonical: validation modules
    if canonical and 'modules' in canonical:
        modules = canonical['modules']
        validation_modules = [m for m in modules if 'validation' in m.get('name', '').lower() or 'validator' in m.get('name', '').lower()]
        if validation_modules:
            signals.append({
                'signal_type': 'validation_logic',
                'source': 'fact_canonical:modules',
                'evidence': f"{len(validation_modules)} validation modules",
                'confidence': 'high',
                'summary': f"Repository contains {len(validation_modules)} validation modules"
            })

    # From working summary: rules
    if working and 'rules' in working:
        rules = working['rules']
        if rules:
            signals.append({
                'signal_type': 'rule_identification',
                'source': 'fact_working_summary:rules',
                'evidence': f"{len(rules)} rules identified",
                'confidence': 'medium',
                'summary': f"Working summary identifies {len(rules)} rules"
            })

    return signals

def extract_demand_pattern_signals(canonical: Dict[str, Any], working: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract demand pattern indicator signals"""
    signals = []

    # From canonical: change-related modules
    if canonical and 'modules' in canonical:
        modules = canonical['modules']
        change_modules = [m for m in modules if any(keyword in m.get('name', '').lower() for keyword in ['change', 'diff', 'delta', 'update'])]
        if change_modules:
            signals.append({
                'signal_type': 'change_analysis_pattern',
                'source': 'fact_canonical:modules',
                'evidence': f"{len(change_modules)} change-related modules",
                'confidence': 'medium',
                'summary': f"Repository contains {len(change_modules)} change analysis modules"
            })

    # From working summary: demand patterns
    if working and 'demand_patterns' in working:
        patterns = working['demand_patterns']
        if patterns:
            signals.append({
                'signal_type': 'demand_pattern_identification',
                'source': 'fact_working_summary:demand_patterns',
                'evidence': f"{len(patterns)} patterns identified",
                'confidence': 'medium',
                'summary': f"Working summary identifies {len(patterns)} demand patterns"
            })

    return signals

def render_signals_markdown(signals_data: Dict[str, Any], output_path: Path):
    """Render signals as markdown for human review"""
    lines = ["# Semantic Signals\n"]
    lines.append(f"Generated: {signals_data['metadata']['generated_at']}\n")
    lines.append(f"Source: {signals_data['metadata']['fact_source']}\n")
    lines.append(f"Total signals: {signals_data['metadata']['signal_count']}\n")

    for category in ['domain_signals', 'concept_signals', 'rule_signals', 'demand_pattern_signals']:
        signals = signals_data.get(category, [])
        if signals:
            lines.append(f"\n## {category.replace('_', ' ').title()}\n")
            for signal in signals:
                lines.append(f"- **{signal['signal_type']}** ({signal['confidence']})")
                lines.append(f"  - Source: {signal['source']}")
                lines.append(f"  - Evidence: {signal['evidence']}")
                lines.append(f"  - Summary: {signal['summary']}\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def extract_signals_from_files(canonical: Dict[str, Any], working: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract all signal categories from FACT data"""
    return {
        'domain_signals': extract_domain_signals(canonical, working),
        'concept_signals': extract_concept_signals(canonical, working),
        'rule_signals': extract_rule_signals(canonical, working),
        'demand_pattern_signals': extract_demand_pattern_signals(canonical, working)
    }


def run_incremental_extraction(fact_root: Path, cache_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run incremental extraction using change detection and caching.

    Returns:
        Merged signals from cached and newly extracted data
    """
    detector = ChangeDetector(fact_root, cache_dir)
    cache = SignalCache(cache_dir)

    # Detect changes
    changed, added, removed = detector.detect_changes()

    if not changed and not added and not removed:
        print("ℹ No changes detected, using cached signals")
        # Load all cached signals
        canonical_path = fact_root / "fact_canonical_sample.yaml"
        working_path = fact_root / "fact_working_summary_sample.yaml"

        cached_signals = []
        for file_path in [canonical_path, working_path]:
            if file_path.exists():
                file_hash = detector.compute_file_hash(file_path)
                signals = cache.get_cached_signals(file_path, file_hash)
                if signals:
                    cached_signals.append(signals)

        if cached_signals:
            return cache.merge_signals(*cached_signals)

    # Report changes
    if changed:
        print(f"ℹ Changed files: {len(changed)}")
        for f in changed:
            print(f"  - {f.name}")
    if added:
        print(f"ℹ Added files: {len(added)}")
        for f in added:
            print(f"  - {f.name}")
    if removed:
        print(f"ℹ Removed files: {len(removed)}")
        for f in removed:
            print(f"  - {f.name}")
            cache.invalidate_file(f)

    # Extract signals from changed/added files
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)

    if canonical is None:
        print("✗ ERROR: fact_canonical_sample.yaml not found")
        return cache.merge_signals()

    # Extract fresh signals
    fresh_signals = extract_signals_from_files(canonical, working)

    # Cache the results
    canonical_path = fact_root / "fact_canonical_sample.yaml"
    if canonical_path.exists():
        file_hash = detector.compute_file_hash(canonical_path)
        cache.store_signals(canonical_path, file_hash, fresh_signals)

    if working:
        working_path = fact_root / "fact_working_summary_sample.yaml"
        if working_path.exists():
            file_hash = detector.compute_file_hash(working_path)
            cache.store_signals(working_path, file_hash, fresh_signals)

    return fresh_signals


def main():
    parser = argparse.ArgumentParser(description="Extract semantic signals from FACT layer")
    parser.add_argument('--fact-root', type=str, default='docs/semantic-foundation/fact',
                        help='Path to FACT layer root directory')
    parser.add_argument('--output', type=str, default='docs/semantic-foundation/semantic/signals.yaml',
                        help='Output path for signals YAML')
    parser.add_argument('--render-md', type=str,
                        help='Optional: render markdown view to this path')
    parser.add_argument('--incremental', action='store_true',
                        help='Enable incremental extraction (only re-extract changed files)')
    parser.add_argument('--cache-dir', type=str, default='.semantic-cache',
                        help='Cache directory for incremental mode')
    parser.add_argument('--clear-cache', action='store_true',
                        help='Clear cache before extraction')
    args = parser.parse_args()

    fact_root = Path(args.fact_root)
    output_path = Path(args.output)
    cache_dir = Path(args.cache_dir)

    # Clear cache if requested
    if args.clear_cache:
        cache = SignalCache(cache_dir)
        cache.clear_all()
        print("✓ Cache cleared")
        if not args.incremental:
            return 0

    # Run extraction
    if args.incremental:
        print("Running incremental extraction...")
        signals = run_incremental_extraction(fact_root, cache_dir)

        # Build output structure
        signals_data = {
            **signals,
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'fact_source': 'fact_canonical_sample.yaml',
                'extraction_mode': 'incremental',
                'signal_count': sum(len(signals.get(k, [])) for k in ['domain_signals', 'concept_signals', 'rule_signals', 'demand_pattern_signals'])
            }
        }
    else:
        # Full extraction (original behavior)
        print("Running full extraction...")

        # Validate inputs
        canonical = load_fact_canonical(fact_root)
        if canonical is None:
            print("✗ ERROR: fact_canonical_sample.yaml not found")
            print(f"  Expected at: {fact_root / 'fact_canonical_sample.yaml'}")
            return 1

        working = load_fact_working_summary(fact_root)
        if working is None:
            print("⚠ WARNING: fact_working_summary_sample.yaml not found (proceeding without it)")

        # Extract signals
        signals = extract_signals_from_files(canonical, working)

        # Build output structure
        signals_data = {
            **signals,
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'fact_source': 'fact_canonical_sample.yaml',
                'extraction_mode': 'full',
                'signal_count': sum(len(signals.get(k, [])) for k in ['domain_signals', 'concept_signals', 'rule_signals', 'demand_pattern_signals'])
            }
        }

    # Write canonical YAML output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(signals_data, f, sort_keys=False, allow_unicode=True)

    print(f"✓ Extracted {signals_data['metadata']['signal_count']} signals")
    print(f"  - Domain signals: {len(signals_data.get('domain_signals', []))}")
    print(f"  - Concept signals: {len(signals_data.get('concept_signals', []))}")
    print(f"  - Rule signals: {len(signals_data.get('rule_signals', []))}")
    print(f"  - Demand pattern signals: {len(signals_data.get('demand_pattern_signals', []))}")
    print(f"✓ Written to: {output_path}")

    # Render markdown view if requested
    if args.render_md:
        render_path = Path(args.render_md)
        render_signals_markdown(signals_data, render_path)
        print(f"✓ Rendered view: {render_path}")

    return 0

if __name__ == "__main__":
    exit(main())
