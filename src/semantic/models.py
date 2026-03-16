from __future__ import annotations
from typing import List, Optional, Literal
from enum import Enum
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
    summary: Optional[str] = None

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
    domain_signals: List[DomainSignal] = Field(default_factory=list)
    concept_signals: List[ConceptSignal] = Field(default_factory=list)
    rule_signals: List[RuleSignal] = Field(default_factory=list)
    demand_pattern_signals: List[DemandPatternSignal] = Field(default_factory=list)

    class Config:
        extra = "allow"

# ============================================================================
# Candidate Models (for later semantic capabilities)
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
    type: CandidateType
    semantic_validity: SemanticValidity
    validity_reason: str
    business_score: float = Field(ge=1.0, le=10.0)
    value_score: float = Field(ge=1.0, le=10.0)
    priority: float = Field(ge=1.0, le=10.0)
    recommendation: RecommendationBody
    recommended_reasons: List[str]
    not_recommended_reasons: List[str]
    needs_evidence_check: bool = False
    evidence_gap: Optional[str] = None
    merge_target: Optional[str] = None

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
