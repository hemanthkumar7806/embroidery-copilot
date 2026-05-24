"""Ink/Stitch design extraction: single-pass report + geometry helpers. No AI logic."""

from __future__ import annotations

import logging
import math
import os
import re
from pathlib import Path
from typing import Any

from .document_state import classify_document_path

logger = logging.getLogger("InkscapeBridge.design_report")

INKSTITCH_NS = "http://inkstitch.org/namespace"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"


def _path_geometry_from_d(d: str) -> tuple[int, int] | None:
    if not d or not d.strip():
        return None
    try:
        import inkex
        from inkex.paths import Path as InkexPath

        p = InkexPath(d)
        segs = len(p)
        try:
            pts = len(list(p.end_points))
        except Exception:
            pts = segs
        return (pts, segs)
    except Exception:
        pass
    commands = re.findall(r"[MLHVCSQTAZ]", d, re.IGNORECASE)
    if not commands:
        return None
    seg_count = len(commands)
    node_count = sum(1 for c in commands if c.upper() != "Z")
    return (node_count, seg_count)


def _approx_path_length_uu(path) -> float | None:
    """Approximate geometric length in user units from inkex Path."""
    if path is None:
        return None
    try:
        pts = list(path.end_points)
        if len(pts) < 2:
            return None
        total = 0.0
        for i in range(1, len(pts)):
            dx = float(pts[i].x - pts[i - 1].x)
            dy = float(pts[i].y - pts[i - 1].y)
            total += math.hypot(dx, dy)
        return total
    except Exception:
        return None


def _uu_to_mm(val_uu: float, svg_root) -> float | None:
    if val_uu is None or svg_root is None:
        return None
    try:
        return float(svg_root.uutounit(val_uu, "mm"))
    except Exception:
        return None


def get_path_length_mm(element, doc) -> float | None:
    try:
        import inkex

        if not isinstance(element, inkex.PathElement):
            return None
        d = element.get("d")
        if not d:
            return None
        if not element.path:
            element.set_path(d)
        plen_uu = _approx_path_length_uu(element.path)
        if plen_uu is None:
            return None
        return _uu_to_mm(plen_uu, doc.getroot())
    except Exception:
        return None


def get_bbox_mm(element, doc) -> dict[str, float] | None:
    try:
        import inkex

        if not isinstance(element, inkex.PathElement):
            return None
        d = element.get("d")
        if d and not element.path:
            element.set_path(d)
        bb = element.bounding_box()
        if bb is None:
            return None
        w = float(bb.width)
        h = float(bb.height)
        if w <= 0 and h <= 0:
            return None
        root = doc.getroot()
        wmm = _uu_to_mm(w, root)
        hmm = _uu_to_mm(h, root)
        if wmm is None or hmm is None:
            return None
        return {"w": wmm, "h": hmm}
    except Exception:
        return None


def is_closed_path(element) -> bool | None:
    try:
        import inkex
        from inkex.paths import Path as InkexPath

        if not isinstance(element, inkex.PathElement):
            return None
        d = element.get("d", "")
        if not d:
            return None
        if "z" in d.lower():
            return True
        if not element.path:
            element.set_path(d)
        p = element.path
        if p is not None and len(p) > 0:
            try:
                if p.closed:
                    return True
            except Exception:
                pass
        try:
            ip = InkexPath(d)
            if len(ip) > 0 and ip[-1].letter.upper() == "Z":
                return True
        except Exception:
            pass
        return False
    except Exception:
        return None


def has_open_path(element) -> bool | None:
    closed = is_closed_path(element)
    if closed is None:
        return None
    return not closed


def has_transform(element) -> bool:
    try:
        t = element.get("transform")
        return bool(t and str(t).strip())
    except Exception:
        return False


def is_visible(element) -> bool:
    try:
        if element.get("display") == "none":
            return False
        vis = element.get("visibility")
        if vis == "hidden" or vis == "collapse":
            return False
        op = element.get("opacity")
        if op is not None and str(op).strip() == "0":
            return False
        st = element.get("style") or ""
        if "display:none" in st.replace(" ", ""):
            return False
        if "visibility:hidden" in st.replace(" ", ""):
            return False
        return True
    except Exception:
        return True


def get_layer_info(element) -> tuple[str | None, str | None]:
    layer_id = None
    layer_name = None
    try:
        parent = element.getparent()
        while parent is not None:
            gm = parent.get(f"{{{INKSCAPE_NS}}}groupmode")
            if gm == "layer":
                layer_id = parent.get("id") or None
                label = parent.get(f"{{{INKSCAPE_NS}}}label")
                layer_name = label or layer_id
                break
            parent = parent.getparent()
    except Exception:
        pass
    return layer_id, layer_name


def _style_summary(element) -> dict[str, str] | None:
    try:
        out: dict[str, str] = {}
        for k in ("fill", "stroke", "stroke-width", "opacity"):
            v = element.get(k)
            if v is not None and str(v).strip():
                out[k.replace("-", "_")] = str(v).strip()
        st = element.get("style")
        if st:
            out["style"] = st[:500] if len(st) > 500 else st
        return out if out else None
    except Exception:
        return None


def _path_complexity_hints(d: str | None) -> dict[str, int] | None:
    if not d:
        return None
    try:
        cmds = re.findall(r"[MLHVCSQTAZ]", d, re.IGNORECASE)
        if not cmds:
            return None
        return {"command_count": len(cmds)}
    except Exception:
        return None


def _infer_stitch_type(
    node,
    inkstitch_attrs: dict[str, str],
) -> str:
    stitch_type = "stroke"
    if inkstitch_attrs.get("satin_column") or inkstitch_attrs.get("satin_method"):
        stitch_type = "satin"
    elif inkstitch_attrs.get("stroke_method"):
        stitch_type = "stroke"
    else:
        tag = node.tag if isinstance(node.tag, str) else str(node.tag)
        tag_local = tag.split("}")[-1] if "}" in tag else tag
        if tag_local == "path":
            d = node.get("d", "")
            has_fill = node.get("fill") and node.get("fill") != "none"
            if has_fill and d and ("z" in d.lower() or "Z" in d):
                stitch_type = "fill"
        if stitch_type == "stroke" and (
            inkstitch_attrs.get("row_spacing_mm") is not None
            or inkstitch_attrs.get("fill_underlay") is not None
        ):
            stitch_type = "fill"
    return stitch_type


def _count_hidden_layers(root) -> int:
    n = 0
    try:
        for node in root.iter():
            tag = node.tag if isinstance(node.tag, str) else str(node.tag)
            local = tag.split("}")[-1] if "}" in tag else tag
            if local != "g":
                continue
            if node.get(f"{{{INKSCAPE_NS}}}groupmode") != "layer":
                continue
            st = node.get("style") or ""
            if "display:none" in st.replace(" ", "").lower():
                n += 1
                continue
            if node.get(f"{{{SODIPODI_NS}}}insensitive") == "true":
                n += 1
    except Exception as e:
        logger.warning("hidden layer scan: %s", e)
    return n


def get_page_size_mm(root) -> dict[str, float] | None:
    try:
        w = root.get("width")
        h = root.get("height")
        if not w or not h:
            return None
        ww = root.uutounit(root.unittouu(w), "mm")
        hh = root.uutounit(root.unittouu(h), "mm")
        if ww is None or hh is None:
            return None
        return {"w": float(ww), "h": float(hh)}
    except Exception:
        return None


def _estimated_complexity_hint(
    total_node_count: int,
    element_count: int,
) -> float:
    # Matches TS computeComplexityScore: node/1000, path/200, element/100 with weights 0.5, 0.3, 0.2
    path_count = element_count
    score = (
        (total_node_count / 1000.0) * 0.5
        + (path_count / 200.0) * 0.3
        + (element_count / 100.0) * 0.2
    )
    return min(float(score), 1.0)


def _data_completeness_score(
    page_size_mm: dict | None,
    viewbox_val: Any,
    total_node_count: int | None,
    total_segment_count: int | None,
    total_path_length_mm: float | None,
) -> float:
    fields = [
        page_size_mm,
        viewbox_val,
        total_node_count,
        total_segment_count,
        total_path_length_mm,
    ]
    non_null = sum(1 for f in fields if f is not None)
    return non_null / float(len(fields))


def build_design_report_payload(
    doc: Any,
    doc_path: str,
    include_geometry: bool = False,
    include_summary: bool = True,
) -> dict[str, Any]:
    import inkex  # noqa: PLC0415

    ns_prefix = "{" + INKSTITCH_NS + "}"
    root = doc.getroot()
    elements: list[dict[str, Any]] = []
    parse_warnings: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    stitch_type_counts: dict[str, int] = {}
    total_node = 0
    total_seg = 0
    total_path_len_mm: float | None = None
    open_path_count = 0
    closed_path_count = 0
    transformed_count = 0
    path_len_sum = 0.0
    path_len_known = 0

    page_mm = get_page_size_mm(root)
    vb = root.get("viewBox") or None
    hidden_layer_count = _count_hidden_layers(root)

    for node in root.iter():
        inkstitch_attrs = {
            k[len(ns_prefix) :]: v
            for k, v in node.attrib.items()
            if k.startswith(ns_prefix)
        }
        if not inkstitch_attrs:
            continue

        elem_id = node.get("id") or ""
        if not elem_id:
            base = "inkstitch"
            for i in range(1000):
                cand = f"{base}{i}" if i else base
                if cand not in seen_ids:
                    elem_id = cand
                    seen_ids.add(cand)
                    break
        else:
            seen_ids.add(elem_id)

        try:
            stitch_type = _infer_stitch_type(node, inkstitch_attrs)
            el: dict[str, Any] = {
                "id": elem_id,
                "stitch_type": stitch_type,
                "params": inkstitch_attrs,
                "path_length_mm": None,
                "avg_segment_length_mm": None,
                "bounding_box_mm": None,
                "min_dimension_mm": None,
                "is_closed_path": None,
                "has_open_path": None,
                "transform_present": has_transform(node),
                "visible": is_visible(node),
                "layer_id": None,
                "layer_name": None,
                "style_summary": None,
                "path_complexity_hints": None,
            }
            lid, lname = get_layer_info(node)
            el["layer_id"] = lid
            el["layer_name"] = lname
            el["style_summary"] = _style_summary(node)

            d_attr = node.get("d", "") if hasattr(node, "get") else ""
            el["path_complexity_hints"] = _path_complexity_hints(d_attr or None)

            pe = None
            try:
                pe = inkex.PathElement(node)
                if d_attr and not pe.path:
                    pe.set_path(d_attr)
            except Exception:
                pe = None

            if include_geometry and d_attr:
                geom = _path_geometry_from_d(d_attr)
                if geom:
                    el["node_count"] = geom[0]
                    el["segment_count"] = geom[1]
                    total_node += geom[0]
                    total_seg += geom[1]
                if pe is not None:
                    el["path_length_mm"] = get_path_length_mm(pe, doc)
                    el["bounding_box_mm"] = get_bbox_mm(pe, doc)
                    ic = is_closed_path(pe)
                    el["is_closed_path"] = ic
                    el["has_open_path"] = has_open_path(pe)
                    if ic is True:
                        closed_path_count += 1
                    elif ic is False:
                        open_path_count += 1
                    pl = el["path_length_mm"]
                    if pl is not None:
                        path_len_sum += pl
                        path_len_known += 1
                    try:
                        plen = el.get("path_length_mm")
                        sc = el.get("segment_count")
                        if plen is not None and isinstance(sc, int) and sc > 0:
                            el["avg_segment_length_mm"] = plen / sc
                    except Exception:
                        el["avg_segment_length_mm"] = None
                    try:
                        bb = el.get("bounding_box_mm")
                        if isinstance(bb, dict) and "w" in bb and "h" in bb:
                            el["min_dimension_mm"] = min(
                                float(bb["w"]),
                                float(bb["h"]),
                            )
                    except Exception:
                        el["min_dimension_mm"] = None

            stitch_type_counts[stitch_type] = stitch_type_counts.get(stitch_type, 0) + 1
            if el.get("transform_present"):
                transformed_count += 1

            elements.append(el)
        except Exception as e:
            logger.warning("element %s: %s", elem_id, e)
            parse_warnings.append({"element_id": elem_id, "message": str(e)})
            elements.append({"id": elem_id, "parse_error": str(e)})

    if path_len_known > 0:
        total_path_len_mm = path_len_sum

    summary: dict[str, Any] | None = None
    if include_summary:
        ec = len([e for e in elements if "parse_error" not in e])
        avg_segment_length_global: float | None = None
        try:
            if (
                total_path_len_mm is not None
                and include_geometry
                and total_seg > 0
            ):
                avg_segment_length_global = total_path_len_mm / total_seg
        except Exception:
            avg_segment_length_global = None
        summary = {
            "document_path": doc_path,
            "document_name": Path(doc_path).name,
            "page_size_mm": page_mm,
            "viewBox": vb,
            "element_count": ec,
            "stitch_type_counts": dict(stitch_type_counts),
            "total_node_count": total_node if include_geometry else None,
            "total_segment_count": total_seg if include_geometry else None,
            "total_path_length_mm": total_path_len_mm,
            "avg_segment_length_global": avg_segment_length_global,
            "hidden_layer_count": hidden_layer_count,
            "open_path_count": open_path_count,
            "closed_path_count": closed_path_count,
            "transformed_element_count": transformed_count,
            "estimated_complexity_hint": _estimated_complexity_hint(
                total_node if include_geometry else 0,
                ec,
            ),
            "data_completeness_score": _data_completeness_score(
                page_mm,
                vb if vb else None,
                total_node if include_geometry else None,
                total_seg if include_geometry else None,
                total_path_len_mm,
            ),
        }

    return {
        "elements": elements,
        "summary": summary,
        "parse_warnings": parse_warnings,
    }


def build_document_info_from_doc(doc: Any, doc_path: str, extended: bool = False) -> dict[str, Any]:
    """Build document info dict from an already-loaded inkex document."""
    p = Path(doc_path)
    name = p.name
    root = doc.getroot()
    out: dict[str, Any] = {
        "path": doc_path,
        "name": name,
        "width": root.get("width", ""),
        "height": root.get("height", ""),
        "viewBox": root.get("viewBox", ""),
    }
    if not extended:
        return out

    cls = classify_document_path(doc_path)
    resolved = cls["resolved_path"]
    out["page_size_mm"] = get_page_size_mm(root)
    out["bridge_document_path_resolved"] = resolved
    out["is_likely_temp_file"] = cls["is_temp_like"]
    out["is_persisted_document"] = cls["is_persisted"]
    out["document_write_allowed"] = cls["is_persisted"]
    if cls["is_temp_like"]:
        out["read_only_notice"] = (
            "This path looks temporary; MCP write tools are blocked until you save/open a real .svg "
            "and reconnect (or set INKSCAPE_AI_ALLOW_TEMP_WRITES=1 for testing)."
        )
    return out


def build_document_info_payload(doc_path: str, extended: bool = False) -> dict[str, Any]:
    """Structured document info; extended adds mm size, temp heuristics, resolved path."""
    p = Path(doc_path)
    if not p.exists():
        return {"error": "Document file not found.", "path": doc_path}
    name = p.name
    try:
        import inkex  # noqa: PLC0415

        with open(p, "rb") as f:
            doc = inkex.load_svg(f)
    except Exception as e:
        return {"path": doc_path, "name": name, "error": str(e)}

    return build_document_info_from_doc(doc, doc_path, extended=extended)
