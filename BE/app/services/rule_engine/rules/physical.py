"""Physical / fabric rules."""

from __future__ import annotations

from app.services.rule_engine.config import STRETCHY_FABRICS
from app.services.rule_engine.types import Rule

physical_rules: list[Rule] = [
    Rule(
        id="fabric_type_unknown",
        category="physical",
        severity="low",
        confidence=0.4,
        fields=["physical.fabric_type"],
        title="Fabric type unknown",
        source="docs/rules/issue-checker-cross-reference.md (fabric-dependent thresholds)",
        suggested_action="Specify fabric type so appropriate thresholds can be applied",
        check=lambda report: report.physical.get("fabric_type") is None,
        detail=lambda _report: (
            "Fabric type not specified. Density, pull compensation, and underlay thresholds "
            "all vary by fabric."
        ),
    ),
    Rule(
        id="hoop_size_not_set",
        category="physical",
        severity="low",
        confidence=0.4,
        fields=["physical.hoop_size_mm"],
        title="Hoop size not set",
        source="hoop boundary checks",
        suggested_action="Set hoop size to enable boundary checking",
        check=lambda report: report.physical.get("hoop_size_mm") is None,
        detail=lambda _report: (
            "Hoop size not specified. Cannot check whether design fits the hoop."
        ),
    ),
    Rule(
        id="stretchy_fabric_no_underlay",
        category="physical",
        severity="critical",
        confidence=0.88,
        fields=["physical.fabric_type", "structure.has_underlay"],
        skip_when=lambda report: report.physical.get("fabric_type") is None,
        title="Stretchy fabric without underlay",
        source="docs/sources/community/fabric-presets.md",
        suggested_action="Add cutaway stabilizer and grid underlay for all stretchy fabric designs",
        check=lambda report: (
            any(name in str(report.physical.get("fabric_type")).lower() for name in STRETCHY_FABRICS)
            and not report.structure.get("has_underlay")
        ),
        detail=lambda report: (
            f'Fabric type "{report.physical.get("fabric_type")}" is stretchy but no underlay is set. '
            "Stretchy fabric with no underlay will severely distort."
        ),
    ),
]
