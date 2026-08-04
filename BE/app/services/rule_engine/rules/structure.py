"""Structure rules."""

from __future__ import annotations

from app.services.rule_engine.types import Rule

structure_rules: list[Rule] = [
    Rule(
        id="missing_underlay",
        category="structure",
        severity="high",
        confidence=0.8,
        fields=["structure.has_underlay", "structure.stitch_types"],
        title="Fill without underlay",
        source="docs/sources/inkstitch/tutorial-underlay.md",
        suggested_action=(
            "Add underlay stitches in Ink/Stitch — use edge-walk for light fabrics, grid for heavy"
        ),
        check=lambda report: (
            not report.structure.get("has_underlay")
            and "fill" in (report.structure.get("stitch_types") or [])
        ),
        detail=lambda _report: (
            "Fill stitches found but no underlay detected. "
            "Fills without underlay shift and distort on most fabrics."
        ),
    ),
    Rule(
        id="no_inkstitch_attributes_found",
        category="structure",
        severity="low",
        confidence=0.95,
        fields=["structure.element_count", "structure.has_inkstitch_params"],
        title="No Ink/Stitch attributes found",
        source="Ink/Stitch params model — shapes need inkstitch: attributes to be a configured embroidery design",
        suggested_action=(
            "If you intend to stitch this, select the shapes and set params via "
            "Extensions > Ink/Stitch > Params"
        ),
        check=lambda report: (
            report.structure.get("element_count", 0) > 0
            and not report.structure.get("has_inkstitch_params")
        ),
        detail=lambda _report: (
            "None of the shapes carry explicit Ink/Stitch parameters — this looks like a "
            "standard SVG that hasn't been prepared for embroidery yet, not an error."
        ),
    ),
    Rule(
        id="hidden_layers_present",
        category="structure",
        severity="medium",
        confidence=0.9,
        fields=["structure.has_hidden_layers"],
        title="Hidden layers present",
        source="Inkscape / export hygiene",
        suggested_action="Delete or show all hidden layers and review before export",
        check=lambda report: report.structure.get("has_hidden_layers") is True,
        detail=lambda _report: (
            "Hidden layers detected. Hidden layers may export unexpectedly and add unwanted stitches."
        ),
    ),
    Rule(
        id="no_stitch_types_detected",
        category="structure",
        severity="critical",
        confidence=0.95,
        fields=["structure.stitch_types"],
        title="No stitch types detected",
        source="docs/sources/inkstitch/params-overview.md",
        suggested_action=(
            "Select paths and apply Ink/Stitch params via Extensions > Ink/Stitch > Params"
        ),
        check=lambda report: len(report.structure.get("stitch_types") or []) == 0,
        detail=lambda _report: (
            "No embroidery stitch objects found. Design objects must have Ink/Stitch params applied."
        ),
    ),
    Rule(
        id="excessive_element_count",
        category="structure",
        severity="medium",
        confidence=0.65,
        fields=["structure.element_count"],
        title="High element count",
        source="docs/rules/issue-checker-cross-reference.md §8 (performance)",
        suggested_action="Merge or simplify elements where possible before simulation",
        check=lambda report: report.structure.get("element_count", 0) > 200,
        detail=lambda report: (
            f"Element count is {report.structure.get('element_count')} (threshold: 200). "
            "Large element counts significantly increase simulation and export time."
        ),
    ),
    Rule(
        id="satin_without_underlay",
        category="structure",
        severity="high",
        confidence=0.82,
        fields=["structure.stitch_types", "structure.has_underlay"],
        title="Satin without underlay",
        source="docs/sources/inkstitch/stitch-satin.md",
        suggested_action="Add zigzag or edge-walk underlay to all satin columns",
        check=lambda report: (
            "satin" in (report.structure.get("stitch_types") or [])
            and not report.structure.get("has_underlay")
        ),
        detail=lambda _report: (
            "Satin columns found without underlay. "
            "Satin without underlay sinks into fabric and loses definition."
        ),
    ),
    Rule(
        id="mixed_stitch_no_routing",
        category="structure",
        severity="medium",
        confidence=0.6,
        fields=["structure.stitch_types", "routing.jump_stitch_count"],
        skip_when=lambda report: report.routing.get("jump_stitch_count") is None,
        title="Mixed stitch types with many jumps",
        source="docs/sources/inkstitch/tutorial-routing.md",
        suggested_action="Re-sequence stitch order to group same-type elements and reduce jumps",
        check=lambda report: (
            len(report.structure.get("stitch_types") or []) > 2
            and (report.routing.get("jump_stitch_count") or 0) > 20
        ),
        detail=lambda report: (
            f"{len(report.structure.get('stitch_types') or [])} stitch types with "
            f"{report.routing.get('jump_stitch_count')} jump stitches. "
            "Poor routing between stitch types causes unnecessary jumps."
        ),
    ),
]
