#!/usr/bin/env python3
"""Inkscape extension: upload the current SVG and open the chat UI in the browser.

One click — no settings dialog. Defaults to hosted Render URL.
Optional override: INKSCAPE_AI_BASE_URL environment variable (advanced/local).

Free hosts sleep when idle. Best practice here:
1. Probe /health
2. If asleep, open the site in the browser (wakes it) and poll until ready
3. Upload with retries so a slow first response does not strand the user
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import time
import uuid
import webbrowser
from io import BytesIO
from pathlib import Path
from urllib import error, request

import inkex

DEFAULT_URL = "https://embroidery-ext.onrender.com"
PROBE_TIMEOUT_S = 10
UPLOAD_TIMEOUT_S = 120
WAKE_POLL_S = 5
UPLOAD_RETRIES = 3
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


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    text = str(exc).lower()
    return "timed out" in text or "timeout" in text


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


def _urlopen(req: request.Request, timeout: float):
    return request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT)


def _probe_health(base_url: str, timeout: float = PROBE_TIMEOUT_S) -> bool:
    req = request.Request(f"{base_url}/health", method="GET")
    try:
        with _urlopen(req, timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _open_browser(url: str) -> None:
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def _ensure_backend_awake(base_url: str) -> None:
    """Ensure backend answers /health without freezing Inkscape for a full minute.

    If the free host is asleep: open the site in the browser (starts wake) and
    ask the user to click again once the page loads. A long in-process wait
    makes Inkscape look frozen.
    """
    if _probe_health(base_url):
        return

    _open_browser(base_url)
    # Brief second chance — sometimes the host is mid-wake.
    time.sleep(WAKE_POLL_S)
    if _probe_health(base_url):
        return

    raise RuntimeError(
        "Server is waking up (free hosting sleeps when idle).\n\n"
        "A browser tab was opened to wake it.\n"
        "1. Wait until that page loads (can take 30–60 seconds)\n"
        "2. Click Extensions → Inkscape AI → Send to AI Assistant again\n\n"
        f"URL: {base_url}"
    )


def _request_json_once(req: request.Request) -> dict:
    try:
        with _urlopen(req, UPLOAD_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"Backend rejected upload ({exc.code}): {detail}") from exc
    except Exception as exc:
        if _is_timeout(exc):
            raise RuntimeError("timeout") from exc
        if isinstance(exc, error.URLError):
            raise RuntimeError(f"url_error:{exc.reason}") from exc
        if isinstance(exc, json.JSONDecodeError):
            raise RuntimeError(f"Backend returned non-JSON response: {exc}") from exc
        raise


def _post_session_json(url: str, filename: str, data: bytes) -> dict:
    """POST multipart with rebuild+retry (free hosts drop the first request sometimes)."""
    last_msg = ""
    for attempt in range(1, UPLOAD_RETRIES + 1):
        body, content_type = _encode_multipart(filename, data)
        req = request.Request(
            url,
            data=body,
            headers={"Content-Type": content_type, "Accept": "application/json"},
            method="POST",
        )
        try:
            return _request_json_once(req)
        except RuntimeError as exc:
            last_msg = str(exc)
            retryable = last_msg == "timeout" or last_msg.startswith("url_error:")
            if retryable and attempt < UPLOAD_RETRIES:
                time.sleep(3 * attempt)
                continue
            if last_msg == "timeout":
                raise RuntimeError(
                    "Upload timed out after retries.\n\n"
                    f"Open {_base_url()} in your browser, wait until it loads,\n"
                    "then click Send to AI Assistant again."
                ) from exc
            if last_msg.startswith("url_error:"):
                raise RuntimeError(
                    f"Could not reach backend: {last_msg.split(':', 1)[1]}.\n"
                    f"URL: {_base_url()}"
                ) from exc
            raise
    raise RuntimeError(f"Upload failed: {last_msg}")


def _create_session(base_url: str, filename: str, data: bytes) -> str:
    return _parse_session_id(
        _post_session_json(f"{base_url}/api/v1/sessions", filename, data)
    )


def _update_session(base_url: str, session_id: str, filename: str, data: bytes) -> str:
    _parse_session_id(
        _post_session_json(f"{base_url}/api/v1/sessions/{session_id}/svg", filename, data)
    )
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
            _ensure_backend_awake(base_url)
            session_id = _upload_or_create_session(base_url, filename, svg_bytes, doc_path)
        except RuntimeError as exc:
            inkex.errormsg(str(exc))
            return
        except Exception as exc:
            if _is_timeout(exc):
                inkex.errormsg(
                    "Timed out contacting the server.\n\n"
                    f"Open {base_url} in your browser, wait for the page,\n"
                    "then click Send to AI Assistant again."
                )
                return
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
