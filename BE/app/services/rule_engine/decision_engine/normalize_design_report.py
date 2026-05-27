"""Decision engine: per-element normalization for state/mismatch checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.services.rule_engine.types import DesignReport

StitchType = Literal["satin", "stroke", "fill"] | None


@dataclass
class DesignElement:
    id: str
    node_count: int
    subpath_count: int
    min_segment_length: float
    stitch_type: StitchType
    attrs: dict[str, Any]
    has_inkstitch_attrs: bool
    is_single_stroke_visual: bool
    d: str | None = None


@dataclass
class NormalizedDesignReport:
    elements: list[DesignElement]


def _count_subpaths(d: str | None) -> int:
    if not d:
        return 1
    parts = d.split("M")
    return max(len(parts) - 1, 1)


def _as_stitch_type(value: Any) -> StitchType:
    if value in ("satin", "stroke", "fill"):
        return value
    return None


def _normalize_element(raw: dict[str, Any], index: int) -> DesignElement:
    attrs = raw.get("attrs") if isinstance(raw.get("attrs"), dict) else {}
    if not attrs and isinstance(raw.get("params"), dict):
        attrs = raw["params"]

    d_value = raw.get("d") if isinstance(raw.get("d"), str) else None
    node_count_raw = raw.get("node_count")
    node_count = int(node_count_raw) if isinstance(node_count_raw, (int, float)) else 0
    min_seg_raw = raw.get("min_segment_length")
    if min_seg_raw is None:
        min_seg_raw = raw.get("avg_segment_length_mm")
    min_segment_length = float(min_seg_raw) if isinstance(min_seg_raw, (int, float)) else 0.0

    element = DesignElement(
        id=str(raw.get("id") or f"element_{index + 1}"),
        node_count=node_count,
        subpath_count=1,
        min_segment_length=min_segment_length,
        stitch_type=_as_stitch_type(raw.get("stitch_type")),
        attrs=attrs,
        has_inkstitch_attrs=False,
        is_single_stroke_visual=False,
        d=d_value,
    )

    element.has_inkstitch_attrs = any(
        key.startswith("inkstitch:") or key in attrs for key in (element.attrs or {})
    ) and len(element.attrs) > 0
    element.subpath_count = _count_subpaths(element.d)
    element.is_single_stroke_visual = element.subpath_count == 1 and element.node_count < 50
    return element


def normalize_design_report_for_decision(report: DesignReport) -> NormalizedDesignReport:
    if report.elements:
        return NormalizedDesignReport(
            elements=[_normalize_element(element, index) for index, element in enumerate(report.elements)]
        )

    stitch_type = report.structure.get("stitch_types", [None])[0] if report.structure.get("stitch_types") else None
    pseudo = _normalize_element(
        {
            "id": "report_geometry",
            "node_count": report.geometry.get("node_count", 0),
            "min_segment_length": report.geometry.get("avg_segment_length_mm") or 0,
            "stitch_type": stitch_type,
            "attrs": {},
            "d": "M 0 0",
        },
        0,
    )
    return NormalizedDesignReport(elements=[pseudo])
