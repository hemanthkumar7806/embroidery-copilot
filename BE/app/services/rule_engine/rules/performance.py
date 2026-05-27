"""Performance and complexity rules."""

from __future__ import annotations

from typing import Any

from app.services.rule_engine.metrics import compute_complexity_score, is_fragmented
from app.services.rule_engine.types import DesignReport, Rule


def density_interaction_risk_fires(report: DesignReport) -> bool:
    return (
        report.parameters.get("stitch_length_mm") is not None
        and report.parameters.get("stitch_length_mm") <= 1.5
        and report.geometry.get("node_count", 0) > 120
        and report.structure.get("element_count", 0) > 1
    )


def _insufficient_data_null_count(report: DesignReport) -> dict[str, Any]:
    fields: list[tuple[str, Any]] = [
        ("parameters.row_spacing_mm", report.parameters.get("row_spacing_mm")),
        ("routing.estimated_stitch_count", report.routing.get("estimated_stitch_count")),
        ("physical.fabric_type", report.physical.get("fabric_type")),
        ("geometry.bounding_box", report.geometry.get("bounding_box")),
    ]
    null_fields = [name for name, value in fields if value is None]
    return {"count": len(null_fields), "null_fields": null_fields}


performance_rules: list[Rule] = [
    Rule(
        id="simulation_freeze_risk",
        category="performance",
        group="performance",
        severity="critical",
        confidence=0.85,
        fields=["geometry.node_count", "geometry.path_count", "structure.element_count"],
        title="Simulation freeze risk",
        source="rule-engine/heuristics: complexity vs path fragmentation",
        suggested_action="Simplify paths, reduce node count, and avoid excessive fragmentation",
        check=lambda report: (
            compute_complexity_score(report) > 0.8
            or (
                report.geometry.get("node_count", 0) > 800
                and report.geometry.get("path_count", 0) > 200
            )
        ),
        detail=lambda report: (
            f"High simulator load risk: node_count={report.geometry.get('node_count')}, "
            f"path_count={report.geometry.get('path_count')}, "
            f"complexity_score={compute_complexity_score(report):.3f}."
        ),
        evidence=lambda report: {
            "node_count": report.geometry.get("node_count"),
            "path_count": report.geometry.get("path_count"),
            "element_count": report.structure.get("element_count"),
            "complexity_score": compute_complexity_score(report),
        },
    ),
    Rule(
        id="high_complexity_design",
        category="performance",
        group="performance",
        severity="high",
        confidence=0.8,
        fields=["geometry.node_count", "geometry.path_count", "structure.element_count"],
        title="High design complexity",
        source="rule-engine/heuristics: weighted complexity score",
        suggested_action="Simplify paths or reduce element count before simulation",
        check=lambda report: compute_complexity_score(report) > 0.6,
        detail=lambda report: (
            f"Design complexity score is {compute_complexity_score(report):.3f}, "
            "which may slow simulation"
        ),
    ),
    Rule(
        id="excessive_fragmentation",
        category="performance",
        group="performance",
        severity="medium",
        confidence=0.75,
        fields=["structure.element_count", "geometry.path_count"],
        title="Excessive fragmentation",
        source="rule-engine/heuristics: many elements and paths",
        suggested_action="Merge paths or reduce object count where possible",
        check=is_fragmented,
        detail=lambda _report: (
            "Design contains many small elements and paths, increasing computation cost"
        ),
    ),
    Rule(
        id="density_interaction_risk",
        category="performance",
        group="interaction",
        severity="high",
        confidence=0.8,
        fields=["parameters.stitch_length_mm", "geometry.node_count", "structure.element_count"],
        title="Density interaction risk",
        source="rule-engine/heuristics: stitch length × node density × elements",
        suggested_action="Increase stitch length OR reduce path complexity",
        check=density_interaction_risk_fires,
        detail=lambda _report: (
            "Combination of short stitch length and high node count increases "
            "needle penetration density significantly"
        ),
        evidence=lambda report: {
            "stitch_length_mm": report.parameters.get("stitch_length_mm"),
            "node_count": report.geometry.get("node_count"),
            "element_count": report.structure.get("element_count"),
        },
    ),
    Rule(
        id="insufficient_data_risk",
        category="performance",
        group="gaps",
        severity="low",
        confidence=0.6,
        fields=[
            "parameters.row_spacing_mm",
            "routing.estimated_stitch_count",
            "physical.fabric_type",
            "geometry.bounding_box",
        ],
        title="Insufficient data for full analysis",
        source="rule-engine/gaps: key report fields null",
        suggested_action="Provide missing measurements in the design pipeline",
        check=lambda report: _insufficient_data_null_count(report)["count"] > 2,
        detail=lambda report: (
            "Several critical fields are missing "
            f"({_insufficient_data_null_count(report)['count']} null), limiting accurate analysis: "
            f"{', '.join(_insufficient_data_null_count(report)['null_fields'])}"
        ),
        evidence=lambda report: _insufficient_data_null_count(report),
    ),
    Rule(
        id="stitch_count_risk",
        category="performance",
        group="stitch_density",
        severity="medium",
        confidence=0.8,
        fields=["geometry.path_length_mm", "parameters.stitch_length_mm"],
        title="High estimated stitch count",
        source="rule-engine/heuristics: path length / stitch length",
        suggested_action="Increase stitch length or simplify the path",
        check=lambda report: (
            (length := report.geometry.get("path_length_mm")) is not None
            and (stitch := report.parameters.get("stitch_length_mm")) is not None
            and length / stitch > 3000
        ),
        detail=lambda _report: (
            "Estimated stitch count is high based on path length and stitch length"
        ),
    ),
    Rule(
        id="global_complexity_risk",
        category="performance",
        group="complexity",
        severity="medium",
        confidence=0.7,
        fields=["summary.total_path_length_mm", "summary.avg_segment_length_global"],
        title="Global design complexity",
        source="rule-engine/heuristics: document path length and segment length",
        suggested_action=(
            "Simplify paths or reduce fragmentation to improve simulation performance"
        ),
        check=lambda report: (
            (total := report.summary.get("total_path_length_mm")) is not None
            and (avg := report.summary.get("avg_segment_length_global")) is not None
            and total > 2000
            and avg < 1.0
        ),
        detail=lambda _report: (
            "Overall design complexity may impact simulation or stitching performance"
        ),
    ),
]
