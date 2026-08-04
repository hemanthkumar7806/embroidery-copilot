"""Types for the embroidery rule engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

Category = Literal[
    "geometry",
    "parameters",
    "structure",
    "routing",
    "export",
    "physical",
    "performance",
]

Severity = Literal["critical", "high", "medium", "low"]

DecisionStatus = Literal["SAFE_TO_TEST", "CAUTION", "FIX_BEFORE_STITCH"]

FailureType = Literal["geometry", "structure", "parameter", "routing", "unknown"]

ConfidenceTier = Literal["low", "medium", "high", "certain"]

# Capability tier: how much the platform can safely automate a fix.
#   auto_fix       -> deterministic live edit (attribute/order), one-click, undoable (🟢)
#   guided         -> AI knows the fix but can't safely apply it live; guide + verify (🟡)
#   recommendation -> design-level/subjective; reasoning only, no automation (🔵)
# Default is the safest tier: never auto-apply something not explicitly marked.
Capability = Literal["auto_fix", "guided", "recommendation"]


@dataclass
class DesignReport:
    meta: dict[str, Any] | None = None
    geometry: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] = field(default_factory=dict)
    routing: dict[str, Any] = field(default_factory=dict)
    export: dict[str, Any] = field(default_factory=dict)
    physical: dict[str, Any] = field(default_factory=dict)
    elements: list[dict[str, Any]] | None = None


@dataclass
class Issue:
    id: str
    category: Category
    severity: Severity
    confidence: float
    title: str
    detail: str
    source: str
    suggested_action: str
    capability: Capability = "recommendation"
    adjustment_note: str | None = None
    group: str | None = None
    evidence: dict[str, Any] | None = None


@dataclass
class Rule:
    id: str
    category: Category
    severity: Severity
    confidence: float
    fields: list[str]
    title: str
    source: str
    suggested_action: str
    check: Callable[[DesignReport], bool]
    detail: Callable[[DesignReport], str]
    skip_when: Callable[[DesignReport], bool] | None = None
    group: str | None = None
    evidence: Callable[[DesignReport], dict[str, Any]] | None = None
    # Capability tier this rule's issue belongs to (see Capability). Defaults to the
    # safest tier; only rules with a deterministic fix should opt into auto_fix.
    capability: Capability = "recommendation"


@dataclass
class RuleEngineOptions:
    min_confidence: float = 0.5
    dry_run: bool = False


@dataclass
class DryRunEvaluation:
    rule_id: str
    fired: bool
    skipped: bool
    meets_confidence_threshold: bool
    confidence: float


@dataclass
class GapReport:
    unchecked_fields: list[str]
    low_confidence_rules: list[str]
    missing_physical_data: list[str]
    soft_rules: list[str]
    skipped_rules: list[str]


@dataclass
class EngineDecision:
    status: DecisionStatus
    reason: str


@dataclass
class ClassificationResult:
    type: FailureType
    confidence: ConfidenceTier
    reason: str


@dataclass
class RootCause:
    id: str
    cause: str
    action: str
    confidence: ConfidenceTier


@dataclass
class Decision:
    main_problem: str
    next_action: str
    explanation: str


@dataclass
class RuleEngineResult:
    issues: list[Issue]
    context_gap_issues: list[Issue]
    classification: ClassificationResult
    root_cause: RootCause | None
    detailed_decision: Decision
    summary: dict[str, Any]
    gaps: GapReport
    decision: EngineDecision
    dry_run_evaluations: list[DryRunEvaluation] | None = None
