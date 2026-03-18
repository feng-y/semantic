from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class DevelopmentType(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    MIGRATION = "migration"
    OPTIMIZE = "optimize"


class ChangeRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUPPORTING = "supporting"


class SemanticValue(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RawCommit:
    commit_id: str
    author: str
    timestamp: str
    files: List[str]
    diff_chunks: List[str]
    related_tests: List[str] = field(default_factory=list)


@dataclass
class ChangeGroup:
    group_id: str
    theme: str
    files: List[str]
    role: ChangeRole
    diff_chunks: List[str] = field(default_factory=list)


@dataclass
class BugfixEvidence:
    weak: List[str] = field(default_factory=list)
    medium: List[str] = field(default_factory=list)
    strong: List[str] = field(default_factory=list)


@dataclass
class SplitHints:
    too_many_files: bool = False
    too_many_diff_themes: bool = False
    mixed_feature_and_bugfix: bool = False
    unrelated_objects_detected: bool = False


@dataclass
class SemanticCaseInput:
    case_id: str
    commit_id: str
    module: str
    files: List[str]
    diff_chunks: List[str]
    domain: str = ""  # Optional, defaults to module if not provided (P0 spec line 238)
    related_tests: List[str] = field(default_factory=list)
    bugfix_evidence: BugfixEvidence = field(default_factory=BugfixEvidence)
    split_hints: SplitHints = field(default_factory=SplitHints)
    semantic_value: str = "medium"  # high/medium/low


@dataclass
class SplitSuggestion:
    needs_split: bool = False
    split_reasons: List[str] = field(default_factory=list)


@dataclass
class SemanticCaseOutput:
    case_id: str
    commit_id: str
    module: str
    commit_log: str
    issue_text: str
    development_type: DevelopmentType
    domain: str = ""  # Optional, defaults to module if not provided (P0 spec line 250)
    rules: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    split_suggestion: SplitSuggestion = field(default_factory=SplitSuggestion)
    semantic_value: str = "medium"
    dedup_key: str = ""
    pattern_id: str = ""


@dataclass
class CaseRecord:
    """Matches the case dict written to cases.jsonl (semantic_case_output_to_dict)."""
    case_id: str
    commit_id: str
    module: str
    commit_log: str
    issue_text: str
    development_type: str
    domain: str = ""
    rules: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    split_suggestion: Dict[str, Any] = field(default_factory=dict)
    semantic_value: str = "medium"
    dedup_key: str = ""
    pattern_id: str = ""


@dataclass
class DomainPatternStat:
    pattern_count: int
    status: str
    action: str


@dataclass
class HighFrequencyPattern:
    pattern_id: str
    domain: str
    count: int
    representative_issue_text: str


@dataclass
class ExportSummary:
    """Matches the dict returned by generate_statistics()."""
    total_cases: int
    unique_cases: int
    duplicate_cases: int
    duplicate_groups: int
    valid_cases: int
    invalid_cases: int
    low_value_cases: int
    validation_pass_rate: float
    development_type_distribution: Dict[str, int]
    bugfix_count: int
    bugfix_ratio: float
    needs_split_count: int
    needs_split_ratio: float
    pattern_count: int
    domain_pattern_stats: Dict[str, Any] = field(default_factory=dict)
    high_frequency_patterns: List[Any] = field(default_factory=list)
    invalid_reason_top_n: Dict[str, int] = field(default_factory=dict)
