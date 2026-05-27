"""Geometry rules."""

from __future__ import annotations

from app.services.rule_engine.config import CRITICAL_MIN_WIDTH_MM, FILL_MIN_WIDTH_MM, SATIN_MIN_WIDTH_MM
from app.services.rule_engine.metrics import has_running_density_risk
from app.services.rule_engine.rules.performance import density_interaction_risk_fires
from app.services.rule_engine.types import DesignReport, Rule


def _narrow_geometry_check(report: DesignReport) -> bool:
    min_dim = report.geometry.get("min_dimension_mm")
    stitch_types = report.structure.get("stitch_types") or []
    risky_stitch = "satin" in stitch_types or "fill" in stitch_types
    if min_dim is None or not risky_stitch:
        return False
    if min_dim < CRITICAL_MIN_WIDTH_MM:
        return True
    return min_dim < SATIN_MIN_WIDTH_MM and "satin" in stitch_types


geometry_rules: list[Rule] = [
    Rule(
        id="high_node_count",
        category="geometry",
        severity="medium",
        confidence=0.75,
        fields=["geometry.node_count"],
        title="High node count",
        source=(
            "docs/sources/community/reddit-troubleshoot-passes-no-stitch-out.md; "
            "docs/rules/issue-checker-cross-reference.md §8"
        ),
        suggested_action="Simplify paths: Inkscape Path > Simplify (Ctrl+L)",
        check=lambda report: report.geometry.get("node_count", 0) > 1000,
        detail=lambda report: (
            f"Node count is {report.geometry.get('node_count')} (threshold: 1000). "
            "High node counts cause slow rendering and export errors."
        ),
    ),
    Rule(
        id="open_paths_present",
        category="geometry",
        severity="high",
        confidence=0.9,
        fields=["geometry.has_open_paths", "geometry.open_path_count"],
        title="Open paths present",
        source="docs/sources/inkstitch/troubleshoot.md; embroidery geometry best practice",
        suggested_action=(
            "Close all open paths before export (Path > Object to Path, then check for open nodes)"
        ),
        skip_when=lambda report: report.geometry.get("has_open_paths") is None,
        check=lambda report: report.geometry.get("has_open_paths") is True,
        detail=lambda _report: (
            "Design contains open paths. Open paths cause unpredictable stitch routing."
        ),
    ),
    Rule(
        id="high_overlap_ratio",
        category="geometry",
        severity="high",
        confidence=0.8,
        fields=["geometry.overlap_ratio"],
        title="High overlap ratio",
        source="docs/sources/community/failure-causes.md; density/overlap guidance",
        suggested_action="Remove overlapping fills — use cutwork or proper layer ordering instead",
        skip_when=lambda report: report.geometry.get("overlap_ratio") is None,
        check=lambda report: (report.geometry.get("overlap_ratio") or 0) > 0.3,
        detail=lambda report: (
            f"Overlap ratio is {(report.geometry.get('overlap_ratio') or 0) * 100:.1f}% "
            "(threshold: 30%). Overlapping fills cause thread buildup and puckering."
        ),
    ),
    Rule(
        id="design_exceeds_hoop",
        category="geometry",
        severity="critical",
        confidence=0.95,
        fields=["geometry.bounding_box", "physical.hoop_size_mm"],
        skip_when=lambda report: (
            report.physical.get("hoop_size_mm") is None
            or report.geometry.get("bounding_box") is None
        ),
        title="Design exceeds hoop",
        source="production constraint / hoop boundaries",
        suggested_action="Resize design to fit within hoop boundaries before export",
        check=lambda report: (
            (report.geometry.get("bounding_box") or {}).get("w", 0)
            > (report.physical.get("hoop_size_mm") or {}).get("w", 0)
            or (report.geometry.get("bounding_box") or {}).get("h", 0)
            > (report.physical.get("hoop_size_mm") or {}).get("h", 0)
        ),
        detail=lambda report: (
            f"Design is {(report.geometry.get('bounding_box') or {}).get('w')}×"
            f"{(report.geometry.get('bounding_box') or {}).get('h')}mm, hoop is "
            f"{(report.physical.get('hoop_size_mm') or {}).get('w')}×"
            f"{(report.physical.get('hoop_size_mm') or {}).get('h')}mm."
        ),
    ),
    Rule(
        id="too_many_paths",
        category="geometry",
        severity="low",
        confidence=0.6,
        fields=["geometry.path_count"],
        title="Many paths",
        source="conservative default; stitch file complexity",
        suggested_action="Combine redundant paths to reduce stitch file complexity",
        check=lambda report: report.geometry.get("path_count", 0) > 500,
        detail=lambda report: f"Path count is {report.geometry.get('path_count')} (threshold: 500).",
    ),
    Rule(
        id="over_detailed_path",
        category="geometry",
        group="complexity",
        severity="medium",
        confidence=0.75,
        fields=["geometry.avg_segment_length_mm"],
        title="Over-detailed path",
        source="rule-engine/heuristics: MCP avg segment length",
        suggested_action="Simplify path to reduce unnecessary detail",
        check=lambda report: (
            (avg := report.geometry.get("avg_segment_length_mm")) is not None and avg < 0.5
        ),
        detail=lambda _report: (
            "Very short segment lengths indicate overly detailed or fragmented path"
        ),
        evidence=lambda report: {
            "avg_segment_length_mm": report.geometry.get("avg_segment_length_mm"),
        },
    ),
    Rule(
        id="narrow_geometry_stitch_mismatch",
        category="geometry",
        group="feasibility",
        severity="high",
        confidence=0.85,
        fields=["geometry.min_dimension_mm", "structure.stitch_types"],
        title="Narrow geometry for stitch type",
        source=(
            "docs/rules/issue-checker-cross-reference.md; satin min width 1.5 mm "
            "(critical below 1.0 mm)"
        ),
        suggested_action="Use running stitch or increase shape width",
        check=_narrow_geometry_check,
        detail=lambda report: (
            "Geometry is too narrow for the selected stitch type (satin/fill) — "
            f"min width {report.geometry.get('min_dimension_mm')} mm"
        ),
        evidence=lambda report: {
            "min_dimension_mm": report.geometry.get("min_dimension_mm"),
            "stitch_types": report.structure.get("stitch_types"),
        },
    ),
    Rule(
        id="running_stitch_density_risk",
        category="geometry",
        group="density",
        severity="low",
        confidence=0.7,
        fields=["parameters.stitch_length_mm", "geometry.avg_segment_length_mm"],
        title="Running stitch density risk",
        source="rule-engine/heuristics: short stitch length + high node count",
        suggested_action="Increase stitch length slightly (1.8–2.0 mm) or simplify the path",
        skip_when=lambda report: report.parameters.get("stitch_length_mm") is None,
        check=lambda report: has_running_density_risk(report)
        and not density_interaction_risk_fires(report),
        detail=lambda _report: (
            "Short stitch length combined with many nodes may cause dense stitching and thread stress"
        ),
        evidence=lambda report: {
            "stitch_length_mm": report.parameters.get("stitch_length_mm"),
            "avg_segment_length_mm": report.geometry.get("avg_segment_length_mm"),
        },
    ),
    Rule(
        id="fill_on_narrow_path",
        category="geometry",
        group="feasibility",
        severity="high",
        confidence=0.85,
        fields=["structure.narrow_fill_count", "geometry.min_dimension_mm"],
        title="Fill stitch on a narrow path",
        source="docs/sources/inkstitch/stitch-fill.md (min width for fill ~2 mm)",
        suggested_action="Convert narrow fills to running or satin stitch",
        check=lambda report: (report.structure.get("narrow_fill_count") or 0) > 0,
        detail=lambda report: (
            f"{report.structure.get('narrow_fill_count')} fill element(s) are narrower than "
            f"{FILL_MIN_WIDTH_MM} mm — fill stitch cannot cover these shapes reliably."
        ),
        evidence=lambda report: {
            "narrow_fill_count": report.structure.get("narrow_fill_count"),
            "min_dimension_mm": report.geometry.get("min_dimension_mm"),
        },
    ),
]
