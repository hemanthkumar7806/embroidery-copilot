"""System / root-cause oriented rules."""

from __future__ import annotations

from app.services.rule_engine.types import DesignReport, Rule


def _hidden_layer_count(report: DesignReport) -> int | None:
    value = report.summary.get("hidden_layer_count")
    return value if isinstance(value, int) else None


system_rules: list[Rule] = [
    Rule(
        id="hidden_layer_stitch_risk",
        category="structure",
        group="root_cause",
        severity="high",
        confidence=0.9,
        fields=["summary.hidden_layer_count"],
        skip_when=lambda report: _hidden_layer_count(report) is None,
        title="Hidden layer stitch risk",
        source="root cause system checks",
        suggested_action="Remove hidden layers or unhide and validate before export",
        check=lambda report: (_hidden_layer_count(report) or 0) > 0,
        detail=lambda _report: "Hidden layers may still be stitched by the machine",
        evidence=lambda report: {"hidden_layer_count": _hidden_layer_count(report)},
    ),
    Rule(
        id="stitch_type_loss_risk",
        category="structure",
        group="root_cause",
        severity="high",
        confidence=0.85,
        fields=["structure.stitch_types", "structure.element_count"],
        skip_when=lambda report: report.structure.get("element_count") is None,
        title="Stitch type loss risk",
        source="root cause system checks",
        suggested_action="Reapply stitch params and avoid lossy conversion steps",
        check=lambda report: (
            "running" in (report.structure.get("stitch_types") or [])
            and "satin" in (report.structure.get("stitch_types") or [])
            and (report.structure.get("element_count") or 0) > 20
        ),
        detail=lambda _report: (
            "Unexpected mix of stitch types may indicate parameter loss or incorrect conversion"
        ),
        evidence=lambda report: {
            "stitch_types": report.structure.get("stitch_types"),
            "element_count": report.structure.get("element_count"),
        },
    ),
    Rule(
        id="export_param_mismatch_risk",
        category="export",
        group="root_cause",
        severity="medium",
        confidence=0.8,
        fields=["export.format", "export.software_version"],
        title="Export parameter mismatch risk",
        source="root cause system checks",
        suggested_action="Export with complete metadata and verify software compatibility",
        check=lambda report: (
            report.export.get("format") is None or report.export.get("software_version") is None
        ),
        detail=lambda _report: (
            "Export metadata is incomplete; machine may interpret design incorrectly"
        ),
        evidence=lambda report: {
            "format": report.export.get("format"),
            "software_version": report.export.get("software_version"),
        },
    ),
    Rule(
        id="fabric_instability_risk",
        category="physical",
        group="root_cause",
        severity="medium",
        confidence=0.75,
        fields=["physical.fabric_type"],
        title="Fabric instability risk",
        source="root cause system checks",
        suggested_action="Set fabric type and adjust stabilizer before stitching",
        check=lambda report: report.physical.get("fabric_type") is None,
        detail=lambda _report: (
            "Fabric type not specified; stretch fabrics may distort stitching"
        ),
        evidence=lambda report: {"fabric_type": report.physical.get("fabric_type")},
    ),
    Rule(
        id="trim_behavior_risk",
        category="routing",
        group="root_cause",
        severity="medium",
        confidence=0.75,
        fields=["routing.jump_stitch_count"],
        title="Trim behavior risk",
        source="root cause system checks",
        suggested_action="Verify trim settings and run machine preview on target format",
        check=lambda report: report.routing.get("jump_stitch_count") is None,
        detail=lambda _report: (
            "Trim/jump behavior unknown; machine may leave threads between elements"
        ),
        evidence=lambda report: {"jump_stitch_count": report.routing.get("jump_stitch_count")},
    ),
]
