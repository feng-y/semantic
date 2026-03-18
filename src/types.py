from dataclasses import dataclass, field
from typing import List, Optional
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
    related_tests: List[str] = field(default_factory=list)
    bugfix_evidence: BugfixEvidence = field(default_factory=BugfixEvidence)
    split_hints: SplitHints = field(default_factory=SplitHints)


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
    rules: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    split_suggestion: SplitSuggestion = field(default_factory=SplitSuggestion)
