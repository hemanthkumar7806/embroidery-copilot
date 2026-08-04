"""Tests for the fabric-preset + context layer (step 1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import database_service
from app.services.fabric_presets import DEFAULT, PRESETS, preset_for
from app.services.issue_element_mapper import resolve_fix, resolve_issue_targets

FILL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'xmlns:inkstitch="http://inkstitch.org/namespace" '
    'width="100mm" height="100mm" viewBox="0 0 100 100">'
    '<path id="fill1" d="M10,10 L90,10 L90,90 L10,90 Z" style="fill:#cc0000" '
    'inkstitch:row_spacing_mm="0.25"/></svg>'
).encode()


# ------------------------------- unit ------------------------------- #


def test_preset_for_known_and_unknown():
    assert preset_for("fleece").row_spacing_mm == PRESETS["fleece"].row_spacing_mm
    assert preset_for("jersey") is PRESETS["knit"]  # alias
    assert preset_for("cotton polo") is PRESETS["cotton"]  # substring fallback
    assert preset_for(None) is DEFAULT
    assert preset_for("unobtainium") is DEFAULT


def _fill_report(fabric: str | None) -> dict:
    report: dict = {
        "elements": [
            {
                "id": "fill1",
                "stitch_type": "fill",
                "bounding_box": {"x": 0, "y": 0, "w": 40, "h": 40},
                "params": {"row_spacing_mm": 0.25},
            }
        ],
        "summary": {},
    }
    if fabric:
        report["physical"] = {"fabric_type": fabric}
    return report


def test_resolve_fix_is_fabric_aware():
    # Unknown fabric -> DEFAULT value (unchanged behavior).
    report = _fill_report(None)
    targets = resolve_issue_targets("row_spacing_too_low", report)
    fix = resolve_fix("row_spacing_too_low", targets["element_ids"], report)
    assert fix is not None
    assert fix["value"] == f"{DEFAULT.row_spacing_mm:g}"  # "0.4"

    # Fleece -> fleece density, and the summary names the fabric.
    report = _fill_report("fleece")
    targets = resolve_issue_targets("row_spacing_too_low", report)
    fix = resolve_fix("row_spacing_too_low", targets["element_ids"], report)
    assert fix["value"] == f"{PRESETS['fleece'].row_spacing_mm:g}"  # "0.55"
    assert "fleece" in fix["summary"]


# --------------------------- integration ---------------------------- #


@pytest.fixture
def client():
    return TestClient(app)


def _row_spacing_fix_value(rule_engine: dict) -> str | None:
    for issue in rule_engine.get("issues", []):
        if issue["id"] == "row_spacing_too_low" and issue.get("fix"):
            return issue["fix"]["value"]
    return None


def test_context_endpoint_makes_fix_fabric_aware(client: TestClient):
    created = client.post(
        "/api/v1/sessions",
        files={"svg_file": ("fill.svg", FILL_SVG, "image/svg+xml")},
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]
    try:
        # Before setting fabric: DEFAULT value.
        rule_engine = created.json()["preflight"]["rule_engine"]
        assert _row_spacing_fix_value(rule_engine) == f"{DEFAULT.row_spacing_mm:g}"

        # Set fabric -> fix value reflects the fleece preset.
        resp = client.post(
            f"/api/v1/sessions/{session_id}/context",
            json={"fabric_type": "fleece"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["session_context"]["fabric_type"] == "fleece"
        assert _row_spacing_fix_value(body["rule_engine"]) == f"{PRESETS['fleece'].row_spacing_mm:g}"

        # Persisted: re-fetch the session, the cached rule engine keeps the fleece value.
        detail = client.get(f"/api/v1/sessions/{session_id}")
        cached = detail.json()["design_report"]["cached_rule_engine"]
        assert _row_spacing_fix_value(cached) == f"{PRESETS['fleece'].row_spacing_mm:g}"
    finally:
        try:
            database_service.delete_session(session_id)
        except Exception:
            pass
