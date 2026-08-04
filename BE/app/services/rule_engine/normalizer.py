"""Map svg_parser / bridge design reports into rule-engine DesignReport."""

from __future__ import annotations

from typing import Any

from app.services.rule_engine.config import FILL_MIN_WIDTH_MM, UNDERLAY_PARAM_KEYS
from app.services.rule_engine.types import DesignReport


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and float(value) == float(value):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = float(value)
            if parsed == parsed:
                return parsed
        except ValueError:
            return None
    return None


def params_indicate_underlay(params: dict[str, Any]) -> bool:
    for key in UNDERLAY_PARAM_KEYS:
        value = params.get(key)
        if value is True:
            return True
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized and normalized not in ("none", "false", "0"):
                return True
    return False


def resolve_stitch_type(element: dict[str, Any]) -> str:
    stitch_type = str(element.get("stitch_type") or "").lower()
    if stitch_type == "stroke":
        stroke_method = element.get("params", {}).get("stroke_method")
        if isinstance(stroke_method, str) and stroke_method.lower() == "manual_stitch":
            return "running"
    return str(element.get("stitch_type") or "")


def _collect_stitch_length_mm(params: dict[str, Any]) -> float | None:
    candidates = [
        _num(params.get("max_stitch_length_mm")),
        _num(params.get("min_stitch_length_mm")),
        _num(params.get("stitch_length_mm")),
        _num(params.get("running_stitch_length_mm")),
    ]
    positive = [value for value in candidates if value is not None and value > 0]
    return min(positive) if positive else None


def normalize_design_report(bridge: dict[str, Any]) -> DesignReport:
    """Aggregate bridge/svg_parser elements[] into a single DesignReport."""
    elements = bridge.get("elements") or []
    node_total = 0
    has_underlay = False
    row_vals: list[float] = []
    stitch_len_vals: list[float] = []
    pull_vals: list[float] = []
    expand_vals: list[float] = []
    density_proxy: float | None = None

    for element in elements:
        if element.get("parse_error"):
            continue

        node_count = element.get("node_count")
        if node_count is None:
            geometry = element.get("geometry") or {}
            node_count = _num(geometry.get("node_count"))
        if isinstance(node_count, (int, float)) and node_count > 0:
            node_total += int(node_count)

        params = element.get("params") or {}
        if isinstance(params, dict):
            row = _num(params.get("row_spacing_mm"))
            if row is not None and row > 0:
                row_vals.append(row)
            stitch_length = _collect_stitch_length_mm(params)
            if stitch_length is not None:
                stitch_len_vals.append(stitch_length)
            pull_comp = _num(params.get("pull_compensation_mm"))
            if pull_comp is not None:
                pull_vals.append(pull_comp)
            if params_indicate_underlay(params):
                has_underlay = True
            expand = _num(params.get("expand_mm"))
            if expand is not None and expand > 0:
                expand_vals.append(expand)
                density_value = min(1.0, expand / 8.0)
                density_proxy = (
                    density_value if density_proxy is None else max(density_proxy, density_value)
                )

    stitch_types = list({resolve_stitch_type(element) for element in elements if not element.get("parse_error")})

    row_spacing_mm = min(row_vals) if row_vals else None
    stitch_length_mm = min(stitch_len_vals) if stitch_len_vals else None
    pull_compensation_mm = max(pull_vals) if pull_vals else None
    max_expand_mm = max(expand_vals) if expand_vals else None

    estimated_stitch_count = (
        round(node_total * 1.2) if node_total > 0 and stitch_length_mm is not None else None
    )

    path_len_sum = 0.0
    path_len_known = 0
    avg_segs: list[float] = []
    min_dims: list[float] = []
    for element in elements:
        if element.get("parse_error"):
            continue
        path_length = _num(element.get("path_length_mm"))
        if path_length is not None and path_length > 0:
            path_len_sum += path_length
            path_len_known += 1
        avg_segment = _num(element.get("avg_segment_length_mm"))
        if avg_segment is not None and avg_segment > 0:
            avg_segs.append(avg_segment)
        min_dimension = _num(element.get("min_dimension_mm"))
        if min_dimension is not None and min_dimension > 0:
            min_dims.append(min_dimension)

    bridge_summary = bridge.get("summary") or {}
    total_path_mm = bridge_summary.get("total_path_length_mm")
    if not isinstance(total_path_mm, (int, float)):
        total_path_mm = path_len_sum if path_len_known > 0 else None

    min_avg_seg = min(avg_segs) if avg_segs else None
    min_dim_mm = min(min_dims) if min_dims else None

    open_path_count = _num(bridge_summary.get("open_path_count"))
    has_open_paths = open_path_count > 0 if open_path_count is not None else None

    hidden_layer_count = bridge_summary.get("hidden_layer_count")
    if not isinstance(hidden_layer_count, int):
        hidden_layer_count = 0

    page_size_mm = bridge_summary.get("page_size_mm")
    bounding_box = None
    if isinstance(page_size_mm, dict):
        width = _num(page_size_mm.get("w"))
        height = _num(page_size_mm.get("h"))
        if width is not None and height is not None:
            bounding_box = {"w": width, "h": height}

    valid_elements = [element for element in elements if not element.get("parse_error")]

    narrow_fill_count = 0
    for element in valid_elements:
        stitch = resolve_stitch_type(element)
        min_dim = _num(element.get("min_dimension_mm"))
        if stitch == "fill" and min_dim is not None and min_dim < FILL_MIN_WIDTH_MM:
            narrow_fill_count += 1

    # Shapes get a default stitch type inferred from fill/stroke even with zero explicit
    # inkstitch: attributes (see svg_parser._infer_stitch_type), so `stitch_types` alone can't
    # tell a digitized design apart from a plain, never-configured SVG. This does.
    has_inkstitch_params = any(bool(element.get("params")) for element in valid_elements)

    session_ctx = bridge.get("session_context") if isinstance(bridge.get("session_context"), dict) else {}
    physical_src = bridge.get("physical") if isinstance(bridge.get("physical"), dict) else {}
    fabric_type = physical_src.get("fabric_type") or session_ctx.get("fabric_type")
    hoop_size_mm = physical_src.get("hoop_size_mm") or session_ctx.get("hoop_size_mm")
    symptom = None
    if isinstance(bridge.get("meta"), dict):
        symptom = bridge["meta"].get("symptom")
    if not symptom:
        symptom = session_ctx.get("symptom")

    design_bbox = bridge_summary.get("design_bounding_box_mm")
    if isinstance(design_bbox, dict):
        width = _num(design_bbox.get("w"))
        height = _num(design_bbox.get("h"))
        if width is not None and height is not None:
            bounding_box = {"w": width, "h": height}

    return DesignReport(
        meta={"symptom": symptom},
        geometry={
            "node_count": node_total,
            "path_count": len(valid_elements),
            "bounding_box": bounding_box,
            "has_open_paths": has_open_paths,
            "open_path_count": open_path_count,
            "overlap_ratio": None,
            "path_length_mm": total_path_mm,
            "avg_segment_length_mm": min_avg_seg,
            "min_dimension_mm": min_dim_mm,
        },
        summary={
            "total_path_length_mm": total_path_mm,
            "avg_segment_length_global": bridge_summary.get("avg_segment_length_global"),
            "hidden_layer_count": hidden_layer_count,
        },
        parameters={
            "row_spacing_mm": row_spacing_mm,
            "stitch_length_mm": stitch_length_mm,
            "pull_compensation_mm": pull_compensation_mm,
            "density_value": density_proxy,
            "expand_mm": max_expand_mm,
        },
        structure={
            "layer_count": 1,
            "has_hidden_layers": hidden_layer_count > 0,
            "has_underlay": has_underlay,
            "stitch_types": stitch_types,
            "element_count": len(valid_elements),
            "narrow_fill_count": narrow_fill_count,
            "has_inkstitch_params": has_inkstitch_params,
        },
        routing={
            "jump_stitch_count": None,
            "trim_count": None,
            "color_change_count": None,
            "estimated_stitch_count": estimated_stitch_count,
            "has_short_runs": None,
        },
        export={
            "format": None,
            "software_version": None,
            "has_metadata": False,
        },
        physical={
            "fabric_type": fabric_type,
            "hoop_size_mm": hoop_size_mm,
            "machine_type": physical_src.get("machine_type"),
        },
        elements=valid_elements,
    )
