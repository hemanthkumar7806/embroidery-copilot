"""Detect inconsistent behavior across similar elements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.rule_engine.decision_engine.normalize_design_report import (
    DesignElement,
    NormalizedDesignReport,
)

MismatchType = Literal["INCONSISTENT_BEHAVIOR"]


@dataclass
class MismatchIssue:
    type: MismatchType
    elements: list[str]
    confidence: float


def _group_by_similarity(elements: list[DesignElement]) -> list[list[DesignElement]]:
    groups: dict[str, list[DesignElement]] = {}
    for element in elements:
        key = f"{element.node_count}_{round(element.min_segment_length)}"
        groups.setdefault(key, []).append(element)
    return list(groups.values())


def detect_mismatch(report: NormalizedDesignReport) -> list[MismatchIssue]:
    issues: list[MismatchIssue] = []
    for group in _group_by_similarity(report.elements):
        stitch_types = {element.stitch_type for element in group}
        if len(stitch_types) > 1 and len(group) > 1:
            issues.append(
                MismatchIssue(
                    type="INCONSISTENT_BEHAVIOR",
                    elements=[element.id for element in group],
                    confidence=0.9,
                )
            )
    return issues
