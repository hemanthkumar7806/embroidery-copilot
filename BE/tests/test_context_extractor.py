"""Tests for chat context extraction."""

from app.services.context_extractor import (
    SessionContext,
    apply_context_to_report,
    extract_context,
    extract_from_text,
    user_requests_preflight,
)


def test_extract_cotton_polo():
    ctx = extract_from_text("This is for a cotton polo shirt.")
    assert ctx.fabric_type == "cotton"
    assert ctx.garment_type == "polo"


def test_extract_fleece_hoodie():
    ctx = extract_from_text("Stitching on a fleece hoodie")
    assert ctx.fabric_type == "fleece"
    assert ctx.garment_type == "hoodie"


def test_extract_save_symptom():
    ctx = extract_from_text("Inkstitch freezes and won't save as PES")
    assert ctx.symptom == "save_or_simulator_freeze"


def test_extract_hoop_size():
    ctx = extract_from_text("My hoop is 100x100 mm")
    assert ctx.hoop_size_mm == {"w": 100.0, "h": 100.0}


def test_apply_context_to_report():
    report: dict = {"session_context": {}}
    ctx = SessionContext(fabric_type="cotton", garment_type="polo", symptom="thread_break")
    apply_context_to_report(report, ctx)
    assert report["physical"]["fabric_type"] == "cotton"
    assert report["meta"]["symptom"] == "thread_break"
    assert report["session_context"]["fabric_type"] == "cotton"


def test_extract_wont_stitch_out_symptom():
    ctx = extract_from_text(
        "passes troubleshoot but won't stitch out — inkstitch freezes on stitch plan preview"
    )
    assert ctx.symptom == "save_or_simulator_freeze"


def test_user_requests_preflight():
    assert user_requests_preflight("Run a preflight check")
    assert not user_requests_preflight("Will this stitch out?")
    assert not user_requests_preflight("What stabilizer for knits?")
