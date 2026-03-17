"""Demand Card V1 models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

DevelopmentType = Literal["feature", "bugfix", "refactor", "migration", "optimize"]


@dataclass(slots=True)
class RequestSource:
    issue_id: str
    issue_text: str


@dataclass(slots=True)
class SemanticMapping:
    domains: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Uncertainties:
    open_questions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DemandCardBody:
    request_source: RequestSource
    semantic_mapping: SemanticMapping
    development_type: DevelopmentType
    uncertainties: Uncertainties


@dataclass(slots=True)
class DemandCard:
    demand_card: DemandCardBody

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
