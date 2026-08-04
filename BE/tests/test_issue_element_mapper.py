"""Tests for mapping rule issues to SVG element targets."""

from __future__ import annotations

from app.services.issue_element_mapper import enrich_rule_engine_payload, resolve_issue_targets
from app.services.svg_parser import build_design_report

OPEN_AND_NARROW_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkstitch="http://inkstitch.org/namespace"
     width="100mm" height="100mm" viewBox="0 0 100 100">
  <path id="open_path" d="M 10 10 L 40 10"
        inkstitch:satin_column="true" />
  <path id="closed_narrow" d="M 50 10 L 90 10 L 90 11 L 50 11 Z"
        inkstitch:satin_column="true" />
</svg>"""


def test_resolve_open_paths_targets_open_elements():
    report = build_design_report(OPEN_AND_NARROW_SVG, document_name="test.svg")
    targets = resolve_issue_targets("open_paths_present", report)
    assert "open_path" in targets["element_ids"]
    assert "closed_narrow" not in targets["element_ids"]
    assert targets["focus_bbox"] is not None


THREE_TRIANGLES_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkstitch="http://inkstitch.org/namespace"
     width="200mm" height="100mm" viewBox="0 0 200 100">
  <path id="tri_bad" d="M 10 10 L 30 10 L 20 30 Z" inkstitch:row_spacing_mm="0.15" fill="black" />
  <path id="tri_good1" d="M 80 10 L 100 10 L 90 30 Z" inkstitch:row_spacing_mm="0.45" fill="black" />
  <path id="tri_good2" d="M 150 10 L 170 10 L 160 30 Z" inkstitch:row_spacing_mm="0.45" fill="black" />
</svg>"""


def test_row_spacing_targets_only_the_offending_shape():
    """Three unrelated shapes, only one has bad row spacing — must not flag all three."""
    report = build_design_report(THREE_TRIANGLES_SVG, document_name="triangles.svg")
    targets = resolve_issue_targets("row_spacing_too_low", report)
    assert targets["element_ids"] == ["tri_bad"]


def test_row_spacing_fix_and_instances_only_touch_the_offending_shape():
    report = build_design_report(THREE_TRIANGLES_SVG, document_name="triangles.svg")
    payload = enrich_rule_engine_payload(
        report,
        {
            "issues": [
                {
                    "id": "row_spacing_too_low",
                    "category": "parameters",
                    "severity": "high",
                    "title": "Row spacing too low",
                    "detail": "x",
                    "source": "test",
                    "suggested_action": "increase",
                    "capability": "auto_fix",
                }
            ],
            "context_gaps": [],
        },
    )
    issue = payload["issues"][0]
    # Bulk fix must not sweep in the two triangles that were already fine.
    assert issue["fix"]["target_ids"] == ["tri_bad"]
    # Per-shape breakdown: one instance, its own fix, its own "was" value.
    assert len(issue["instances"]) == 1
    assert issue["instances"][0]["element_id"] == "tri_bad"
    assert issue["instances"][0]["fix"]["target_ids"] == ["tri_bad"]
    assert "0.15" in issue["instances"][0]["fix"]["summary"]


TWO_BAD_ONE_GOOD_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkstitch="http://inkstitch.org/namespace"
     width="200mm" height="100mm" viewBox="0 0 200 100">
  <path id="tri_bad" d="M 10 10 L 30 10 L 20 30 Z" inkstitch:row_spacing_mm="0.15" fill="black" />
  <path id="tri_bad2" d="M 80 10 L 100 10 L 90 30 Z" inkstitch:row_spacing_mm="0.20" fill="black" />
  <path id="tri_good" d="M 150 10 L 170 10 L 160 30 Z" inkstitch:row_spacing_mm="0.45" fill="black" />
</svg>"""


def test_row_spacing_instances_split_per_offending_shape():
    """Two of three shapes are bad -> two separate instances, each with its own value."""
    report = build_design_report(TWO_BAD_ONE_GOOD_SVG, document_name="triangles.svg")
    payload = enrich_rule_engine_payload(
        report,
        {
            "issues": [
                {
                    "id": "row_spacing_too_low",
                    "category": "parameters",
                    "severity": "high",
                    "title": "Row spacing too low",
                    "detail": "x",
                    "source": "test",
                    "suggested_action": "increase",
                    "capability": "auto_fix",
                }
            ],
            "context_gaps": [],
        },
    )
    issue = payload["issues"][0]
    assert set(issue["element_ids"]) == {"tri_bad", "tri_bad2"}
    assert len(issue["instances"]) == 2
    by_id = {inst["element_id"]: inst["fix"]["summary"] for inst in issue["instances"]}
    assert "0.15" in by_id["tri_bad"]
    assert "0.2" in by_id["tri_bad2"]


def test_enrich_rule_engine_payload_adds_element_ids():
    report = build_design_report(OPEN_AND_NARROW_SVG, document_name="test.svg")
    payload = enrich_rule_engine_payload(
        report,
        {
            "issues": [
                {
                    "id": "open_paths_present",
                    "category": "geometry",
                    "severity": "high",
                    "title": "Open paths present",
                    "detail": "x",
                    "source": "test",
                    "suggested_action": "close",
                }
            ],
            "context_gaps": [],
        },
    )
    issue = payload["issues"][0]
    assert issue["element_ids"] == ["open_path"]
    assert issue["focus_bbox"] is not None
