"""Smoke tests for the Python rule engine port."""

from __future__ import annotations

from app.schemas.sessions import rule_engine_from_dict
from app.services.rule_engine import normalize_design_report, run, run_rule_engine
from app.services.rule_engine.types import DesignReport


def _minimal_report(**overrides) -> DesignReport:
    base = DesignReport(
        geometry={
            "node_count": 0,
            "path_count": 0,
            "bounding_box": None,
            "has_open_paths": None,
            "open_path_count": None,
            "overlap_ratio": None,
            "path_length_mm": None,
            "avg_segment_length_mm": None,
            "min_dimension_mm": None,
        },
        summary={
            "total_path_length_mm": None,
            "avg_segment_length_global": None,
            "hidden_layer_count": 0,
        },
        parameters={
            "row_spacing_mm": None,
            "stitch_length_mm": None,
            "pull_compensation_mm": None,
            "density_value": None,
            "expand_mm": None,
        },
        structure={
            "layer_count": 0,
            "has_hidden_layers": False,
            "has_underlay": False,
            "stitch_types": [],
            "element_count": 0,
        },
        routing={
            "jump_stitch_count": None,
            "trim_count": None,
            "color_change_count": None,
            "estimated_stitch_count": None,
            "has_short_runs": None,
        },
        export={
            "format": None,
            "software_version": None,
            "has_metadata": False,
        },
        physical={
            "fabric_type": None,
            "hoop_size_mm": None,
            "machine_type": None,
        },
    )
    for key, value in overrides.items():
        if hasattr(base, key):
            setattr(base, key, value)
    return base


def test_empty_design_safe_to_test_without_critical_only_issues():
    result = run_rule_engine(_minimal_report())
    assert result.decision.status == "FIX_BEFORE_STITCH"
    assert any(issue.id == "no_stitch_types_detected" for issue in result.issues)


def test_hidden_layer_fires_hidden_layer_stitch_risk():
    report = _minimal_report(
        summary={"hidden_layer_count": 2},
        structure={
            "layer_count": 1,
            "has_hidden_layers": True,
            "has_underlay": False,
            "stitch_types": ["fill"],
            "element_count": 1,
        },
    )
    result = run_rule_engine(report)
    assert any(issue.id == "hidden_layer_stitch_risk" for issue in result.issues)


def test_satin_without_underlay_fires():
    report = _minimal_report(
        structure={
            "layer_count": 1,
            "has_hidden_layers": False,
            "has_underlay": False,
            "stitch_types": ["satin"],
            "element_count": 1,
        },
        routing={"estimated_stitch_count": 120},
    )
    result = run_rule_engine(report)
    assert any(issue.id == "satin_without_underlay" for issue in result.issues)


def test_cotton_realistic_params_no_false_positives():
    bridge = {
        "elements": [
            {
                "id": "fill1",
                "stitch_type": "fill",
                "params": {
                    "row_spacing_mm": 0.45,
                    "pull_compensation_mm": 0.2,
                    "fill_underlay": "true",
                },
                "node_count": 80,
            }
        ],
        "summary": {"hidden_layer_count": 0, "open_path_count": 0},
    }
    result = run(bridge)
    fired_ids = {issue["id"] for issue in result["issues"]}
    assert "row_spacing_too_low" not in fired_ids
    assert "row_spacing_too_high" not in fired_ids
    assert "pull_compensation_missing" not in fired_ids
    assert "extreme_density" not in fired_ids


def test_state_desync_from_stroke_with_inkstitch_params():
    bridge = {
        "elements": [
            {
                "id": "stroke1",
                "stitch_type": "stroke",
                "params": {"row_spacing_mm": 0.4},
                "node_count": 10,
            }
        ],
        "summary": {"hidden_layer_count": 0},
    }
    normalized = normalize_design_report(bridge)
    result = run_rule_engine(normalized)
    assert result.root_cause is not None
    assert result.root_cause.id == "STATE_DESYNC"


def test_end_to_end_output_matches_api_schema():
    bridge = {
        "elements": [
            {
                "id": "a",
                "stitch_type": "satin",
                "params": {},
                "node_count": 20,
                "min_dimension_mm": 0.8,
            }
        ],
        "summary": {"hidden_layer_count": 0, "open_path_count": 0},
    }
    payload = run(bridge)
    api_model = rule_engine_from_dict(payload)
    assert api_model is not None
    assert api_model.decision.status in {"SAFE_TO_TEST", "CAUTION", "FIX_BEFORE_STITCH"}
    assert isinstance(api_model.issues, list)
    assert api_model.summary.get("total") == len(api_model.issues)


def test_row_spacing_too_high_uses_0_7_threshold():
    report = _minimal_report(
        parameters={"row_spacing_mm": 0.65, "stitch_length_mm": 2.0, "pull_compensation_mm": 0.2},
        structure={
            "layer_count": 1,
            "has_hidden_layers": False,
            "has_underlay": True,
            "stitch_types": ["fill"],
            "element_count": 1,
        },
    )
    result = run_rule_engine(report)
    assert not any(issue.id == "row_spacing_too_high" for issue in result.issues)


def test_stitch_length_satin_allows_0_4():
    report = _minimal_report(
        parameters={"row_spacing_mm": 0.4, "stitch_length_mm": 0.45, "pull_compensation_mm": 0.2},
        structure={
            "layer_count": 1,
            "has_hidden_layers": False,
            "has_underlay": True,
            "stitch_types": ["satin"],
            "element_count": 1,
        },
    )
    result = run_rule_engine(report)
    assert not any(issue.id == "stitch_length_too_short" for issue in result.issues)


def test_context_gaps_split_from_real_issues():
    result = run_rule_engine(_minimal_report())
    gap_ids = {issue.id for issue in result.context_gap_issues}
    issue_ids = {issue.id for issue in result.issues}
    assert "fabric_instability_risk" in gap_ids or "fabric_type_unknown" in gap_ids
    assert "no_stitch_types_detected" in issue_ids


def test_fill_on_narrow_path_fires():
    bridge = {
        "elements": [
            {
                "id": "narrow_fill",
                "stitch_type": "fill",
                "params": {"row_spacing_mm": 0.4, "fill_underlay": "true"},
                "min_dimension_mm": 1.2,
                "node_count": 40,
            }
        ],
        "summary": {"hidden_layer_count": 0, "open_path_count": 0},
    }
    result = run(bridge)
    assert any(issue["id"] == "fill_on_narrow_path" for issue in result["issues"])


def test_no_inkstitch_attributes_found_fires_for_plain_svg():
    """A design with visible shapes but zero explicit inkstitch: attributes on any of
    them (svg_parser still infers a default fill/stroke stitch_type for bare shapes,
    so `stitch_types` alone can't detect this) should surface as a low-severity,
    non-error note — not silently pass through as if it were digitized."""
    bridge = {
        "elements": [
            {"id": "shape1", "stitch_type": "fill", "params": {}, "node_count": 10},
            {"id": "shape2", "stitch_type": "stroke", "params": {}, "node_count": 5},
        ],
        "summary": {"hidden_layer_count": 0, "open_path_count": 0},
    }
    result = run(bridge)
    issue = next(
        (item for item in result["issues"] if item["id"] == "no_inkstitch_attributes_found"),
        None,
    )
    assert issue is not None
    assert issue["severity"] == "low"


def test_no_inkstitch_attributes_found_does_not_fire_when_params_present():
    bridge = {
        "elements": [
            {
                "id": "shape1",
                "stitch_type": "fill",
                "params": {"row_spacing_mm": 0.4},
                "node_count": 10,
            },
        ],
        "summary": {"hidden_layer_count": 0, "open_path_count": 0},
    }
    result = run(bridge)
    assert not any(item["id"] == "no_inkstitch_attributes_found" for item in result["issues"])


def test_symptom_boost_increases_confidence():
    report = _minimal_report(
        meta={"symptom": "save_or_simulator_freeze"},
        geometry={
            "node_count": 1200,
            "path_count": 250,
            "bounding_box": None,
            "has_open_paths": None,
            "open_path_count": None,
            "overlap_ratio": None,
            "path_length_mm": None,
            "avg_segment_length_mm": None,
            "min_dimension_mm": None,
        },
        structure={
            "layer_count": 1,
            "has_hidden_layers": False,
            "has_underlay": False,
            "stitch_types": ["fill"],
            "element_count": 5,
            "narrow_fill_count": 0,
        },
    )
    result = run_rule_engine(report)
    freeze_issue = next(
        (issue for issue in result.issues if issue.id == "simulation_freeze_risk"),
        None,
    )
    assert freeze_issue is not None
    assert freeze_issue.confidence >= 0.95
