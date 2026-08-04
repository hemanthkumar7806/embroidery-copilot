"""Smoke test for send_to_ai.py against a running backend.

Run:
    python inkscape_extension/tests/smoke_test.py

Stubs out `inkex` so the module imports without Inkscape installed.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = REPO_ROOT / "inkscape_extension"
SAMPLE_SVG = REPO_ROOT / "BE" / "test-fixtures" / "sample.svg"


def _install_inkex_stub() -> None:
    inkex = types.ModuleType("inkex")

    class _EffectExtensionStub:
        pass

    def _errormsg_stub(msg: str) -> None:
        print(f"[inkex.errormsg] {msg}")

    inkex.EffectExtension = _EffectExtensionStub
    inkex.errormsg = _errormsg_stub
    sys.modules["inkex"] = inkex


def _check_agent_units(send_to_ai) -> None:
    """Pure-function checks for the local agent (no Inkscape required)."""
    actions = send_to_ai.build_apply_actions(
        {"op": "set-attribute", "attribute": "inkstitch:row_spacing_mm",
         "value": "0.4", "target_ids": ["a", "b"]}
    )
    assert actions == (
        "select-by-id:a;object-set-attribute:inkstitch:row_spacing_mm,0.4;select-clear;"
        "select-by-id:b;object-set-attribute:inkstitch:row_spacing_mm,0.4;select-clear"
    ), actions
    assert send_to_ai.build_apply_actions(
        {"op": "simplify", "target_ids": ["x"]}
    ) == "select-by-id:x;path-simplify;select-clear"

    assert (
        send_to_ai._qualify("inkstitch:row_spacing_mm")
        == "{http://inkstitch.org/namespace}row_spacing_mm"
    )
    assert send_to_ai._qualify("d") == "d"

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkstitch="http://inkstitch.org/namespace">'
        '<path id="p1" d="M0,0 L1,1" inkstitch:row_spacing_mm="0.25"/></svg>'
    )
    tmp = Path(tempfile.gettempdir()) / "inkscape_ai_agent_unit.svg"
    tmp.write_text(svg, encoding="utf-8")
    try:
        assert send_to_ai._element_exists(tmp, "p1")
        assert not send_to_ai._element_exists(tmp, "nope")
        assert send_to_ai._read_attr(tmp, "p1", "inkstitch:row_spacing_mm") == "0.25"
        assert send_to_ai._read_attr(tmp, "p1", "d") == "M0,0 L1,1"
        assert send_to_ai._read_attr(tmp, "p1", "inkstitch:expand_mm") is None
    finally:
        tmp.unlink(missing_ok=True)

    status, _before, result = send_to_ai._handle_command({"kind": "bogus", "payload": {}})
    assert status == "failed" and "unknown" in result["error"]
    print("Agent unit checks: OK")


def main() -> int:
    _install_inkex_stub()
    sys.path.insert(0, str(EXT_DIR))
    import send_to_ai

    _check_agent_units(send_to_ai)

    # Prefer local backend for smoke tests; fall back to DEFAULT_URL.
    base_url = os.environ.get("INKSCAPE_AI_BASE_URL", "http://localhost:8000").rstrip("/")
    print(f"Base URL: {base_url}")

    data = SAMPLE_SVG.read_bytes()
    print(f"Sample SVG: {SAMPLE_SVG} ({len(data)} bytes)")

    body, content_type = send_to_ai._encode_multipart(SAMPLE_SVG.name, data)
    assert content_type.startswith("multipart/form-data; boundary=----InkscapeAI")
    assert b"Content-Disposition: form-data" in body
    print(f"Multipart body: {len(body)} bytes, content-type OK")

    if not send_to_ai._probe_health(base_url):
        print(f"Backend offline at {base_url} — skipping integration tests")
        print("SMOKE TEST PASSED (unit checks only)")
        return 0

    print("Health check: OK")

    session_id = send_to_ai._create_session(base_url, SAMPLE_SVG.name, data)
    print(f"Created session: {session_id}")
    assert session_id and len(session_id) > 8

    updated = send_to_ai._update_session(base_url, session_id, SAMPLE_SVG.name, data)
    assert updated == session_id
    print(f"Updated session: {updated}")

    with tempfile.TemporaryDirectory() as tmp:
        doc = Path(tmp) / "design.svg"
        doc.write_bytes(data)
        sidecar = send_to_ai._sidecar_path(doc)
        assert sidecar.name == "design.svg.inkscape-ai.json"

        send_to_ai._write_sidecar(sidecar, session_id)
        assert send_to_ai._read_sidecar(sidecar) == session_id

        # Default behavior: every Send-to-AI starts a FRESH session even with an
        # existing sidecar, so a new design never inherits a previous chat/session.
        fresh = send_to_ai._upload_or_create_session(base_url, doc.name, data, doc)
        assert fresh != session_id
        print(f"Fresh session (sidecar ignored by default): {fresh}")

        # Opt-in reuse via INKSCAPE_AI_REUSE_SESSION=1 restores the old behavior.
        send_to_ai._write_sidecar(sidecar, session_id)
        os.environ["INKSCAPE_AI_REUSE_SESSION"] = "1"
        try:
            reused = send_to_ai._upload_or_create_session(base_url, doc.name, data, doc)
            assert reused == session_id
            print(f"Reuse opt-in session: {reused}")
        finally:
            del os.environ["INKSCAPE_AI_REUSE_SESSION"]

    url = f"{base_url}/?s={session_id}&from=inkscape"
    print(f"Deep link:    {url}")
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
