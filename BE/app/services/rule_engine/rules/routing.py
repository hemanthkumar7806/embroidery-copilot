"""Routing rules."""

from __future__ import annotations

from app.services.rule_engine.types import Rule

routing_rules: list[Rule] = [
    Rule(
        id="excessive_jump_stitches",
        category="routing",
        severity="high",
        confidence=0.8,
        fields=["routing.jump_stitch_count"],
        skip_when=lambda report: report.routing.get("jump_stitch_count") is None,
        title="Excessive jump stitches",
        source="docs/sources/inkstitch/tutorial-routing.md",
        suggested_action=(
            "Re-order stitch elements or use running stitch connectors between nearby objects"
        ),
        check=lambda report: (report.routing.get("jump_stitch_count") or 0) > 30,
        detail=lambda report: (
            f"{report.routing.get('jump_stitch_count')} jump stitches detected (threshold: 30). "
            "Excessive jumps increase production time and visible thread tails."
        ),
    ),
    Rule(
        id="excessive_color_changes",
        category="routing",
        severity="medium",
        confidence=0.75,
        fields=["routing.color_change_count"],
        skip_when=lambda report: report.routing.get("color_change_count") is None,
        title="Excessive color changes",
        source="production / machine stops",
        suggested_action="Consolidate colors — reorder elements to batch same-color stitching together",
        check=lambda report: (report.routing.get("color_change_count") or 0) > 10,
        detail=lambda report: (
            f"{report.routing.get('color_change_count')} color changes (threshold: 10). "
            "Each change requires machine stop and operator re-threading."
        ),
    ),
    Rule(
        id="stitch_count_too_high",
        category="routing",
        severity="medium",
        confidence=0.7,
        fields=["routing.estimated_stitch_count"],
        skip_when=lambda report: report.routing.get("estimated_stitch_count") is None,
        title="Stitch count very high",
        source="production time heuristic",
        suggested_action="Simplify design or reduce fill density to lower stitch count",
        check=lambda report: (report.routing.get("estimated_stitch_count") or 0) > 15000,
        detail=lambda report: (
            f"Estimated {report.routing.get('estimated_stitch_count'):,} stitches "
            "(threshold: 15,000). High stitch count significantly increases production time."
        ),
    ),
    Rule(
        id="short_run_segments",
        category="routing",
        severity="high",
        confidence=0.78,
        fields=["routing.has_short_runs"],
        skip_when=lambda report: report.routing.get("has_short_runs") is None,
        title="Short run segments",
        source="docs/sources/community/failure-causes.md",
        suggested_action="Minimum 3 stitches per run — merge very short segments with adjacent elements",
        check=lambda report: report.routing.get("has_short_runs") is True,
        detail=lambda _report: (
            "Short run segments detected (fewer than 3 stitches). "
            "Very short runs cause tension issues and thread nesting."
        ),
    ),
    Rule(
        id="trim_count_high",
        category="routing",
        severity="low",
        confidence=0.6,
        fields=["routing.trim_count"],
        skip_when=lambda report: report.routing.get("trim_count") is None,
        title="High trim count",
        source="production efficiency",
        suggested_action="Connect nearby elements with short running stitches instead of trim+jump",
        check=lambda report: (report.routing.get("trim_count") or 0) > 20,
        detail=lambda report: (
            f"{report.routing.get('trim_count')} trims detected (threshold: 20). "
            "Excessive trims slow production and increase manual cleanup."
        ),
    ),
    Rule(
        id="zero_stitches",
        category="routing",
        severity="critical",
        confidence=1.0,
        fields=["routing.estimated_stitch_count"],
        skip_when=lambda report: report.routing.get("estimated_stitch_count") is None,
        title="Zero stitches",
        source="docs/sources/inkstitch/params-overview.md",
        suggested_action=(
            "Apply Ink/Stitch params to paths via Extensions > Ink/Stitch > Params before simulating"
        ),
        check=lambda report: report.routing.get("estimated_stitch_count") == 0,
        detail=lambda _report: (
            "Zero stitches estimated. No Ink/Stitch params are applied to any design element."
        ),
    ),
]
