"""
Feedback loop: records accept/reject outcomes for signals, candidates, and recommendations.
Persists to a JSONL append log for later analysis.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json

@dataclass
class FeedbackEntry:
    timestamp: str
    stage: str          # 'review' | 'finalize' | 'auto_accept'
    item_type: str      # 'domain' | 'concept' | 'rule' | 'demand_model'
    item_id: str
    item_name: str
    outcome: str        # 'accepted' | 'rejected' | 'deferred' | 'needs_evidence'
    confidence: str     # original confidence level
    reason: Optional[str] = None

class FeedbackCollector:
    """Appends feedback entries to a JSONL log file"""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, stage: str, item_type: str, item_id: str,
               item_name: str, outcome: str, confidence: str,
               reason: Optional[str] = None) -> FeedbackEntry:
        entry = FeedbackEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage=stage,
            item_type=item_type,
            item_id=item_id,
            item_name=item_name,
            outcome=outcome,
            confidence=confidence,
            reason=reason,
        )
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
        return entry

    def load_all(self) -> List[FeedbackEntry]:
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(FeedbackEntry(**json.loads(line)))
                    except (json.JSONDecodeError, TypeError):
                        continue
        return entries

    def summary(self) -> Dict[str, Any]:
        entries = self.load_all()
        if not entries:
            return {'total': 0, 'accepted': 0, 'rejected': 0, 'acceptance_rate': 0.0}
        accepted = sum(1 for e in entries if e.outcome == 'accepted')
        rejected = sum(1 for e in entries if e.outcome == 'rejected')
        by_confidence: Dict[str, Dict[str, int]] = {}
        for e in entries:
            c = e.confidence
            if c not in by_confidence:
                by_confidence[c] = {'accepted': 0, 'rejected': 0, 'other': 0}
            if e.outcome == 'accepted':
                by_confidence[c]['accepted'] += 1
            elif e.outcome == 'rejected':
                by_confidence[c]['rejected'] += 1
            else:
                by_confidence[c]['other'] += 1
        return {
            'total': len(entries),
            'accepted': accepted,
            'rejected': rejected,
            'acceptance_rate': (accepted / len(entries) * 100) if entries else 0.0,
            'by_confidence': by_confidence,
        }
