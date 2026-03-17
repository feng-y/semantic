"""
Confidence-based auto-accept for semantic recommendations.

High-confidence items are auto-accepted with an audit log entry.
Medium and low confidence items require manual review.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import yaml

CONFIDENCE_LEVELS = {"high": 3, "medium": 2, "low": 1}

@dataclass
class AutoAcceptResult:
    item_id: str
    item_name: str
    confidence: str
    auto_accepted: bool
    reason: str

@dataclass
class AutoAcceptReport:
    accepted: List[AutoAcceptResult] = field(default_factory=list)
    pending_review: List[AutoAcceptResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.accepted) + len(self.pending_review)

    @property
    def acceptance_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return len(self.accepted) / self.total * 100

def should_auto_accept(item: Dict[str, Any], threshold: str = "high") -> tuple[bool, str]:
    """
    Determine if an item should be auto-accepted based on confidence.

    Args:
        item: recommendation or candidate dict with 'confidence' field
        threshold: minimum confidence level for auto-accept ("high" or "medium")

    Returns:
        (should_accept, reason)
    """
    confidence = item.get("confidence", "low")
    threshold_level = CONFIDENCE_LEVELS.get(threshold, 3)
    item_level = CONFIDENCE_LEVELS.get(confidence, 1)

    if item_level >= threshold_level:
        return True, f"Auto-accepted: confidence={confidence} meets threshold={threshold}"
    return False, f"Requires review: confidence={confidence} below threshold={threshold}"

def process_recommendations(
    recommendations: List[Dict[str, Any]],
    threshold: str = "high",
    audit_log_path: Optional[Path] = None,
) -> AutoAcceptReport:
    """
    Process a list of recommendations and auto-accept high-confidence ones.

    Args:
        recommendations: list of recommendation dicts
        threshold: "high" or "medium"
        audit_log_path: if provided, write audit log YAML here

    Returns:
        AutoAcceptReport with accepted and pending_review lists
    """
    report = AutoAcceptReport()
    audit_entries = []

    for item in recommendations:
        item_id = item.get("id", "unknown")
        item_name = item.get("name", "unknown")
        confidence = item.get("confidence", "low")

        accept, reason = should_auto_accept(item, threshold)
        result = AutoAcceptResult(
            item_id=item_id,
            item_name=item_name,
            confidence=confidence,
            auto_accepted=accept,
            reason=reason,
        )

        if accept:
            report.accepted.append(result)
        else:
            report.pending_review.append(result)

        audit_entries.append({
            "item_id": item_id,
            "item_name": item_name,
            "confidence": confidence,
            "auto_accepted": accept,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    if audit_log_path and audit_entries:
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_log_path, "w", encoding="utf-8") as f:
            yaml.dump({"auto_accept_audit": audit_entries}, f, allow_unicode=True)

    return report
