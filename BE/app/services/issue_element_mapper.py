"""Map rule-engine issue IDs to SVG element targets for preview highlighting."""

from __future__ import annotations

from typing import Any

from app.services.fabric_presets import DEFAULT as DEFAULT_PRESET
from app.services.fabric_presets import preset_for
from app.services.rule_engine.config import (
    EXTREME_EXPAND_MM,
    FILL_MIN_WIDTH_MM,
    PULL_COMP_STRETCHY_MIN_MM,
    RUNNING_MIN_STITCH_LENGTH_MM,
    SATIN_MIN_STITCH_LENGTH_MM,
    SATIN_MIN_WIDTH_MM,
    STRETCHY_FABRICS,
)
from app.services.rule_engine.normalizer import _collect_stitch_length_mm
from app.services.rule_engine.normalizer import _num as _parse_num
from app.services.rule_engine.normalizer import resolve_stitch_type

OVER_DETAILED_SEGMENT_MM = 0.5
HIGH_NODE_COUNT_PER_ELEMENT = 500


def _valid_elements(design_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [element for element in design_report.get("elements") or [] if not element.get("parse_error")]


def _by_stitch(elements: list[dict[str, Any]], stitch_types: set[str]) -> list[dict[str, Any]]:
    """Elements whose resolved stitch type is one of stitch_types (for param fixes)."""
    return [element for element in elements if resolve_stitch_type(element) in stitch_types]


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

    elif issue_id in ("row_spacing_too_low", "row_spacing_too_high"):
        preset = preset_for((design_report.get("physical") or {}).get("fabric_type"))
        for element in _by_stitch(elements, {"fill"}):
            row = _parse_num((element.get("params") or {}).get("row_spacing_mm"))
            if row is None:
                continue
            if issue_id == "row_spacing_too_low" and row < preset.row_spacing_min_mm:
                matched.append(element)
            elif issue_id == "row_spacing_too_high" and row > preset.row_spacing_max_mm:
                matched.append(element)

    elif issue_id == "extreme_density":
        for element in _by_stitch(elements, {"fill"}):
            expand = _parse_num((element.get("params") or {}).get("expand_mm"))
            if expand is not None and expand > EXTREME_EXPAND_MM:
                matched.append(element)

    elif issue_id == "pull_compensation_missing":
        fabric = (design_report.get("physical") or {}).get("fabric_type")
        stretchy = isinstance(fabric, str) and any(name in fabric.lower() for name in STRETCHY_FABRICS)
        for element in elements:
            pull = _parse_num((element.get("params") or {}).get("pull_compensation_mm"))
            if pull is None:
                continue
            stitch = resolve_stitch_type(element)
            if stitch == "fill" and pull == 0:
                matched.append(element)
            elif stretchy and pull < PULL_COMP_STRETCHY_MIN_MM:
                matched.append(element)

    elif issue_id in ("stitch_length_too_short", "stitch_length_too_long"):
        stitch_types = design_report.get("structure", {}).get("stitch_types") or []
        satin_only = "satin" in stitch_types and "running" not in stitch_types and "stroke" not in stitch_types
        min_threshold = SATIN_MIN_STITCH_LENGTH_MM if satin_only else RUNNING_MIN_STITCH_LENGTH_MM
        for element in _by_stitch(elements, {"running", "stroke", "satin"}):
            length = _collect_stitch_length_mm(element.get("params") or {})
            if length is None:
                continue
            if issue_id == "stitch_length_too_short" and length < min_threshold:
                matched.append(element)
            elif issue_id == "stitch_length_too_long" and length > 6.0:
                matched.append(element)

    element_ids = [str(element.get("id")) for element in matched if element.get("id")]
    boxes = [_element_bbox(element) for element in matched]
    focus_bbox = _union_bbox([box for box in boxes if box is not None])
    return {"element_ids": element_ids, "focus_bbox": focus_bbox}


# Deterministic 🟢 auto-fix recipes, keyed by rule/issue id. Ink/Stitch stores parameters
# as attributes in the inkstitch namespace, so an attribute set IS the parameter change.
# NOTE: exact inkstitch attribute names must be confirmed against the installed Ink/Stitch
# param registry when wiring the live agent; the {op, attribute, value, target_ids} shape
# is the stable contract downstream (queue + agent) consumes.
_FIX_RECIPES: dict[str, dict[str, Any]] = {
    "row_spacing_too_low": {
        "op": "set-attribute", "attribute": "inkstitch:row_spacing_mm", "value": "0.4",
        "label": "row spacing", "unit": "mm", "current": ("parameters", "row_spacing_mm"),
        "preset_field": "row_spacing_mm",
    },
    "row_spacing_too_high": {
        "op": "set-attribute", "attribute": "inkstitch:row_spacing_mm", "value": "0.4",
        "label": "row spacing", "unit": "mm", "current": ("parameters", "row_spacing_mm"),
        "preset_field": "row_spacing_mm",
    },
    "stitch_length_too_short": {
        "op": "set-attribute", "attribute": "inkstitch:running_stitch_length_mm", "value": "2.0",
        "label": "stitch length", "unit": "mm", "current": ("parameters", "stitch_length_mm"),
    },
    "stitch_length_too_long": {
        "op": "set-attribute", "attribute": "inkstitch:running_stitch_length_mm", "value": "3.0",
        "label": "stitch length", "unit": "mm", "current": ("parameters", "stitch_length_mm"),
    },
    "pull_compensation_missing": {
        "op": "set-attribute", "attribute": "inkstitch:pull_compensation_mm", "value": "0.25",
        "label": "pull compensation", "unit": "mm", "current": ("parameters", "pull_compensation_mm"),
        "preset_field": "pull_compensation_mm",
    },
    "extreme_density": {
        "op": "set-attribute", "attribute": "inkstitch:expand_mm", "value": "1.0",
        "label": "fill expand", "unit": "mm", "current": ("parameters", "expand_mm"),
    },
    # Path-op fixes (no attribute). Behind the undo-granularity gate until verified per op.
    "high_node_count": {"op": "simplify", "label": "path simplification"},
    "over_detailed_path": {"op": "simplify", "label": "path simplification"},
}


def _current_value(design_report: dict[str, Any], ref: tuple[str, str] | None) -> Any:
    if not ref:
        return None
    section, key = ref
    container = design_report.get(section)
    if isinstance(container, dict):
        return container.get(key)
    return None


# Sentinel distinguishing "no override given" (use the doc-wide aggregate) from an
# explicit override of None (element has no value for this parameter at all).
_NO_OVERRIDE = object()


def _element_current_value(issue_id: str, element: dict[str, Any]) -> Any:
    """This element's own raw parameter value, for a per-instance fix's 'was X' text."""
    params = element.get("params") or {}
    if issue_id in ("row_spacing_too_low", "row_spacing_too_high"):
        return _parse_num(params.get("row_spacing_mm"))
    if issue_id in ("stitch_length_too_short", "stitch_length_too_long"):
        return _collect_stitch_length_mm(params)
    if issue_id == "pull_compensation_missing":
        return _parse_num(params.get("pull_compensation_mm"))
    if issue_id == "extreme_density":
        return _parse_num(params.get("expand_mm"))
    return None


def resolve_fix(
    issue_id: str,
    element_ids: list[str],
    design_report: dict[str, Any],
    current_override: Any = _NO_OVERRIDE,
) -> dict[str, Any] | None:
    """Synthesize a structured, whitelisted auto-fix operation for a 🟢 issue.

    Returns None when there is no recipe or no target element — a fix is only offered
    when it can actually be applied. `current_override` lets a per-instance fix report
    that one element's own current value instead of the design-wide aggregate.
    """
    recipe = _FIX_RECIPES.get(issue_id)
    if not recipe or not element_ids:
        return None

    op = recipe["op"]
    count = len(element_ids)
    noun = "object" if count == 1 else "objects"
    fix: dict[str, Any] = {"op": op, "target_ids": list(element_ids)}

    if op == "set-attribute":
        # Fabric-aware value: preset-driven ops take their target from the design's fabric
        # preset; others keep the recipe default. Unknown fabric -> DEFAULT (unchanged).
        preset = preset_for((design_report.get("physical") or {}).get("fabric_type"))
        preset_field = recipe.get("preset_field")
        if preset_field:
            value = f"{getattr(preset, preset_field):g}"
        else:
            value = recipe["value"]
        for_fabric = f" for {preset.label}" if preset is not DEFAULT_PRESET else ""

        fix["attribute"] = recipe["attribute"]
        fix["value"] = value
        current = (
            _current_value(design_report, recipe.get("current"))
            if current_override is _NO_OVERRIDE
            else current_override
        )
        was = f" (was {current}{recipe['unit']})" if current is not None else ""
        fix["summary"] = (
            f"Set {recipe['label']} to {value}{recipe['unit']}{for_fabric} "
            f"on {count} {noun}{was}"
        )
        return fix

    if op == "simplify":
        fix["summary"] = f"Simplify {count} {noun} to reduce node count"
        return fix

    return None


def build_instances(
    design_report: dict[str, Any], element_ids: list[str], issue_id: str | None = None
) -> list[dict[str, Any]]:
    """Per-element breakdown of an issue: one entry per shape with its own tight
    focus_bbox and (for a 🟢 issue with a fix recipe) its own single-target fix.

    This is what lets the UI show "3 shapes affected" as three separate rows instead
    of one blurry group — each row zooms to and fixes exactly one shape.
    """
    elements_by_id = {str(el.get("id")): el for el in _valid_elements(design_report) if el.get("id")}
    instances: list[dict[str, Any]] = []
    for element_id in element_ids:
        element = elements_by_id.get(element_id)
        if element is None:
            continue
        box = _element_bbox(element)
        fix = None
        if issue_id:
            fix = resolve_fix(
                issue_id,
                [element_id],
                design_report,
                current_override=_element_current_value(issue_id, element),
            )
        instances.append(
            {
                "element_id": element_id,
                "focus_bbox": _union_bbox([box]) if box else None,
                "fix": fix,
            }
        )
    return instances


def enrich_rule_engine_payload(design_report: dict[str, Any], rules_payload: dict[str, Any]) -> dict[str, Any]:
    """Attach element_ids, focus_bbox, and a per-shape instance breakdown to each issue."""
    enriched = dict(rules_payload)
    for key in ("issues", "context_gaps"):
        items = []
        for issue in rules_payload.get(key) or []:
            if not isinstance(issue, dict):
                continue
            issue_id = str(issue.get("id") or "")
            targets = resolve_issue_targets(issue_id, design_report)
            enriched_issue = {
                **issue,
                "element_ids": targets["element_ids"],
                "focus_bbox": targets["focus_bbox"],
                "instances": build_instances(design_report, targets["element_ids"], issue_id),
            }
            # Attach a concrete auto-fix op only for 🟢 issues that resolve to targets.
            if issue.get("capability") == "auto_fix":
                enriched_issue["fix"] = resolve_fix(
                    issue_id, targets["element_ids"], design_report
                )
            items.append(enriched_issue)
        enriched[key] = items
    return enriched
