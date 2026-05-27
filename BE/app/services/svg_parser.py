"""Ink/Stitch design extraction from SVG bytes using lxml (no inkex)."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any

from lxml import etree

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

    for node in root.iter():
        inkstitch_attrs = {
            key[len(ns_prefix) :]: value
            for key, value in node.attrib.items()
            if key.startswith(ns_prefix)
        }
        if not inkstitch_attrs:
            continue

        elem_id = node.get("id") or ""
        if not elem_id:
            for i in range(1000):
                candidate = f"inkstitch{i}" if i else "inkstitch"
                if candidate not in seen_ids:
                    elem_id = candidate
                    break
        seen_ids.add(elem_id)

        try:
            stitch_type = _infer_stitch_type(node, inkstitch_attrs)
            d_attr = node.get("d", "")
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

            if include_geometry and d_attr:
                geom = _path_geometry_from_d(d_attr)
                if geom:
                    entry["node_count"] = geom[0]
                    entry["segment_count"] = geom[1]
                    total_node += geom[0]
                    total_seg += geom[1]

            stitch_type_counts[stitch_type] = stitch_type_counts.get(stitch_type, 0) + 1
            if entry["transform_present"]:
                transformed_count += 1
            elements.append(entry)
        except Exception as exc:
            parse_warnings.append({"element_id": elem_id, "message": str(exc)})
            elements.append({"id": elem_id, "parse_error": str(exc)})

    element_count = len([e for e in elements if "parse_error" not in e])
    summary = {
        "document_name": Path(document_name).name,
        "page_size_mm": page_mm,
        "viewBox": root.get("viewBox"),
        "element_count": element_count,
        "stitch_type_counts": stitch_type_counts,
        "total_node_count": total_node if include_geometry else None,
        "total_segment_count": total_seg if include_geometry else None,
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
    }


def design_report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False)
