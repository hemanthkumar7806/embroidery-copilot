"""Score and rank root causes from rules, state risks, and mismatches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.rule_engine.decision_engine.mismatch import MismatchIssue
from app.services.rule_engine.decision_engine.state_risk import StateRisk
from app.services.rule_engine.types import Issue

CauseSource = Literal["rule", "state", "mismatch"]


@dataclass
class ScoredCause:
    type: str
    score: float
    confidence: float
    source: CauseSource
    rule_issue: Issue | None = None
    element: str | None = None
    elements: list[str] | None = None


def score_causes(
    *,
    rule_issues: list[Issue],
    state_risks: list[StateRisk],
    mismatch_issues: list[MismatchIssue],
) -> list[ScoredCause]:
    all_causes: list[ScoredCause] = []

    for issue in rule_issues:
        confidence = issue.confidence or 0.6
        all_causes.append(
            ScoredCause(
                type=issue.id,
                score=confidence,
                confidence=confidence,
                source="rule",
                rule_issue=issue,
            )
        )

    for risk in state_risks:
        confidence = risk.confidence or 0.7
        all_causes.append(
            ScoredCause(
                type=risk.type,
                score=confidence + 0.05,
                confidence=confidence,
                source="state",
                element=risk.element,
            )
        )

    for mismatch in mismatch_issues:
        confidence = mismatch.confidence or 0.8
        all_causes.append(
            ScoredCause(
                type=mismatch.type,
                score=confidence + 0.1,
                confidence=confidence,
                source="mismatch",
                elements=mismatch.elements,
            )
        )

    return sorted(all_causes, key=lambda cause: cause.score, reverse=True)
