"""Ink/Stitch design extraction from SVG bytes using lxml (no inkex)."""

from __future__ import annotations

import io
import json
import math
import re
from pathlib import Path
from typing import Any

from lxml import etree
from svgelements import Path as SvgPath

INKSTITCH_NS = "http://inkstitch.org/namespace"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
NS = {
    "svg": "http://www.w3.org/2000/svg",
    "inkstitch": INKSTITCH_NS,
    "inkscape": INKSCAPE_NS,
    "sodipodi": SODIPODI_NS,
}


def _local_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


GEOMETRY_TAGS = {"path", "circle", "ellipse", "rect", "line", "polyline", "polygon"}
_NON_DRAWABLE_ANCESTORS = {"defs", "clipPath", "mask", "symbol", "marker", "pattern"}


def _num(node: etree._Element, attr: str, default: float = 0.0) -> float:
    raw = node.get(attr)
    if raw is None:
        return default
    match = re.match(r"^\s*(-?[\d.]+)", raw)
    try:
        return float(match.group(1)) if match else default
    except (TypeError, ValueError):
        return default


def _shape_to_d(node: etree._Element) -> str | None:
    """Return a path 'd' string for a path or basic SVG shape (Ink/Stitch treats these as stitchable)."""
    tag = _local_tag(node.tag)
    if tag == "path":
        return node.get("d") or None
    if tag == "circle":
        cx, cy, r = _num(node, "cx"), _num(node, "cy"), _num(node, "r")
        if r <= 0:
            return None
        return f"M {cx - r},{cy} a {r},{r} 0 1,0 {2 * r},0 a {r},{r} 0 1,0 {-2 * r},0 Z"
    if tag == "ellipse":
        cx, cy, rx, ry = _num(node, "cx"), _num(node, "cy"), _num(node, "rx"), _num(node, "ry")
        if rx <= 0 or ry <= 0:
            return None
        return f"M {cx - rx},{cy} a {rx},{ry} 0 1,0 {2 * rx},0 a {rx},{ry} 0 1,0 {-2 * rx},0 Z"
    if tag == "rect":
        x, y, w, h = _num(node, "x"), _num(node, "y"), _num(node, "width"), _num(node, "height")
        if w <= 0 or h <= 0:
            return None
        return f"M {x},{y} h {w} v {h} h {-w} Z"
    if tag == "line":
        x1, y1, x2, y2 = _num(node, "x1"), _num(node, "y1"), _num(node, "x2"), _num(node, "y2")
        return f"M {x1},{y1} L {x2},{y2}"
    if tag in ("polyline", "polygon"):
        points = (node.get("points") or "").strip()
        if not points:
            return None
        d = f"M {points}"
        if tag == "polygon":
            d += " Z"
        return d
    return None


def _in_non_drawable(node: etree._Element) -> bool:
    parent = node.getparent()
    while parent is not None:
        if _local_tag(parent.tag) in _NON_DRAWABLE_ANCESTORS:
            return True
        parent = parent.getparent()
    return False


def _paint_info(node: etree._Element) -> tuple[bool, bool]:
    """Return (has_fill, has_stroke). SVG default fill is black when unspecified."""
    style_map: dict[str, str] = {}
    for part in (node.get("style") or "").split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            style_map[key.strip().lower()] = value.strip().lower()

    fill = style_map.get("fill", (node.get("fill") or "").strip().lower())
    stroke = style_map.get("stroke", (node.get("stroke") or "").strip().lower())

    has_fill = fill != "none"  # unspecified ("") defaults to black => still a fill
    has_stroke = stroke not in ("", "none")
    return has_fill, has_stroke


def _path_geometry_from_d(d: str) -> tuple[int, int] | None:
    if not d or not d.strip():
        return None
    commands = re.findall(r"[MLHVCSQTAZ]", d, re.IGNORECASE)
    if not commands:
        return None
    seg_count = len(commands)
    node_count = sum(1 for c in commands if c.upper() != "Z")
    return node_count, seg_count


def _is_visible(element: etree._Element) -> bool:
    if element.get("display") == "none":
        return False
    vis = element.get("visibility")
    if vis in ("hidden", "collapse"):
        return False
    op = element.get("opacity")
    if op is not None and str(op).strip() == "0":
        return False
    st = element.get("style") or ""
    compact = st.replace(" ", "").lower()
    if "display:none" in compact or "visibility:hidden" in compact:
        return False
    return True


def _get_layer_info(element: etree._Element) -> tuple[str | None, str | None]:
    parent = element.getparent()
    while parent is not None:
        if parent.get(f"{{{INKSCAPE_NS}}}groupmode") == "layer":
            layer_id = parent.get("id")
            label = parent.get(f"{{{INKSCAPE_NS}}}label")
            return layer_id, label or layer_id
        parent = parent.getparent()
    return None, None


def _style_summary(element: etree._Element) -> dict[str, str] | None:
    out: dict[str, str] = {}
    for key in ("fill", "stroke", "stroke-width", "opacity"):
        val = element.get(key)
        if val is not None and str(val).strip():
            out[key.replace("-", "_")] = str(val).strip()
    style = element.get("style")
    if style:
        out["style"] = style[:500] if len(style) > 500 else style
    return out or None


def _infer_stitch_type(node: etree._Element, inkstitch_attrs: dict[str, str]) -> str:
    if inkstitch_attrs.get("satin_column") or inkstitch_attrs.get("satin_method"):
        return "satin"
    if inkstitch_attrs.get("stroke_method"):
        return "stroke"
    tag = _local_tag(node.tag)
    if tag == "path":
        d = node.get("d", "")
        fill = node.get("fill")
        has_fill = fill and fill != "none"
        if has_fill and d and "z" in d.lower():
            return "fill"
    if inkstitch_attrs.get("row_spacing_mm") is not None or inkstitch_attrs.get("fill_underlay") is not None:
        return "fill"
    return "stroke"


def _count_hidden_layers(root: etree._Element) -> int:
    count = 0
    for node in root.iter():
        if _local_tag(node.tag) != "g":
            continue
        if node.get(f"{{{INKSCAPE_NS}}}groupmode") != "layer":
            continue
        style = (node.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or node.get(f"{{{SODIPODI_NS}}}insensitive") == "true":
            count += 1
    return count


def _parse_page_size_mm(root: etree._Element) -> dict[str, float] | None:
    width = root.get("width")
    height = root.get("height")
    if not width or not height:
        return None

    def _to_mm(value: str) -> float | None:
        value = value.strip()
        match = re.match(r"^([\d.]+)\s*(mm|cm|in|px|pt)?$", value)
        if not match:
            return None
        num = float(match.group(1))
        unit = (match.group(2) or "px").lower()
        if unit == "mm":
            return num
        if unit == "cm":
            return num * 10
        if unit == "in":
            return num * 25.4
        if unit == "pt":
            return num * 0.352778
        return num * 0.264583

    w_mm = _to_mm(width)
    h_mm = _to_mm(height)
    if w_mm is None or h_mm is None:
        return None
    return {"w": w_mm, "h": h_mm}


def _estimated_complexity_hint(total_node_count: int, element_count: int) -> float:
    score = (
        (total_node_count / 1000.0) * 0.5
        + (element_count / 200.0) * 0.3
        + (element_count / 100.0) * 0.2
    )
    return min(float(score), 1.0)


def _viewbox_scale_to_mm(root: etree._Element, page_mm: dict[str, float] | None) -> float:
    if page_mm:
        viewbox = root.get("viewBox")
        if viewbox:
            parts = viewbox.replace(",", " ").split()
            if len(parts) == 4:
                try:
                    vb_w = float(parts[2])
                    if vb_w > 0:
                        return page_mm["w"] / vb_w
                except ValueError:
                    pass
        return 1.0
    return 0.264583


def _avg_segment_length_mm(
    path_length_mm: float,
    segment_count: int | None,
) -> float | None:
    """Cheap average segment length — avoids svgelements point() sampling (very slow on arcs)."""
    if path_length_mm <= 0:
        return None
    n = segment_count if segment_count and segment_count > 0 else 1
    return path_length_mm / n


def _fast_path_length(svg_path: SvgPath) -> float:
    """Path length with a loose tolerance.

    svgelements' default length() on arc commands can take ~45s per path (Inkscape
    ellipses/circles converted to 'a' arcs). error=1.0 is accurate enough for
    embroidery heuristics and finishes in a few milliseconds.
    """
    try:
        return float(svg_path.length(error=1.0, min_depth=1))
    except TypeError:
        # Older svgelements without min_depth
        return float(svg_path.length(error=1.0))


def _metrics_from_bbox_and_length(
    x_min: float,
    y_min: float,
    width: float,
    height: float,
    path_length: float,
    scale_mm: float,
    segment_count: int | None = None,
) -> dict[str, Any]:
    width_mm = width * scale_mm
    height_mm = height * scale_mm
    path_length_mm = path_length * scale_mm
    min_dimension_mm = min(width_mm, height_mm) if width_mm > 0 and height_mm > 0 else None
    avg_seg = _avg_segment_length_mm(path_length_mm, segment_count)
    out: dict[str, Any] = {
        "bounding_box": {
            "x": round(x_min, 3),
            "y": round(y_min, 3),
            "w": round(width, 3),
            "h": round(height, 3),
        },
        "bounding_box_mm": {"w": round(width_mm, 3), "h": round(height_mm, 3)},
    }
    if min_dimension_mm is not None:
        out["min_dimension_mm"] = round(min_dimension_mm, 3)
    if path_length_mm > 0:
        out["path_length_mm"] = round(path_length_mm, 3)
    if avg_seg is not None and avg_seg > 0:
        out["avg_segment_length_mm"] = round(avg_seg, 3)
    return out


def _analytical_shape_metrics(node: etree._Element, scale_mm: float) -> dict[str, Any] | None:
    """O(1) geometry for basic shapes — never call svgelements on arcs."""
    tag = _local_tag(node.tag)
    if tag == "circle":
        cx, cy, r = _num(node, "cx"), _num(node, "cy"), _num(node, "r")
        if r <= 0:
            return None
        return _metrics_from_bbox_and_length(
            cx - r, cy - r, 2 * r, 2 * r, 2 * math.pi * r, scale_mm, segment_count=4
        )
    if tag == "ellipse":
        cx, cy, rx, ry = _num(node, "cx"), _num(node, "cy"), _num(node, "rx"), _num(node, "ry")
        if rx <= 0 or ry <= 0:
            return None
        # Ramanujan approximation for ellipse perimeter
        h = ((rx - ry) ** 2) / ((rx + ry) ** 2) if (rx + ry) else 0.0
        peri = math.pi * (rx + ry) * (1 + (3 * h) / (10 + math.sqrt(max(0.0, 4 - 3 * h))))
        return _metrics_from_bbox_and_length(
            cx - rx, cy - ry, 2 * rx, 2 * ry, peri, scale_mm, segment_count=4
        )
    if tag == "rect":
        x, y, w, h = _num(node, "x"), _num(node, "y"), _num(node, "width"), _num(node, "height")
        if w <= 0 or h <= 0:
            return None
        return _metrics_from_bbox_and_length(x, y, w, h, 2 * (w + h), scale_mm, segment_count=4)
    return None


def _path_metrics_from_d(
    d_attr: str, scale_mm: float, segment_count: int | None = None
) -> dict[str, Any] | None:
    try:
        svg_path = SvgPath(d_attr)
        bbox = svg_path.bbox()
        if bbox is None:
            return None
        if hasattr(bbox, "xmin"):
            x_min, y_min, x_max, y_max = bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax
        else:
            x_min, y_min, x_max, y_max = bbox
        width = max(0.0, x_max - x_min)
        height = max(0.0, y_max - y_min)
        path_length = _fast_path_length(svg_path)
        return _metrics_from_bbox_and_length(
            x_min, y_min, width, height, path_length, scale_mm, segment_count=segment_count
        )
    except Exception:
        return None


def _enrich_element_geometry(
    elements: list[dict[str, Any]],
    scale_mm: float,
) -> tuple[float | None, dict[str, float] | None]:
    """Attach path geometry; return total path length and design bbox."""
    total_path_length = 0.0
    path_len_known = 0
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    for entry in elements:
        if entry.get("parse_error"):
            continue
        metrics = entry.pop("_precomputed_metrics", None)
        if metrics is None:
            d_attr = entry.get("_d_attr")
            if not d_attr:
                continue
            metrics = _path_metrics_from_d(
                d_attr, scale_mm, segment_count=entry.get("segment_count")
            )
        if not metrics:
            continue
        entry.update(metrics)
        bbox = metrics.get("bounding_box") or {}
        if metrics.get("path_length_mm"):
            total_path_length += float(metrics["path_length_mm"])
            path_len_known += 1
        if bbox:
            bx = float(bbox.get("x", 0))
            by = float(bbox.get("y", 0))
            bw = float(bbox.get("w", 0))
            bh = float(bbox.get("h", 0))
            min_x = min(min_x, bx)
            min_y = min(min_y, by)
            max_x = max(max_x, bx + bw)
            max_y = max(max_y, by + bh)

    total_path_mm = total_path_length if path_len_known > 0 else None
    design_bbox = None
    if path_len_known > 0 and min_x != float("inf"):
        design_bbox = {
            "w": round(max_x - min_x, 3),
            "h": round(max_y - min_y, 3),
        }
    return total_path_mm, design_bbox


def empty_design_report() -> dict[str, Any]:
    """Placeholder report when the user has not uploaded an SVG yet."""
    return {
        "elements": [],
        "summary": {
            "document_name": None,
            "page_size_mm": None,
            "viewBox": None,
            "element_count": 0,
            "stitch_type_counts": {},
            "total_node_count": 0,
            "total_segment_count": 0,
            "hidden_layer_count": 0,
            "open_path_count": 0,
            "closed_path_count": 0,
            "transformed_element_count": 0,
            "estimated_complexity_hint": "no_design_uploaded",
        },
        "parse_warnings": [],
        "session_context": {
            "fabric_type": None,
            "garment_type": None,
            "symptom": None,
            "hoop_size_mm": None,
        },
    }


def build_design_report(svg_bytes: bytes, document_name: str = "upload.svg", include_geometry: bool = True) -> dict[str, Any]:
    """Parse SVG bytes and return an Ink/Stitch-oriented design report."""
    parser = etree.XMLParser(recover=True, huge_tree=False)
    root = etree.parse(io.BytesIO(svg_bytes), parser).getroot()
    ns_prefix = f"{{{INKSTITCH_NS}}}"

    elements: list[dict[str, Any]] = []
    parse_warnings: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    stitch_type_counts: dict[str, int] = {}
    total_node = 0
    total_seg = 0
    open_path_count = 0
    closed_path_count = 0
    transformed_count = 0

    page_mm = _parse_page_size_mm(root)
    hidden_layer_count = _count_hidden_layers(root)
    scale_mm = _viewbox_scale_to_mm(root, page_mm)

    for node in root.iter():
        inkstitch_attrs = {
            key[len(ns_prefix) :]: value
            for key, value in node.attrib.items()
            if key.startswith(ns_prefix)
        }

        implicit_paint: tuple[bool, bool] | None = None
        if not inkstitch_attrs:
            # No explicit Ink/Stitch params: still count plain drawable shapes,
            # because Ink/Stitch stitches any visible filled/stroked object.
            if _local_tag(node.tag) not in GEOMETRY_TAGS:
                continue
            if not _is_visible(node) or _in_non_drawable(node):
                continue
            has_fill, has_stroke = _paint_info(node)
            if not (has_fill or has_stroke):
                continue
            implicit_paint = (has_fill, has_stroke)

        elem_id = node.get("id") or ""
        if not elem_id:
            for i in range(1000):
                candidate = f"inkstitch{i}" if i else "inkstitch"
                if candidate not in seen_ids:
                    elem_id = candidate
                    break
        seen_ids.add(elem_id)

        try:
            if implicit_paint is not None:
                has_fill, has_stroke = implicit_paint
                stitch_type = "fill" if has_fill else "stroke"
            else:
                stitch_type = _infer_stitch_type(node, inkstitch_attrs)
            d_attr = _shape_to_d(node) or ""
            is_closed = None
            if d_attr:
                is_closed = "z" in d_attr.lower()
                if is_closed:
                    closed_path_count += 1
                else:
                    open_path_count += 1

            layer_id, layer_name = _get_layer_info(node)
            entry: dict[str, Any] = {
                "id": elem_id,
                "stitch_type": stitch_type,
                "params": inkstitch_attrs,
                "visible": _is_visible(node),
                "transform_present": bool(node.get("transform")),
                "layer_id": layer_id,
                "layer_name": layer_name,
                "style_summary": _style_summary(node),
                "is_closed_path": is_closed,
            }

            if include_geometry:
                # Prefer O(1) analytics for circle/ellipse/rect. Converting those
                # to arc path 'd' and calling svgelements.length() can take ~45s.
                analytical = _analytical_shape_metrics(node, scale_mm)
                if analytical is not None:
                    entry["_precomputed_metrics"] = analytical
                    entry["node_count"] = 4
                    entry["segment_count"] = 4
                    total_node += 4
                    total_seg += 4
                elif d_attr:
                    geom = _path_geometry_from_d(d_attr)
                    if geom:
                        entry["node_count"] = geom[0]
                        entry["segment_count"] = geom[1]
                        total_node += geom[0]
                        total_seg += geom[1]
                    entry["_d_attr"] = d_attr

            stitch_type_counts[stitch_type] = stitch_type_counts.get(stitch_type, 0) + 1
            if entry["transform_present"]:
                transformed_count += 1
            elements.append(entry)
        except Exception as exc:
            parse_warnings.append({"element_id": elem_id, "message": str(exc)})
            elements.append({"id": elem_id, "parse_error": str(exc)})

    element_count = len([e for e in elements if "parse_error" not in e])
    total_path_mm, design_bbox = _enrich_element_geometry(elements, scale_mm)
    for entry in elements:
        entry.pop("_d_attr", None)
        entry.pop("_precomputed_metrics", None)

    summary = {
        "document_name": Path(document_name).name,
        "page_size_mm": page_mm,
        "viewBox": root.get("viewBox"),
        "element_count": element_count,
        "stitch_type_counts": stitch_type_counts,
        "total_node_count": total_node if include_geometry else None,
        "total_segment_count": total_seg if include_geometry else None,
        "total_path_length_mm": total_path_mm,
        "design_bounding_box_mm": design_bbox,
        "hidden_layer_count": hidden_layer_count,
        "open_path_count": open_path_count,
        "closed_path_count": closed_path_count,
        "transformed_element_count": transformed_count,
        "estimated_complexity_hint": _estimated_complexity_hint(total_node, element_count),
    }

    return {
        "elements": elements,
        "summary": summary,
        "parse_warnings": parse_warnings,
        "session_context": {
            "fabric_type": None,
            "garment_type": None,
            "symptom": None,
            "hoop_size_mm": None,
        },
    }


def design_report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False)
