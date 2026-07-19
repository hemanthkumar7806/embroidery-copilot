#!/usr/bin/env python3
"""Inkscape extension: upload the current SVG and open the chat UI in the browser.

One click — no settings dialog. Defaults to hosted Render URL.
Optional override: INKSCAPE_AI_BASE_URL environment variable (advanced/local).

Architecture (why it never freezes Inkscape):
Inkscape runs extensions synchronously and BLOCKS its whole UI until the script
returns. So the extension must do almost nothing in-process. It grabs the SVG,
writes it to a temp file, launches a fully DETACHED background worker, and
returns immediately. Inkscape unfreezes instantly. The worker (a second copy of
this file run with --worker, stdout/stderr silenced) does all the slow work:
wait for the free host to wake, upload, and open the browser. Because the worker
is detached with no stdout, Inkscape never shows the "script returned data"
dialog either.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import uuid
import webbrowser
from io import BytesIO
from pathlib import Path
from urllib import error, request

try:  # inkex only exists when Inkscape launches us; the worker does not need it.
    import inkex

    _HAVE_INKEX = True
except Exception:  # pragma: no cover - worker process path
    inkex = None  # type: ignore[assignment]
    _HAVE_INKEX = False

DEFAULT_URL = "https://embroidery-ext.onrender.com"
PROBE_TIMEOUT_S = 12
UPLOAD_TIMEOUT_S = 90
# Worker runs in the background, so it can afford to wait for a cold free host.
WAKE_POLL_S = 5
WAKE_POLL_ATTEMPTS = 24  # ~2 min of patient polling, no UI impact
UPLOAD_RETRIES = 3
SIDECAR_SUFFIX = ".inkscape-ai.json"

# Debug logging: on by default during beta. Disable with INKSCAPE_AI_DEBUG=0.
DEBUG = os.environ.get("INKSCAPE_AI_DEBUG", "1").strip() not in ("0", "false", "no", "")
LOG_PATH = Path(
    os.environ.get("INKSCAPE_AI_LOG", str(Path(tempfile.gettempdir()) / "inkscape_ai_debug.log"))
)


def _log(msg: str) -> None:
    if not DEBUG:
        return
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


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


def _resolve_document_bytes(ext) -> tuple[bytes, str, Path | None]:
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
    started = time.time()
    try:
        with _urlopen(req, timeout) as resp:
            ok = resp.status == 200
            _log(f"health probe -> {resp.status} in {time.time() - started:.1f}s")
            return ok
    except Exception as exc:
        _log(f"health probe FAILED in {time.time() - started:.1f}s: {exc!r}")
        return False


def _open_browser(url: str) -> None:
    try:
        webbrowser.open(url, new=2)
        _log(f"browser opened: {url}")
    except Exception as exc:
        _log(f"browser open FAILED: {exc!r}")


def _wait_until_awake(base_url: str) -> bool:
    """Poll /health until the free host is up. Returns True if awake.

    Runs in the detached worker, so waiting here never freezes Inkscape.
    """
    if _probe_health(base_url):
        return True
    _log("server appears asleep; polling health in background")
    for attempt in range(WAKE_POLL_ATTEMPTS):
        time.sleep(WAKE_POLL_S)
        if _probe_health(base_url):
            _log(f"server woke during poll (attempt {attempt + 1})")
            return True
    _log("server did not wake within poll window")
    return False


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
        _log(f"POST {url} attempt {attempt}/{UPLOAD_RETRIES} ({len(data)} bytes)")
        started = time.time()
        try:
            result = _request_json_once(req)
            _log(f"POST ok in {time.time() - started:.1f}s -> session {result.get('session_id')}")
            return result
        except RuntimeError as exc:
            last_msg = str(exc)
            _log(f"POST attempt {attempt} failed in {time.time() - started:.1f}s: {last_msg}")
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


def _spawn_worker(svg_bytes: bytes, filename: str, doc_path: Path | None, base_url: str) -> None:
    """Write the SVG to a temp file and launch a detached worker; return at once.

    This is the whole point: no network here, so Inkscape unfreezes immediately.
    """
    tmp = Path(tempfile.gettempdir()) / f"inkscape_ai_{uuid.uuid4().hex}.svg"
    tmp.write_bytes(svg_bytes)

    args = [
        sys.executable,
        os.path.abspath(__file__),
        "--worker",
        str(tmp),
        filename,
        str(doc_path) if doc_path is not None else "-",
        base_url,
    ]

    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NO_WINDOW: fully independent, no console popup.
        kwargs["creationflags"] = 0x00000008 | 0x08000000
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(args, **kwargs)  # noqa: S603 - trusted, self-invocation
    _log(f"worker spawned pid-detached tmp={tmp.name}")


def _worker_main(argv: list[str]) -> None:
    """Detached background process: wait for host, upload, open browser."""
    tmp_path = Path(argv[0])
    filename = argv[1]
    doc_arg = argv[2]
    base_url = (argv[3] if len(argv) > 3 and argv[3] else _base_url()).rstrip("/")
    doc_path = None if doc_arg in ("", "-") else Path(doc_arg)

    _log("=" * 50)
    _log(f"worker start base_url={base_url} tmp={tmp_path} doc_path={doc_path}")

    try:
        svg_bytes = tmp_path.read_bytes()
    except Exception as exc:
        _log(f"worker could not read temp svg: {exc!r}")
        return

    try:
        awake = _wait_until_awake(base_url)
        if not awake:
            # Give the user something: open the site so it wakes for a retry.
            _open_browser(base_url)
            _log("worker: host asleep, opened base_url as fallback")
            return

        session_id = _upload_or_create_session(base_url, filename, svg_bytes, doc_path)
        _log(f"worker: session ready {session_id}")
        _open_browser(f"{base_url}/?s={session_id}&from=inkscape")
    except Exception as exc:  # noqa: BLE001 - detached; log and fall back
        _log(f"worker upload failed: {exc!r}")
        _open_browser(base_url)  # at least land the user on the site
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        _log("worker done")


if _HAVE_INKEX:

    class SendToAI(inkex.EffectExtension):  # type: ignore[misc]
        """Thin, non-blocking launcher. Does no network; spawns the worker."""

        def effect(self) -> None:
            base_url = _base_url()
            _log("=" * 50)
            _log(f"effect() start base_url={base_url} debug_log={LOG_PATH}")
            try:
                svg_bytes, filename, doc_path = _resolve_document_bytes(self)
                _log(f"resolved svg: filename={filename} bytes={len(svg_bytes)} doc_path={doc_path}")
                _spawn_worker(svg_bytes, filename, doc_path, base_url)
            except Exception as exc:  # noqa: BLE001
                _log(f"effect() FAILED: {exc!r}")
                inkex.errormsg(f"Send to AI Assistant could not start: {exc}")
            # Return immediately either way — never block Inkscape's UI.


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker_main(sys.argv[2:])
        return
    if _HAVE_INKEX:
        SendToAI().run()
    else:  # pragma: no cover
        sys.stderr.write("This script must be run inside Inkscape (inkex missing).\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
