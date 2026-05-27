"""Design complexity and density heuristics."""

from __future__ import annotations

from app.services.rule_engine.types import DesignReport


def compute_complexity_score(report: DesignReport) -> float:
    node_factor = report.geometry.get("node_count", 0) / 1000.0
    path_factor = report.geometry.get("path_count", 0) / 200.0
    element_factor = report.structure.get("element_count", 0) / 100.0
    return node_factor * 0.5 + path_factor * 0.3 + element_factor * 0.2


def is_fragmented(report: DesignReport) -> bool:
    return (
        report.structure.get("element_count", 0) > 100
        and report.geometry.get("path_count", 0) > 200
    )


def has_running_density_risk(report: DesignReport) -> bool:
    stitch = report.parameters.get("stitch_length_mm")
    if stitch is None or stitch > 1.5:
        return False

    avg_seg = report.geometry.get("avg_segment_length_mm")
    node_count = report.geometry.get("node_count", 0)
    if avg_seg is None:
        return node_count > 80
    return node_count > 80 or avg_seg < 1.5
