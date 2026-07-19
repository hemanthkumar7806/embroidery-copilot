"""Tests for SVG path geometry enrichment."""

from app.services.svg_parser import build_design_report

SQUARE_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkstitch="http://inkstitch.org/namespace"
     width="100mm" height="100mm" viewBox="0 0 100 100">
  <path id="square" d="M 10 10 L 90 10 L 90 90 L 10 90 Z"
        inkstitch:row_spacing_mm="0.4" />
</svg>"""


def test_build_design_report_computes_path_geometry():
    report = build_design_report(SQUARE_SVG, document_name="square.svg")
    element = report["elements"][0]
    assert element["id"] == "square"
    assert element.get("path_length_mm") is not None
    assert element.get("min_dimension_mm") is not None
    assert element["min_dimension_mm"] > 50
    bbox = element.get("bounding_box")
    assert bbox is not None
    assert bbox["x"] == 10
    assert bbox["y"] == 10
    assert bbox["w"] == 80
    assert bbox["h"] == 80
    assert report["summary"].get("total_path_length_mm") is not None
    assert report["summary"].get("design_bounding_box_mm") is not None
