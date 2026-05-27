"""Detect Ink/Stitch state desync risks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.rule_engine.decision_engine.normalize_design_report import NormalizedDesignReport

StateRiskType = Literal["STATE_DESYNC", "COMPOUND_PATH_CONFUSION", "CORRUPTED_PATH_STATE"]


@dataclass
class StateRisk:
    type: StateRiskType
    element: str
    confidence: float


def detect_state_risk(report: NormalizedDesignReport) -> list[StateRisk]:
    risks: list[StateRisk] = []

    for element in report.elements:
        if element.has_inkstitch_attrs and element.stitch_type == "stroke":
            risks.append(
                StateRisk(type="STATE_DESYNC", element=element.id, confidence=0.85)
            )

        if element.subpath_count > 1 and element.is_single_stroke_visual:
            risks.append(
                StateRisk(
                    type="COMPOUND_PATH_CONFUSION",
                    element=element.id,
                    confidence=0.7,
                )
            )

        if element.min_segment_length == 0 and element.has_inkstitch_attrs:
            risks.append(
                StateRisk(
                    type="CORRUPTED_PATH_STATE",
                    element=element.id,
                    confidence=0.75,
                )
            )

    return risks
