"""Export rules."""

from __future__ import annotations

from app.services.rule_engine.config import MACHINE_FORMATS
from app.services.rule_engine.types import Rule

export_rules: list[Rule] = [
    Rule(
        id="missing_metadata",
        category="export",
        severity="low",
        confidence=0.5,
        fields=["export.has_metadata"],
        title="Missing metadata",
        source="production tracking best practice",
        suggested_action="Add design metadata in Ink/Stitch before export",
        check=lambda report: not report.export.get("has_metadata"),
        detail=lambda _report: (
            "Design metadata (name, size, thread count) is missing. "
            "Metadata is important for production tracking."
        ),
    ),
    Rule(
        id="unsupported_format",
        category="export",
        severity="high",
        confidence=0.85,
        fields=["export.format"],
        skip_when=lambda report: report.export.get("format") is None,
        title="Possibly unsupported export format",
        source="docs/sources/ricoma/chroma-supported-file-types.md; common machine formats",
        suggested_action="Export to DST, PES, JEF, or VP3 depending on your machine brand",
        check=lambda report: str(report.export.get("format")).lower() not in MACHINE_FORMATS,
        detail=lambda report: (
            f'Format "{report.export.get("format")}" may not be supported by all machines.'
        ),
    ),
]
