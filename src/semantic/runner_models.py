from __future__ import annotations
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel

class RunState(BaseModel):
    mode: Literal["next", "all"]
    current_stage: Optional[str] = None
    completed_stages: List[str] = []
    artifacts: Dict[str, str] = {}
    errors: List[dict] = []
    warnings: List[str] = []
    blocked_reason: Optional[str] = None
