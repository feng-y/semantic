from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

CandidateType = Literal["domain", "concept", "rule", "demand_model"]
SignalType = Literal["domain", "concept", "rule", "demand_pattern"]
ConfidenceLevel = Literal["high", "medium", "low"]

# ============================================================================
# Signal Models (for semantic-signals capability)
# ============================================================================

class Signal(BaseModel):
    """Base signal model for semantic signal extraction"""
    signal_type: str
    source: str
    evidence: str
    confidence: ConfidenceLevel
    summary: str | None = None

class DomainSignal(Signal):
    """Domain boundary indicator signal"""
    pass

class ConceptSignal(Signal):
    """Concept definition indicator signal"""
    pass

class RuleSignal(Signal):
    """Business rule indicator signal"""
    pass

class DemandPatternSignal(Signal):
    """Demand model structure indicator signal"""
    pass

class SignalsOutput(BaseModel):
    """Complete signals output structure"""
    domain_signals: list[DomainSignal] = Field(default_factory=list)
    concept_signals: list[ConceptSignal] = Field(default_factory=list)
    rule_signals: list[RuleSignal] = Field(default_factory=list)
    demand_pattern_signals: list[DemandPatternSignal] = Field(default_factory=list)

    class Config:
        extra = "allow"

# ============================================================================
# Candidate Models (for semantic-candidates capability)
# ============================================================================

class DomainCandidate(BaseModel):
    """Domain candidate model"""
    id: str
    name: str
    summary: str
    boundary: dict[str, Any]
    source_signal_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel

class ConceptCandidate(BaseModel):
    """Concept candidate model"""
    id: str
    name: str
    summary: str
    relationships: list[str] = Field(default_factory=list)
    source_signal_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel

class RuleCandidate(BaseModel):
    """Rule candidate model"""
    id: str
    name: str
    summary: str
    source_signal_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel

class DemandModelCandidate(BaseModel):
    """Demand model candidate model"""
    id: str
    name: str
    summary: str
    source_signal_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel

class CandidatesOutput(BaseModel):
    """Complete candidates output structure"""
    domains: list[DomainCandidate] = Field(default_factory=list)
    concepts: list[ConceptCandidate] = Field(default_factory=list)
    rules: list[RuleCandidate] = Field(default_factory=list)
    demand_models: list[DemandModelCandidate] = Field(default_factory=list)

    class Config:
        extra = "allow"

# ============================================================================
# Recommendation Models (for later semantic capabilities)
# ============================================================================

class SemanticValidity(str, Enum):
    PASS = "pass"
    FAIL = "fail"

class RecommendationStatus(str, Enum):
    RECOMMEND = "recommend"
    NOT_RECOMMEND = "not_recommend"
    DEFER = "defer"

class RecommendationAction(str, Enum):
    KEEP = "keep"
    MERGE = "merge"
    DROP = "drop"
    BACKLOG = "backlog"
    VERIFY_FIRST = "verify_first"

class RecommendationBody(BaseModel):
    status: RecommendationStatus
    action: RecommendationAction
    target_layer: Literal["final_asset", "candidate_pool"]
    target_asset_type: Literal["domain_map", "concept_map", "rule_map", "demand_model_map", "none"]

class RecommendationItem(BaseModel):
    id: str
    name: str
    candidate_id: str
    semantic_validity: SemanticValidity
    validity_reason: str
    business_score: float = Field(ge=1.0, le=10.0)
    value_score: float = Field(ge=1.0, le=10.0)
    priority: float = Field(ge=1.0, le=10.0)
    recommendation: RecommendationBody
    recommended_reasons: list[str]
    not_recommended_reasons: list[str]
    needs_evidence_check: bool = False
    evidence_gap: str | None = None
    merge_target: str | None = None
    source_candidate_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_priority(self):
        expected = max(self.business_score, self.value_score)
        if round(self.priority, 6) != round(expected, 6):
            raise ValueError("priority must equal max(business_score, value_score)")
        if self.recommendation.action == RecommendationAction.MERGE and not self.merge_target:
            raise ValueError("merge_target required for merge")
        if self.needs_evidence_check and not self.evidence_gap:
            raise ValueError("evidence_gap required when needs_evidence_check is true")
        return self

class DomainRecommendation(RecommendationItem):
    """Domain recommendation model"""
    pass

class ConceptRecommendation(RecommendationItem):
    """Concept recommendation model"""
    pass

class RuleRecommendation(RecommendationItem):
    """Rule recommendation model"""
    pass

class DemandModelRecommendation(RecommendationItem):
    """Demand model recommendation model"""
    pass

class RecommendationsOutput(BaseModel):
    """Complete recommendations output structure"""
    domains: list[DomainRecommendation] = Field(default_factory=list)
    concepts: list[ConceptRecommendation] = Field(default_factory=list)
    rules: list[RuleRecommendation] = Field(default_factory=list)
    demand_models: list[DemandModelRecommendation] = Field(default_factory=list)

    class Config:
        extra = "allow"
