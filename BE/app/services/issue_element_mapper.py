"""Map rule-engine issue IDs to SVG element targets for preview highlighting."""

from __future__ import annotations

from typing import Any

from app.services.rule_engine.config import FILL_MIN_WIDTH_MM, SATIN_MIN_WIDTH_MM
from app.services.rule_engine.normalizer import resolve_stitch_type

OVER_DETAILED_SEGMENT_MM = 0.5
HIGH_NODE_COUNT_PER_ELEMENT = 500


def _valid_elements(design_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [element for element in design_report.get("elements") or [] if not element.get("parse_error")]


def _element_bbox(element: dict[str, Any]) -> dict[str, float] | None:
    bbox = element.get("bounding_box")
    if not isinstance(bbox, dict):
        return None
    try:
        x = float(bbox.get("x", 0))
        y = float(bbox.get("y", 0))
        w = float(bbox.get("w", 0))
        h = float(bbox.get("h", 0))
    except (TypeError, ValueError):
        return None
    if w <= 0 and h <= 0:
        return None
    if w <= 0:
        w = 1.0
    if h <= 0:
        h = 1.0
    return {"x": x, "y": y, "w": w, "h": h}


def _union_bbox(boxes: list[dict[str, float]], padding_ratio: float = 0.15) -> dict[str, float] | None:
    if not boxes:
        return None
    min_x = min(box["x"] for box in boxes)
    min_y = min(box["y"] for box in boxes)
    max_x = max(box["x"] + box["w"] for box in boxes)
    max_y = max(box["y"] + box["h"] for box in boxes)
    width = max_x - min_x
    height = max_y - min_y
    pad_x = width * padding_ratio
    pad_y = height * padding_ratio
    return {
        "x": min_x - pad_x,
        "y": min_y - pad_y,
        "w": width + pad_x * 2,
        "h": height + pad_y * 2,
    }


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def resolve_issue_targets(issue_id: str, design_report: dict[str, Any]) -> dict[str, Any]:
    """Return element_ids and focus_bbox for a rule issue."""
    elements = _valid_elements(design_report)
    matched: list[dict[str, Any]] = []

    if issue_id == "open_paths_present":
        matched = [element for element in elements if element.get("is_closed_path") is False]

    elif issue_id == "narrow_geometry_stitch_mismatch":
        for element in elements:
            stitch = resolve_stitch_type(element)
            min_dim = _num(element.get("min_dimension_mm"))
            if min_dim is None:
                continue
            if stitch in ("satin", "fill") and min_dim < SATIN_MIN_WIDTH_MM:
                matched.append(element)

    elif issue_id == "fill_on_narrow_path":
        for element in elements:
            stitch = resolve_stitch_type(element)
            min_dim = _num(element.get("min_dimension_mm"))
            if stitch == "fill" and min_dim is not None and min_dim < FILL_MIN_WIDTH_MM:
                matched.append(element)

    elif issue_id == "over_detailed_path":
        for element in elements:
            avg_seg = _num(element.get("avg_segment_length_mm"))
            if avg_seg is not None and avg_seg < OVER_DETAILED_SEGMENT_MM:
                matched.append(element)

    elif issue_id == "high_node_count":
        matched = [
            element
            for element in elements
            if isinstance(element.get("node_count"), (int, float))
            and int(element["node_count"]) > HIGH_NODE_COUNT_PER_ELEMENT
        ]
        if not matched and elements:
            summary = design_report.get("summary") or {}
            total_nodes = summary.get("total_node_count")
            if isinstance(total_nodes, (int, float)) and total_nodes > 1000:
                matched = elements

    element_ids = [str(element.get("id")) for element in matched if element.get("id")]
    boxes = [_element_bbox(element) for element in matched]
    focus_bbox = _union_bbox([box for box in boxes if box is not None])
    return {"element_ids": element_ids, "focus_bbox": focus_bbox}


def enrich_rule_engine_payload(design_report: dict[str, Any], rules_payload: dict[str, Any]) -> dict[str, Any]:
    """Attach element_ids and focus_bbox to each issue for UI highlighting."""
    enriched = dict(rules_payload)
    for key in ("issues", "context_gaps"):
        items = []
        for issue in rules_payload.get(key) or []:
            if not isinstance(issue, dict):
                continue
            issue_id = str(issue.get("id") or "")
            targets = resolve_issue_targets(issue_id, design_report)
            items.append(
                {
                    **issue,
                    "element_ids": targets["element_ids"],
                    "focus_bbox": targets["focus_bbox"],
                }
            )
        enriched[key] = items
    return enriched
