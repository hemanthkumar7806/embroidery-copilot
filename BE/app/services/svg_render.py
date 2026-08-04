"""Render an SVG to a PNG for the multimodal LLM review.

Fallback chain:
  1. cairosvg  — lightweight; the intended path on the Amazon Linux prod host
     (`pip install cairosvg` + `sudo yum install cairo`).
  2. Inkscape CLI — used in local dev (Inkscape is installed here) or any host that has it.

Returns None if neither backend is available, so the review gracefully stays text-only.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.logging import logger

DEFAULT_WIDTH = 768


def _render_via_cairosvg(svg_bytes: bytes, width: int) -> bytes | None:
    try:
        import cairosvg  # type: ignore
    except Exception:
        return None  # not installed / cairo lib missing (e.g. Windows dev)
    try:
        return cairosvg.svg2png(bytestring=svg_bytes, output_width=width)
    except Exception as exc:  # noqa: BLE001 - best effort
        logger.warning("svg_render_cairosvg_failed", error=str(exc))
        return None


def _find_inkscape() -> str | None:
    candidates = [
        os.environ.get("INKSCAPE_AI_INKSCAPE", "").strip(),
        shutil.which("inkscape") or "",
        r"C:\Program Files\Inkscape\bin\inkscape.exe",
        "/usr/bin/inkscape",
    ]
    return next((p for p in candidates if p and Path(p).is_file()), None)


def _render_via_inkscape(svg_bytes: bytes, width: int) -> bytes | None:
    inkscape = _find_inkscape()
    if not inkscape:
        return None
    tmpdir = Path(tempfile.mkdtemp(prefix="svgrender_"))
    src, out = tmpdir / "in.svg", tmpdir / "out.png"
    try:
        src.write_bytes(svg_bytes)
        subprocess.run(  # noqa: S603 - trusted inkscape invocation on a file (no --active-window)
            [
                inkscape,
                "--export-type=png",
                f"--export-filename={out}",
                f"--export-width={width}",
                str(src),
            ],
            capture_output=True,
            timeout=30,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        return out.read_bytes() if out.exists() else None
    except Exception as exc:  # noqa: BLE001 - best effort
        logger.warning("svg_render_inkscape_failed", error=str(exc))
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def render_svg_to_png(svg_bytes: bytes | None, width: int = DEFAULT_WIDTH) -> bytes | None:
    """Render an SVG to PNG bytes, or None if no renderer is available."""
    if not svg_bytes:
        return None
    return _render_via_cairosvg(svg_bytes, width) or _render_via_inkscape(svg_bytes, width)
