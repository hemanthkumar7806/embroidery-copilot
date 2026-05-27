"""Parameter rules with doc-aligned thresholds."""

from __future__ import annotations

from app.services.rule_engine.config import (
    EXTREME_EXPAND_MM,
    PULL_COMP_STRETCHY_MIN_MM,
    ROW_SPACING_TOO_HIGH_MM,
    RUNNING_MIN_STITCH_LENGTH_MM,
    SATIN_MIN_STITCH_LENGTH_MM,
    STRETCHY_FABRICS,
)
from app.services.rule_engine.types import DesignReport, Rule


def _is_stretchy_fabric(report: DesignReport) -> bool:
    fabric = report.physical.get("fabric_type")
    if not isinstance(fabric, str):
        return False
    lowered = fabric.lower()
    return any(name in lowered for name in STRETCHY_FABRICS)


def _min_stitch_length_threshold(report: DesignReport) -> float:
    stitch_types = report.structure.get("stitch_types") or []
    satin_only = "satin" in stitch_types and "running" not in stitch_types and "stroke" not in stitch_types
    return SATIN_MIN_STITCH_LENGTH_MM if satin_only else RUNNING_MIN_STITCH_LENGTH_MM


def _stitch_length_too_short(report: DesignReport) -> bool:
    stitch_length = report.parameters.get("stitch_length_mm")
    if stitch_length is None:
        return False
    return stitch_length < _min_stitch_length_threshold(report)


def _pull_compensation_missing(report: DesignReport) -> bool:
    pull_comp = report.parameters.get("pull_compensation_mm")
    if pull_comp is None:
        return False
    stitch_types = report.structure.get("stitch_types") or []
    if "fill" in stitch_types and pull_comp == 0:
        return True
    return _is_stretchy_fabric(report) and pull_comp < PULL_COMP_STRETCHY_MIN_MM


parameter_rules: list[Rule] = [
    Rule(
        id="row_spacing_too_low",
        category="parameters",
        severity="high",
        confidence=0.85,
        fields=["parameters.row_spacing_mm"],
        skip_when=lambda report: report.parameters.get("row_spacing_mm") is None,
        title="Row spacing too low",
        source="docs/sources/inkstitch/stitch-fill.md; extracted-data.md",
        suggested_action="Increase row spacing to minimum 0.35mm in Ink/Stitch fill settings",
        check=lambda report: (report.parameters.get("row_spacing_mm") or 0) < 0.35,
        detail=lambda report: (
            f"Row spacing is {report.parameters.get('row_spacing_mm')}mm (minimum: 0.35mm). "
            "Dense fills cause thread breakage and fabric damage."
        ),
    ),
    Rule(
        id="row_spacing_too_high",
        category="parameters",
        severity="medium",
        confidence=0.7,
        fields=["parameters.row_spacing_mm"],
        skip_when=lambda report: report.parameters.get("row_spacing_mm") is None,
        title="Row spacing too high",
        source="docs/sources/inkstitch/stitch-fill.md; docs/sources/community/fabric-presets.md",
        suggested_action="Decrease row spacing — gaps between rows will show in finished embroidery",
        check=lambda report: (report.parameters.get("row_spacing_mm") or 0) > ROW_SPACING_TOO_HIGH_MM,
        detail=lambda report: (
            f"Row spacing is {report.parameters.get('row_spacing_mm')}mm "
            f"(maximum recommended: {ROW_SPACING_TOO_HIGH_MM}mm). "
            "Gaps will be visible in stitch-out."
        ),
    ),
    Rule(
        id="stitch_length_too_short",
        category="parameters",
        severity="high",
        confidence=0.85,
        fields=["parameters.stitch_length_mm", "structure.stitch_types"],
        skip_when=lambda report: report.parameters.get("stitch_length_mm") is None,
        title="Stitch length too short",
        source="docs/sources/inkstitch/extracted-data.md; satin min 0.4 mm, running min 1.5 mm",
        suggested_action="Set minimum stitch length appropriate to stitch type in Ink/Stitch params",
        check=_stitch_length_too_short,
        detail=lambda report: (
            f"Stitch length is {report.parameters.get('stitch_length_mm')}mm "
            f"(minimum: {_min_stitch_length_threshold(report)}mm). "
            "Very short stitches shred thread and damage fabric."
        ),
    ),
    Rule(
        id="stitch_length_too_long",
        category="parameters",
        severity="medium",
        confidence=0.75,
        fields=["parameters.stitch_length_mm"],
        skip_when=lambda report: report.parameters.get("stitch_length_mm") is None,
        title="Stitch length too long",
        source="docs/sources/inkstitch/extracted-data.md",
        suggested_action="Keep stitches under 6mm — add intermediate stitches for long spans",
        check=lambda report: (report.parameters.get("stitch_length_mm") or 0) > 6.0,
        detail=lambda report: (
            f"Stitch length is {report.parameters.get('stitch_length_mm')}mm (maximum: 6.0mm). "
            "Long stitches snag and distort easily."
        ),
    ),
    Rule(
        id="pull_compensation_missing",
        category="parameters",
        severity="medium",
        confidence=0.65,
        fields=["parameters.pull_compensation_mm", "structure.stitch_types", "physical.fabric_type"],
        skip_when=lambda report: (
            report.parameters.get("pull_compensation_mm") is None
            or (
                "fill" not in (report.structure.get("stitch_types") or [])
                and not _is_stretchy_fabric(report)
            )
        ),
        title="Pull compensation missing on fill",
        source=(
            "docs/sources/inkstitch/tutorial-pull-compensation.md; "
            "community stretch starting point 0.17–0.20 mm"
        ),
        suggested_action=(
            "Add pull compensation 0.2–0.3mm for woven fabric, higher for stretch fabrics"
        ),
        check=_pull_compensation_missing,
        detail=lambda report: (
            f"Pull compensation is {report.parameters.get('pull_compensation_mm')}mm. "
            "Fill/stretch designs need compensation to prevent size distortion."
        ),
    ),
    Rule(
        id="extreme_density",
        category="parameters",
        severity="high",
        confidence=0.8,
        fields=["parameters.expand_mm"],
        skip_when=lambda report: report.parameters.get("expand_mm") is None,
        title="Extreme density",
        source="docs/sources/inkstitch/stitch-fill.md; expand_mm > 4 mm threshold",
        suggested_action=(
            "Reduce density — if design requires detail, consider splitting into multiple passes"
        ),
        check=lambda report: (report.parameters.get("expand_mm") or 0) > EXTREME_EXPAND_MM,
        detail=lambda report: (
            f"Expand/density is {report.parameters.get('expand_mm')}mm "
            f"(threshold: {EXTREME_EXPAND_MM}mm). "
            "Extreme density causes needle breakage and fabric damage."
        ),
    ),
]
