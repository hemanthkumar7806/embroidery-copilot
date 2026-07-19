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
