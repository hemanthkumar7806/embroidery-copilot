#!/usr/bin/env python3
"""Inkscape extension: upload the current SVG and open the chat UI in the browser.

One click — no settings dialog. Defaults to http://localhost:8000.
Optional override: INKSCAPE_AI_BASE_URL environment variable (advanced/hosted).
"""

from __future__ import annotations

import json
import os
import ssl
import uuid
import webbrowser
from io import BytesIO
from pathlib import Path
from urllib import error, request

import inkex

DEFAULT_URL = "https://embroidery-ext.onrender.com"
UPLOAD_TIMEOUT_S = 60
HEALTH_TIMEOUT_S = 60
SIDECAR_SUFFIX = ".inkscape-ai.json"


def _ssl_context() -> ssl.SSLContext:
    """SSL context that works on Inkscape's bundled Python.

    Windows Inkscape often ships without a CA bundle, so verifying a hosted
    HTTPS backend fails with CERTIFICATE_VERIFY_FAILED. Prefer certifi's CA
    bundle when present; otherwise fall back to an unverified context so the
    one-click flow still reaches the server.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


_SSL_CONTEXT = _ssl_context()


def _base_url() -> str:
    env = os.environ.get("INKSCAPE_AI_BASE_URL", "").strip()
    return (env or DEFAULT_URL).rstrip("/")


def _sidecar_path(doc_path: Path) -> Path:
    return doc_path.with_name(f"{doc_path.name}{SIDECAR_SUFFIX}")


def _read_sidecar(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    session_id = payload.get("session_id") if isinstance(payload, dict) else None
    return str(session_id) if session_id else None


def _write_sidecar(path: Path, session_id: str) -> None:
    """Persist session mapping beside the SVG; ignore failures on read-only dirs."""
    try:
        path.write_text(
            json.dumps({"session_id": session_id}, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _resolve_document_bytes(ext: inkex.EffectExtension) -> tuple[bytes, str, Path | None]:
    """Return (svg_bytes, filename, saved_doc_path_or_none)."""
    doc_path = os.environ.get("DOCUMENT_PATH", "").strip()
    if doc_path:
        path = Path(doc_path).expanduser()
        if path.is_file():
            return path.read_bytes(), path.name, path

    document = getattr(ext, "document", None)
    if document is not None:
        buf = BytesIO()
        document.write(buf)
        return buf.getvalue(), "untitled.svg", None

    raise RuntimeError("Unable to read SVG content from Inkscape.")


def _encode_multipart(
    filename: str, data: bytes, field_name: str = "svg_file"
) -> tuple[bytes, str]:
    boundary = f"----InkscapeAI{uuid.uuid4().hex}"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: image/svg+xml\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = header + data + footer
    return body, f"multipart/form-data; boundary={boundary}"


def _parse_session_id(payload: dict) -> str:
    session_id = payload.get("session_id")
    if not session_id:
        raise RuntimeError("Backend response did not include session_id.")
    return str(session_id)


def _request_json(req: request.Request) -> dict:
    try:
        with request.urlopen(req, timeout=UPLOAD_TIMEOUT_S, context=_SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"Backend rejected upload ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Could not reach backend: {exc.reason}.\n"
            "Start the backend: uv run python -m uvicorn app.main:app --port 8000"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Backend returned non-JSON response: {exc}") from exc


def _check_health(base_url: str) -> None:
    req = request.Request(f"{base_url}/health", method="GET")
    try:
        with request.urlopen(req, timeout=HEALTH_TIMEOUT_S, context=_SSL_CONTEXT) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Backend health check failed ({resp.status}).")
    except error.URLError as exc:
        raise RuntimeError(
            f"Backend is not reachable at {base_url}: {exc.reason}.\n"
            "Start the backend: uv run python -m uvicorn app.main:app --port 8000"
        ) from exc


def _create_session(base_url: str, filename: str, data: bytes) -> str:
    body, content_type = _encode_multipart(filename, data)
    req = request.Request(
        f"{base_url}/api/v1/sessions",
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    return _parse_session_id(_request_json(req))


def _update_session(base_url: str, session_id: str, filename: str, data: bytes) -> str:
    body, content_type = _encode_multipart(filename, data)
    req = request.Request(
        f"{base_url}/api/v1/sessions/{session_id}/svg",
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    _parse_session_id(_request_json(req))
    return session_id


def _upload_or_create_session(
    base_url: str,
    filename: str,
    data: bytes,
    doc_path: Path | None,
) -> str:
    if doc_path is not None:
        existing = _read_sidecar(_sidecar_path(doc_path))
        if existing:
            try:
                return _update_session(base_url, existing, filename, data)
            except RuntimeError as exc:
                message = str(exc).lower()
                if "404" not in message and "not found" not in message and "expired" not in message:
                    raise

    session_id = _create_session(base_url, filename, data)
    if doc_path is not None:
        _write_sidecar(_sidecar_path(doc_path), session_id)
    return session_id


class SendToAI(inkex.EffectExtension):
    def effect(self) -> None:
        base_url = _base_url()

        try:
            svg_bytes, filename, doc_path = _resolve_document_bytes(self)
        except Exception as exc:
            inkex.errormsg(f"Send to AI Assistant: {exc}")
            return

        try:
            _check_health(base_url)
            session_id = _upload_or_create_session(base_url, filename, svg_bytes, doc_path)
        except RuntimeError as exc:
            inkex.errormsg(str(exc))
            return
        except Exception as exc:
            inkex.errormsg(f"Unexpected error: {exc}")
            return

        url = f"{base_url}/?s={session_id}&from=inkscape"
        try:
            webbrowser.open(url, new=2)
        except Exception:
            inkex.errormsg(
                "Upload succeeded but the browser could not be opened.\n\n"
                f"Visit:\n{url}"
            )


if __name__ == "__main__":
    SendToAI().run()
