"""
Tests for multi-format export (JSON, GraphQL schema)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.export import (
    export_json,
    export_graphql,
    candidates_to_graphql,
    _to_pascal,
    _to_camel,
)


def test_export_json_creates_file(tmp_path):
    data = {"key": "value", "count": 42}
    out = tmp_path / "out.json"
    export_json(data, out)
    assert out.exists()


def test_export_json_roundtrip(tmp_path):
    data = {"domains": [{"name": "Foo", "id": "d_001"}], "metadata": {"count": 1}}
    out = tmp_path / "out.json"
    export_json(data, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == data


def test_candidates_to_graphql_domains():
    data = {
        "domain_candidates": [
            {"name": "order management", "description": "Handles orders"}
        ]
    }
    schema = candidates_to_graphql(data)
    assert "type OrderManagement {" in schema
    assert "id: ID!" in schema
    assert "name: String!" in schema


def test_candidates_to_graphql_concepts():
    data = {
        "concept_candidates": [
            {"name": "line item", "confidence": "high"}
        ]
    }
    schema = candidates_to_graphql(data)
    assert "type LineItem {" in schema
    assert "id: ID!" in schema
    assert "name: String!" in schema
    assert "# confidence: high" in schema


def test_candidates_to_graphql_query_type():
    data = {
        "domain_candidates": [{"name": "inventory"}],
        "concept_candidates": [{"name": "product"}],
    }
    schema = candidates_to_graphql(data)
    assert "type Query {" in schema
    assert "inventorys: [Inventory!]!" in schema
    assert "products: [Product!]!" in schema


def test_candidates_to_graphql_empty():
    schema = candidates_to_graphql({})
    assert schema.startswith("# Auto-generated GraphQL schema from semantic candidates")
    assert "type Query" not in schema


def test_export_graphql_creates_file(tmp_path):
    data = {
        "domain_candidates": [{"name": "billing"}]
    }
    out = tmp_path / "schema.graphql"
    export_graphql(data, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "type Billing {" in content


def test_to_pascal():
    assert _to_pascal("my domain name") == "MyDomainName"
    assert _to_pascal("my_domain_name") == "MyDomainName"
    assert _to_pascal("my-domain-name") == "MyDomainName"
    assert _to_pascal("single") == "Single"
    assert _to_pascal("") == ""


def test_to_camel():
    assert _to_camel("my domain name") == "myDomainName"
    assert _to_camel("my_domain_name") == "myDomainName"
    assert _to_camel("Single") == "single"
    assert _to_camel("") == ""
