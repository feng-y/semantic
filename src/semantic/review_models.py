from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, model_validator

CandidateType = Literal["domain", "concept", "rule", "demand_model"]

class FinalAction(str, Enum):
    KEEP = "keep"
    MERGE = "merge"
    DROP = "drop"
    BACKLOG = "backlog"
    VERIFY_FIRST = "verify_first"

class ReviewDecision(BaseModel):
    candidate_id: str
    candidate_type: CandidateType
    final_action: FinalAction
    final_reason: str
    merge_target: str | None = None

    @model_validator(mode="after")
    def check_merge(self):
        if self.final_action == FinalAction.MERGE and not self.merge_target:
            raise ValueError("merge_target required for merge")
        return self
