"""Failure type classification."""

from __future__ import annotations

from app.services.rule_engine.types import ClassificationResult, DesignReport, Issue


def classify_failure(report: DesignReport, _issues: list[Issue]) -> ClassificationResult:
    element_count = report.structure.get("element_count", 0)
    node_count = report.geometry.get("node_count", 0)
    has_geometry = node_count is not None and node_count > 0

    if element_count == 0 and has_geometry:
        return ClassificationResult(
            type="structure",
            confidence="high",
            reason="Geometry exists but no stitch elements detected",
        )

    hidden_layer_count = report.summary.get("hidden_layer_count") or 0
    if report.structure.get("has_hidden_layers") or hidden_layer_count > 0:
        return ClassificationResult(
            type="structure",
            confidence="medium",
            reason="Hidden layers detected",
        )

    stitch_types = report.structure.get("stitch_types") or []
    if "running" in stitch_types and "satin" in stitch_types and element_count > 20:
        return ClassificationResult(
            type="parameter",
            confidence="medium",
            reason="Mixed stitch types suggest param inconsistency",
        )

    if report.export.get("format") is None:
        return ClassificationResult(
            type="parameter",
            confidence="low",
            reason="Missing export format",
        )

    min_dim = report.geometry.get("min_dimension_mm")
    if min_dim is not None and min_dim < 1.0:
        return ClassificationResult(
            type="geometry",
            confidence="high",
            reason="Very narrow geometry detected",
        )

    avg_seg = report.geometry.get("avg_segment_length_mm")
    if avg_seg is not None and avg_seg < 0.5:
        return ClassificationResult(
            type="geometry",
            confidence="medium",
            reason="Highly fragmented path",
        )

    if report.routing.get("jump_stitch_count") is None:
        return ClassificationResult(
            type="routing",
            confidence="low",
            reason="Routing data missing",
        )

    return ClassificationResult(
        type="unknown",
        confidence="low",
        reason="No strong signal detected",
    )
