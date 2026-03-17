"""
Multi-format export for semantic pipeline outputs.

Supports:
- JSON: flat export of any semantic YAML artifact
- GraphQL schema: generates a .graphql schema from candidates
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import yaml


def export_json(data: Dict[str, Any], output_path: Path) -> None:
    """Export semantic data as pretty-printed JSON"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def candidates_to_graphql(candidates_data: Dict[str, Any]) -> str:
    """
    Generate a GraphQL schema string from candidates data.

    Domains -> GraphQL types
    Concepts -> GraphQL types with fields
    Rules -> comments on relevant types
    """
    lines = ['# Auto-generated GraphQL schema from semantic candidates', '']

    # Domain types
    domains = candidates_data.get('domain_candidates', [])
    for domain in domains:
        name = _to_pascal(domain.get('name', 'Unknown'))
        desc = domain.get('description', '')
        if desc:
            desc_safe = desc.replace('"""', "'''")
            lines.append('"""')
            lines.append(desc_safe)
            lines.append('"""')
        lines.append(f'type {name} {{')
        lines.append(f'  id: ID!')
        lines.append(f'  name: String!')
        lines.append(f'}}')
        lines.append('')

    # Concept types
    concepts = candidates_data.get('concept_candidates', [])
    for concept in concepts:
        name = _to_pascal(concept.get('name', 'Unknown'))
        desc = concept.get('description', '')
        if desc:
            desc_safe = desc.replace('"""', "'''")
            lines.append('"""')
            lines.append(desc_safe)
            lines.append('"""')
        lines.append(f'type {name} {{')
        lines.append(f'  id: ID!')
        lines.append(f'  name: String!')
        confidence = concept.get('confidence', '')
        if confidence:
            lines.append(f'  # confidence: {confidence}')
        lines.append(f'}}')
        lines.append('')

    # Query type
    if domains or concepts:
        lines.append('type Query {')
        for domain in domains:
            fname = _to_camel(domain.get('name', 'unknown'))
            tname = _to_pascal(domain.get('name', 'Unknown'))
            lines.append(f'  {fname}s: [{tname}!]!')
        for concept in concepts:
            fname = _to_camel(concept.get('name', 'unknown'))
            tname = _to_pascal(concept.get('name', 'Unknown'))
            lines.append(f'  {fname}s: [{tname}!]!')
        lines.append('}')

    return '\n'.join(lines)


def export_graphql(candidates_data: Dict[str, Any], output_path: Path) -> None:
    """Export candidates as a GraphQL schema file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = candidates_to_graphql(candidates_data)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(schema)


def _to_pascal(name: str) -> str:
    """Convert 'my domain name' or 'my_domain_name' to 'MyDomainName'"""
    return ''.join(w.capitalize() for w in name.replace('-', ' ').replace('_', ' ').split())


def _to_camel(name: str) -> str:
    """Convert to camelCase"""
    pascal = _to_pascal(name)
    return pascal[0].lower() + pascal[1:] if pascal else name
