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


def main() -> int:
    _install_inkex_stub()
    sys.path.insert(0, str(EXT_DIR))
    import send_to_ai

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

        reused = send_to_ai._upload_or_create_session(base_url, doc.name, data, doc)
        assert reused == session_id
        print(f"Sidecar reuse session: {reused}")

    url = f"{base_url}/?s={session_id}&from=inkscape"
    print(f"Deep link:    {url}")
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
