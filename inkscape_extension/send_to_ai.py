#!/usr/bin/env python3
"""Inkscape extension: upload the current SVG to the Inkscape AI beta backend
and open the chat UI in the default browser.

Configuration:
    INKSCAPE_AI_BASE_URL  Backend root URL (default: http://localhost:8000)
"""

from __future__ import annotations

import json
import os
import sys
import uuid
import webbrowser
from io import BytesIO
from pathlib import Path
from urllib import error, request

import inkex

DEFAULT_BASE_URL = "http://localhost:8000"
UPLOAD_TIMEOUT_S = 30


def _base_url() -> str:
    raw = os.environ.get("INKSCAPE_AI_BASE_URL", "").strip()
    return (raw or DEFAULT_BASE_URL).rstrip("/")


def _resolve_document_bytes(ext: inkex.EffectExtension) -> tuple[bytes, str]:
    """Return (svg_bytes, filename).

    Prefer the on-disk file when Inkscape exposes DOCUMENT_PATH; otherwise
    serialize whatever the extension was handed so unsaved/temp documents still
    work for the beta demo.
    """
    doc_path = os.environ.get("DOCUMENT_PATH", "").strip()
    if doc_path:
        p = Path(doc_path).expanduser()
        if p.is_file():
            return p.read_bytes(), p.name

    document = getattr(ext, "document", None)
    if document is not None:
        buf = BytesIO()
        document.write(buf)
        return buf.getvalue(), "untitled.svg"

    raise RuntimeError("Unable to read SVG content from Inkscape.")


def _encode_multipart(
    filename: str, data: bytes, field_name: str = "svg_file"
) -> tuple[bytes, str]:
    boundary = f"----InkscapeAI{uuid.uuid4().hex}"
    crlf = b"\r\n"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: image/svg+xml\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = header + data + footer
    return body, f"multipart/form-data; boundary={boundary}"


def _create_session(base_url: str, filename: str, data: bytes) -> str:
    body, content_type = _encode_multipart(filename, data)
    req = request.Request(
        f"{base_url}/api/v1/sessions",
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=UPLOAD_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"Backend rejected upload ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Could not reach backend at {base_url}: {exc.reason}.\n"
            "Start the backend (uvicorn app.main:app --port 8000) or set "
            "INKSCAPE_AI_BASE_URL to the hosted URL."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Backend returned non-JSON response: {exc}") from exc

    session_id = payload.get("session_id")
    if not session_id:
        raise RuntimeError("Backend response did not include session_id.")
    return str(session_id)


class SendToAI(inkex.EffectExtension):
    def effect(self) -> None:
        base_url = _base_url()
        try:
            svg_bytes, filename = _resolve_document_bytes(self)
        except Exception as exc:
            inkex.errormsg(f"Send to AI Assistant: {exc}")
            return

        try:
            session_id = _create_session(base_url, filename, svg_bytes)
        except RuntimeError as exc:
            inkex.errormsg(str(exc))
            return
        except Exception as exc:
            inkex.errormsg(f"Unexpected error: {exc}")
            return

        url = f"{base_url}/?s={session_id}"
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass
        inkex.errormsg(
            "Sent to Inkscape AI.\n\n"
            f"Session: {session_id}\n\n"
            f"If the browser did not open automatically, visit:\n{url}"
        )


if __name__ == "__main__":
    SendToAI().run()
