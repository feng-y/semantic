from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, model_validator

class RuleAsset(BaseModel):
    id: str
    name: str
    scope: str
    statement: str
    rule_type: str
    consequence: str
    validation: List[str]
    evidence: List[str]
    business_impact: float = Field(ge=1.0, le=10.0)
    value_impact: float = Field(ge=1.0, le=10.0)

    @model_validator(mode="after")
    def has_validation(self):
        if not self.validation:
            raise ValueError("RuleAsset must contain validation")
        return self
