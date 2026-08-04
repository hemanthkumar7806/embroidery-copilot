#!/usr/bin/env python3
"""Inkscape extension: upload the current SVG and open the chat UI in the browser.

One click — no settings dialog. Defaults to the hosted AWS backend.
Optional override: INKSCAPE_AI_BASE_URL=http://127.0.0.1:8000 for local.

HTTP transport (best practice on Windows Inkscape):
Inkscape ships a stripped Python whose urllib often hangs on POST to localhost
even when the server has already received the body. System curl.exe is reliable,
so we prefer curl for health checks and uploads; urllib is only a fallback.

Local vs hosted:
- localhost → sync upload in-process (fast, ~1s), then open browser
- hosted → detached background worker so Inkscape never freezes on cold starts
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import uuid
import warnings
import webbrowser
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from urllib import error, request

# Inkscape surfaces anything on the extension's stderr as a popup dialog, so keep
# it clean (e.g. the benign "subprocess still running" ResourceWarning at exit).
warnings.filterwarnings("ignore", category=ResourceWarning)

try:  # inkex only exists when Inkscape launches us; the worker does not need it.
    import inkex

    _HAVE_INKEX = True
except Exception:  # pragma: no cover - worker process path
    inkex = None  # type: ignore[assignment]
    _HAVE_INKEX = False

DEFAULT_URL = "https://stitchbase.duckdns.org"
PROBE_TIMEOUT_S = 3
# Real designs run to hundreds of KB and the session write goes to a remote Postgres,
# so a legitimate upload can take several seconds. Timing out early just retries and
# leaves behind duplicate orphan sessions.
UPLOAD_TIMEOUT_S = 90
# Background worker (hosted only) can poll briefly if the server is still starting.
WAKE_POLL_S = 2
WAKE_POLL_ATTEMPTS = 5
UPLOAD_RETRIES = 2
# Local is always-on and fast. One attempt is enough once geometry is O(1).
LOCAL_PROBE_TIMEOUT_S = 3
LOCAL_UPLOAD_TIMEOUT_S = 60
LOCAL_UPLOAD_RETRIES = 1
SIDECAR_SUFFIX = ".inkscape-ai.json"

# Agent command loop (applies 🟢 fixes into the live document).
AGENT_POLL_S = 2
AGENT_IDLE_TIMEOUT_S = 30 * 60
AGENT_ACTION_TIMEOUT_S = 20

# SVG namespaces we resolve when reading attributes off an exported document.
_AGENT_NS = {
    "inkstitch": "http://inkstitch.org/namespace",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
    "svg": "http://www.w3.org/2000/svg",
}

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


def _find_curl() -> str | None:
    """Prefer Windows system curl — Inkscape's urllib hangs on local POST."""
    explicit = os.environ.get("INKSCAPE_AI_CURL", "").strip()
    candidates = [
        explicit,
        shutil.which("curl") or "",
        r"C:\Windows\System32\curl.exe",
        r"C:\Windows\SysWOW64\curl.exe",
    ]
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


_CURL = _find_curl()


def _base_url() -> str:
    env = os.environ.get("INKSCAPE_AI_BASE_URL", "").strip()
    return (env or DEFAULT_URL).rstrip("/")


def _is_local(base_url: str) -> bool:
    host = base_url.lower().split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    return host in ("localhost", "127.0.0.1", "::1")


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
    """Return (svg_bytes, filename, saved_doc_path_or_none).

    Always serializes from Inkscape's live in-memory document when available — it
    reflects any unsaved edits (e.g. Ink/Stitch params just set via the Params
    dialog). DOCUMENT_PATH (the file's on-disk path, when it's been saved at least
    once) is only used for the filename and session sidecar, never as the source
    of the SVG bytes — reading bytes from disk would silently re-upload a stale,
    pre-edit copy until the next save.
    """
    doc_path_str = os.environ.get("DOCUMENT_PATH", "").strip()
    doc_path: Path | None = None
    if doc_path_str:
        candidate = Path(doc_path_str).expanduser()
        if candidate.is_file():
            doc_path = candidate

    document = getattr(ext, "document", None)
    if document is not None:
        buf = BytesIO()
        document.write(buf)
        filename = doc_path.name if doc_path else "untitled.svg"
        return buf.getvalue(), filename, doc_path

    if doc_path is not None:
        return doc_path.read_bytes(), doc_path.name, doc_path

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
    # Only attach SSL context for HTTPS. Passing it on HTTP can confuse some
    # Python builds (including Inkscape's) and cause hung local uploads.
    if req.full_url.lower().startswith("https:"):
        return request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT)
    return request.urlopen(req, timeout=timeout)


def _curl_run(args: list[str], timeout: float) -> tuple[int, str, str]:
    """Run curl; return (exit_code, stdout, stderr)."""
    assert _CURL is not None
    # Soft wall slightly above curl's --max-time so we can classify timeouts.
    wall = max(timeout + 3.0, 8.0)
    try:
        completed = subprocess.run(  # noqa: S603 - trusted curl invocation
            args,
            capture_output=True,
            text=True,
            timeout=wall,
            creationflags=0x08000000 if os.name == "nt" else 0,  # CREATE_NO_WINDOW
        )
        return completed.returncode, completed.stdout or "", completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("timeout") from exc


def _curl_get_ok(url: str, timeout: float) -> bool:
    args = [
        _CURL,
        "-sS",
        "-o",
        os.devnull,
        "-w",
        "%{http_code}",
        "--max-time",
        str(max(1, int(timeout))),
        "-H",
        "Connection: close",
        url,
    ]
    code, out, err = _curl_run(args, timeout)
    if code != 0:
        _log(f"curl GET failed code={code} err={err[:200]!r}")
        if code in (28, 7):  # timeout / couldn't connect
            return False
        return False
    return out.strip() == "200"


def _curl_post_svg(url: str, filename: str, data: bytes, timeout: float) -> dict:
    """Upload SVG via curl multipart — reliable on Windows Inkscape."""
    tmp = Path(tempfile.gettempdir()) / f"inkscape_ai_up_{uuid.uuid4().hex}.svg"
    # Sanitize filename for curl -F (no quotes/newlines).
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename) or "upload.svg"
    if not safe_name.lower().endswith(".svg"):
        safe_name += ".svg"
    try:
        tmp.write_bytes(data)
        # curl -F uses the path's basename unless we set filename= explicitly.
        form = f"svg_file=@{tmp};filename={safe_name};type=image/svg+xml"
        args = [
            _CURL,
            "-sS",
            "-X",
            "POST",
            "--max-time",
            str(max(1, int(timeout))),
            "-H",
            "Accept: application/json",
            "-H",
            "Connection: close",
            "-F",
            form,
            url,
        ]
        code, out, err = _curl_run(args, timeout)
        if code == 28:
            raise RuntimeError("timeout")
        if code == 7:
            raise RuntimeError(f"url_error:could not connect to {url}")
        if code != 0:
            raise RuntimeError(f"url_error:curl exit {code}: {err[:200]}")
        if not out.strip():
            raise RuntimeError("Backend returned empty response.")
        try:
            payload = json.loads(out)
        except json.JSONDecodeError as exc:
            # HTTP error pages often aren't JSON.
            raise RuntimeError(f"Backend returned non-JSON response: {out[:200]}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Backend returned unexpected JSON.")
        # curl -f would fail on HTTP errors; we parse and check session_id instead.
        if "session_id" not in payload and "detail" in payload:
            raise RuntimeError(f"Backend rejected upload: {payload.get('detail')}")
        return payload
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def _probe_health(base_url: str, timeout: float | None = None) -> bool:
    if timeout is None:
        timeout = LOCAL_PROBE_TIMEOUT_S if _is_local(base_url) else PROBE_TIMEOUT_S
    url = f"{base_url}/health"
    started = time.time()
    try:
        if _CURL:
            ok = _curl_get_ok(url, timeout)
            _log(f"health probe (curl) -> {'200' if ok else 'fail'} in {time.time() - started:.1f}s")
            return ok
        req = request.Request(url, method="GET")
        with _urlopen(req, timeout) as resp:
            ok = resp.status == 200
            _log(f"health probe (urllib) -> {resp.status} in {time.time() - started:.1f}s")
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


def _request_json_once_urllib(req: request.Request, timeout: float) -> dict:
    try:
        with _urlopen(req, timeout) as resp:
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


def _post_session_json(url: str, filename: str, data: bytes, timeout: float | None = None) -> dict:
    """POST multipart with rebuild+retry. Prefer curl on Windows."""
    local = _is_local(url.rsplit("/api/", 1)[0])
    if timeout is None:
        timeout = LOCAL_UPLOAD_TIMEOUT_S if local else UPLOAD_TIMEOUT_S
    retries = LOCAL_UPLOAD_RETRIES if local else UPLOAD_RETRIES
    last_msg = ""
    transport = "curl" if _CURL else "urllib"
    for attempt in range(1, retries + 1):
        _log(f"POST {url} attempt {attempt}/{retries} via {transport} ({len(data)} bytes)")
        started = time.time()
        try:
            if _CURL:
                result = _curl_post_svg(url, filename, data, timeout)
            else:
                body, content_type = _encode_multipart(filename, data)
                req = request.Request(
                    url,
                    data=body,
                    headers={"Content-Type": content_type, "Accept": "application/json"},
                    method="POST",
                )
                result = _request_json_once_urllib(req, timeout)
            _log(f"POST ok in {time.time() - started:.1f}s -> session {result.get('session_id')}")
            return result
        except RuntimeError as exc:
            last_msg = str(exc)
            _log(f"POST attempt {attempt} failed in {time.time() - started:.1f}s: {last_msg}")
            retryable = last_msg == "timeout" or last_msg.startswith("url_error:")
            if retryable and attempt < retries:
                time.sleep(0.5 * attempt)
                continue
            if last_msg == "timeout":
                raise RuntimeError(
                    "Upload timed out after retries.\n\n"
                    f"Is the backend running?\nURL: {_base_url()}"
                ) from exc
            if last_msg.startswith("url_error:"):
                raise RuntimeError(
                    f"Could not reach backend: {last_msg.split(':', 1)[1]}.\n"
                    f"URL: {_base_url()}"
                ) from exc
            raise
    raise RuntimeError(f"Upload failed: {last_msg}")


def _run_local_sync(
    base_url: str, filename: str, svg_bytes: bytes, doc_path: Path | None
) -> str:
    """Local path: upload in-process. Localhost is fast; no worker needed."""
    _log(f"local sync using curl={_CURL!r}")
    if not _probe_health(base_url):
        raise RuntimeError(
            "Local backend is not running.\n\n"
            "In a terminal:\n"
            "  cd BE\n"
            "  uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000\n\n"
            f"Then try again. URL: {base_url}"
        )
    return _upload_or_create_session(base_url, filename, svg_bytes, doc_path)


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
    """Start a fresh session on every Send.

    Each Send-to-AI opens its own chat session so a new design never inherits an
    earlier design's session or chat history. Set INKSCAPE_AI_REUSE_SESSION=1 to
    fall back to the old behaviour (re-use the last session for the same document
    via its sidecar).
    """
    reuse = os.environ.get("INKSCAPE_AI_REUSE_SESSION", "0").strip() in ("1", "true", "yes")
    if reuse and doc_path is not None:
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
        # Record the latest session beside the file for reference, even though we
        # no longer reuse it by default.
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

    proc = subprocess.Popen(args, **kwargs)  # noqa: S603 - trusted, self-invocation
    # Fire-and-forget: the worker is fully detached and outlives us on purpose.
    # Mark it reaped so CPython's Popen.__del__ does not emit a ResourceWarning
    # at interpreter shutdown (Inkscape would surface that on stderr as a dialog).
    proc.returncode = 0
    _log(f"worker spawned pid={proc.pid} detached tmp={tmp.name}")


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
        # This process is already detached, so host the agent loop inline: it applies
        # 🟢 fixes the user triggers in the browser, without ever blocking Inkscape.
        _agent_loop(base_url, session_id)
    except Exception as exc:  # noqa: BLE001 - detached; log and fall back
        _log(f"worker upload failed: {exc!r}")
        _open_browser(base_url)  # at least land the user on the site
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        _log("worker done")


# --------------------------------------------------------------------------- #
# Local agent: poll the backend for commands and apply them into the live doc.
#
# Runs only in a detached background process, so Inkscape is never blocked. It polls
# outbound (no inbound listener); the session id is the capability token. Every applied
# 🟢 fix is a normal Inkscape undo step, and before-values are reported so a whole batch
# can be reverted server-side.
# --------------------------------------------------------------------------- #


def _find_inkscape() -> str | None:
    explicit = os.environ.get("INKSCAPE_AI_INKSCAPE", "").strip()
    candidates = [
        explicit,
        shutil.which("inkscape") or "",
        r"C:\Program Files\Inkscape\bin\inkscape.exe",
        "/Applications/Inkscape.app/Contents/MacOS/inkscape",
        "/usr/bin/inkscape",
    ]
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def _get_json(url: str, timeout: float = 10) -> object | None:
    if _CURL:
        args = [
            _CURL, "-sS", "--max-time", str(max(1, int(timeout))),
            "-H", "Accept: application/json", "-H", "Connection: close", url,
        ]
        try:
            code, out, _err = _curl_run(args, timeout)
        except RuntimeError:
            return None
        if code != 0 or not out.strip():
            return None
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return None
    try:
        req = request.Request(url, method="GET", headers={"Accept": "application/json"})
        with _urlopen(req, timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _post_json(url: str, body: dict, timeout: float = 10) -> object | None:
    data = json.dumps(body).encode("utf-8")
    if _CURL:
        tmp = Path(tempfile.gettempdir()) / f"inkscape_ai_cmd_{uuid.uuid4().hex}.json"
        try:
            tmp.write_bytes(data)
            args = [
                _CURL, "-sS", "-X", "POST", "--max-time", str(max(1, int(timeout))),
                "-H", "Content-Type: application/json", "-H", "Accept: application/json",
                "-H", "Connection: close", "--data-binary", f"@{tmp}", url,
            ]
            code, out, _err = _curl_run(args, timeout)
            if code != 0:
                return None
            return json.loads(out) if out.strip() else {}
        except (RuntimeError, json.JSONDecodeError):
            return None
        finally:
            tmp.unlink(missing_ok=True)
    try:
        req = request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with _urlopen(req, timeout) as resp:
            txt = resp.read().decode("utf-8")
            return json.loads(txt) if txt.strip() else {}
    except Exception:
        return None


def _run_actions(inkscape: str, actions: str, timeout: float = AGENT_ACTION_TIMEOUT_S) -> tuple[bool, str]:
    """Drive the live document. Inkscape exits 0 even on unknown actions, so parse stderr."""
    args = [inkscape, "--active-window", f"--actions={actions}"]
    try:
        completed = subprocess.run(  # noqa: S603 - trusted inkscape invocation
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    err = completed.stderr or ""
    ok = completed.returncode == 0 and "could not find action" not in err and "Invalid" not in err
    if not ok:
        _log(f"actions failed rc={completed.returncode} err={err[:200]!r} actions={actions[:180]}")
    return ok, err


def _export_live_doc(inkscape: str, timeout: float = AGENT_ACTION_TIMEOUT_S) -> Path | None:
    out = Path(tempfile.gettempdir()) / f"inkscape_ai_live_{uuid.uuid4().hex}.svg"
    ok, _err = _run_actions(inkscape, f"export-filename:{out};export-do", timeout)
    if not ok or not out.exists():
        return None
    return out


def _qualify(attribute: str) -> str:
    if ":" in attribute:
        prefix, local = attribute.split(":", 1)
        uri = _AGENT_NS.get(prefix)
        if uri:
            return f"{{{uri}}}{local}"
    return attribute


def _iter_elements(svg_path: Path):
    try:
        root = ET.parse(svg_path).getroot()
    except (ET.ParseError, OSError):
        return []
    return list(root.iter())


def _read_attr(svg_path: Path, element_id: str, attribute: str) -> str | None:
    qualified = _qualify(attribute)
    for element in _iter_elements(svg_path):
        if element.get("id") == element_id:
            return element.get(qualified)
    return None


def _element_exists(svg_path: Path, element_id: str) -> bool:
    return any(element.get("id") == element_id for element in _iter_elements(svg_path))


def build_apply_actions(payload: dict) -> str:
    """Pure: build the Inkscape action string for a whitelisted apply op.

    Values are emitted with no space after the comma, since Inkscape keeps whatever
    follows it as part of the value.
    """
    op = payload.get("op")
    parts: list[str] = []
    for target in payload.get("target_ids") or []:
        parts.append(f"select-by-id:{target}")
        if op == "set-attribute":
            parts.append(f"object-set-attribute:{payload['attribute']},{payload['value']}")
        elif op == "remove-attribute":
            # No remove action exists; clearing the value is the closest safe no-op.
            parts.append(f"object-set-attribute:{payload['attribute']},")
        elif op == "simplify":
            parts.append("path-simplify")
        parts.append("select-clear")
    return ";".join(parts)


def _execute_apply(payload: dict) -> tuple[str, dict | None, dict]:
    inkscape = _find_inkscape()
    if not inkscape:
        return "failed", None, {"error": "Inkscape not found on this machine."}

    live = _export_live_doc(inkscape)
    if live is None:
        return "failed", None, {"error": "Could not read the active Inkscape document."}
    try:
        targets = payload.get("target_ids") or []
        # Wrong-document / stale guard: never apply to a doc missing the targets.
        missing = [t for t in targets if not _element_exists(live, t)]
        if missing:
            return "failed", None, {"error": f"Target(s) not in the active document: {missing}"}

        attribute = payload.get("attribute") or ("d" if payload.get("op") == "simplify" else None)
        before: dict = {}
        if attribute:
            for target in targets:
                before[target] = {"attribute": attribute, "old": _read_attr(live, target, attribute)}

        ok, err = _run_actions(inkscape, build_apply_actions(payload))
        if not ok:
            return "failed", before or None, {"error": err[:300] or "action failed"}

        # Lightweight per-fix confirm for attribute writes.
        if payload.get("op") == "set-attribute":
            after = _export_live_doc(inkscape)
            confirmed = after is not None and all(
                _read_attr(after, t, payload["attribute"]) == str(payload["value"]) for t in targets
            )
            if after is not None:
                after.unlink(missing_ok=True)
            if not confirmed:
                return "failed", before or None, {"error": "Post-apply verification failed."}
        return "done", before or None, {"ok": True}
    finally:
        live.unlink(missing_ok=True)


def _execute_highlight(payload: dict) -> tuple[str, dict | None, dict]:
    inkscape = _find_inkscape()
    if not inkscape:
        return "failed", None, {"error": "Inkscape not found on this machine."}
    parts = ["select-clear"] + [f"select-by-id:{t}" for t in payload.get("target_ids") or []]
    ok, err = _run_actions(inkscape, ";".join(parts))
    return ("done" if ok else "failed"), None, {"ok": ok, "error": None if ok else err[:200]}


def _execute_verify(payload: dict) -> tuple[str, dict | None, dict]:
    """Guided-fix verification: re-export and check the expected condition on demand."""
    inkscape = _find_inkscape()
    if not inkscape:
        return "failed", None, {"error": "Inkscape not found on this machine."}
    live = _export_live_doc(inkscape)
    if live is None:
        return "failed", None, {"error": "Could not read the active Inkscape document."}
    try:
        check = payload.get("check")
        target = payload.get("target_id")
        if check == "element_exists":
            verified = _element_exists(live, target)
        elif check == "attribute_present":
            verified = _read_attr(live, target, payload["attribute"]) is not None
        elif check == "attribute_equals":
            verified = _read_attr(live, target, payload["attribute"]) == str(payload.get("value"))
        else:
            return "done", None, {"verified": False, "detail": f"unknown check {check!r}"}
        return "done", None, {"verified": verified}
    finally:
        live.unlink(missing_ok=True)


def _execute_rescan(base_url: str, session_id: str) -> tuple[str, dict | None, dict]:
    """Re-export the live document and upload it for a silent re-analysis (Verify loop)."""
    inkscape = _find_inkscape()
    if not inkscape:
        return "failed", None, {"error": "Inkscape not found on this machine."}
    live = _export_live_doc(inkscape)
    if live is None:
        return "failed", None, {"error": "Could not read the active Inkscape document."}
    try:
        data = live.read_bytes()
        _post_session_json(
            f"{base_url}/api/v1/sessions/{session_id}/rescan", "rescan.svg", data, timeout=40
        )
        return "done", None, {"ok": True}
    except Exception as exc:  # noqa: BLE001 - detached; report failure
        return "failed", None, {"error": f"re-scan upload failed: {exc}"[:300]}
    finally:
        live.unlink(missing_ok=True)


def _handle_command(cmd: dict, base_url: str = "", session_id: str = "") -> tuple[str, dict | None, dict]:
    kind = cmd.get("kind")
    payload = cmd.get("payload") or {}
    if kind in ("apply", "revert"):
        return _execute_apply(payload)
    if kind == "highlight":
        return _execute_highlight(payload)
    if kind == "verify":
        return _execute_verify(payload)
    if kind == "rescan":
        return _execute_rescan(base_url, session_id)
    return "failed", None, {"error": f"unknown command kind {kind!r}"}


def _agent_poll_once(base_url: str, session_id: str) -> int:
    cmds = _get_json(f"{base_url}/api/v1/sessions/{session_id}/commands/pending")
    if not isinstance(cmds, list):
        return 0
    for cmd in cmds:
        if not isinstance(cmd, dict) or "id" not in cmd:
            continue
        try:
            status, before, result = _handle_command(cmd, base_url, session_id)
        except Exception as exc:  # noqa: BLE001 - detached; report failure, keep going
            _log(f"agent command {cmd.get('id')} raised: {exc!r}")
            status, before, result = "failed", None, {"error": str(exc)[:300]}
        _post_json(
            f"{base_url}/api/v1/sessions/{session_id}/commands/{cmd['id']}/ack",
            {"status": status, "before": before, "result": result},
        )
        _log(f"agent {cmd.get('kind')} {cmd['id']} -> {status}")
    return len(cmds)


def _agent_lock_active(lock: Path) -> bool:
    try:
        return (time.time() - lock.stat().st_mtime) < AGENT_IDLE_TIMEOUT_S
    except OSError:
        return False


def _agent_current_path() -> Path:
    """Machine-wide marker naming the session the live agent belongs to."""
    return Path(tempfile.gettempdir()) / "inkscape_ai_agent_current"


def _claim_agent(session_id: str) -> None:
    try:
        _agent_current_path().write_text(session_id, encoding="utf-8")
    except OSError:
        pass


def _agent_is_current(session_id: str) -> bool:
    try:
        return _agent_current_path().read_text(encoding="utf-8").strip() == session_id
    except OSError:
        return True  # no marker (or unreadable) — assume we're still the one


def _agent_loop(base_url: str, session_id: str) -> None:
    lock = Path(tempfile.gettempdir()) / f"inkscape_ai_agent_{session_id}.lock"
    if lock.exists() and _agent_lock_active(lock):
        _log(f"agent already running for session {session_id}; not starting another")
        return
    try:
        lock.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        pass
    # Every Send starts a new session; without this, each one would leave behind an
    # agent polling for 30 minutes and they'd pile up and starve the backend. Claiming
    # the marker makes older agents stand down on their next tick.
    _claim_agent(session_id)
    _log(f"agent loop start session={session_id}")
    deadline = time.time() + AGENT_IDLE_TIMEOUT_S
    try:
        while time.time() < deadline:
            if not _agent_is_current(session_id):
                _log(f"agent superseded by a newer session; exiting ({session_id})")
                return
            try:
                handled = _agent_poll_once(base_url, session_id)
            except Exception as exc:  # noqa: BLE001
                _log(f"agent poll error: {exc!r}")
                handled = 0
            if handled > 0:
                deadline = time.time() + AGENT_IDLE_TIMEOUT_S
                lock.touch()
            time.sleep(AGENT_POLL_S)
    finally:
        lock.unlink(missing_ok=True)
        _log(f"agent loop done session={session_id}")


def _spawn_agent(base_url: str, session_id: str) -> None:
    """Launch a detached agent process (used by the local sync path)."""
    args = [sys.executable, os.path.abspath(__file__), "--agent", base_url, session_id]
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x08000000
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(args, **kwargs)  # noqa: S603 - trusted self-invocation
    proc.returncode = 0
    _log(f"agent spawned pid={proc.pid} session={session_id}")


def _agent_main(argv: list[str]) -> None:
    if len(argv) < 2:
        return
    base_url = (argv[0] or _base_url()).rstrip("/")
    session_id = argv[1]
    _log("=" * 50)
    _log(f"agent main start session={session_id} base_url={base_url}")
    _agent_loop(base_url, session_id)


if _HAVE_INKEX:

    class SendToAI(inkex.EffectExtension):  # type: ignore[misc]
        """Local: sync upload (fast). Hosted: detach worker (no UI freeze)."""

        def effect(self) -> None:
            base_url = _base_url()
            _log("=" * 50)
            _log(f"effect() start base_url={base_url} debug_log={LOG_PATH}")
            try:
                svg_bytes, filename, doc_path = _resolve_document_bytes(self)
                _log(
                    f"resolved svg: filename={filename} bytes={len(svg_bytes)} "
                    f"doc_path={doc_path} local={_is_local(base_url)}"
                )
                if _is_local(base_url):
                    # Localhost is ~0.3s — sync is fine and more reliable than a
                    # detached worker (which was hanging on local HTTP uploads).
                    session_id = _run_local_sync(base_url, filename, svg_bytes, doc_path)
                    _log(f"local session ready: {session_id}")
                    _open_browser(f"{base_url}/?s={session_id}&from=inkscape")
                    # Local path returns immediately; run the agent in a detached
                    # process so it can apply 🟢 fixes without freezing Inkscape.
                    _spawn_agent(base_url, session_id)
                else:
                    _spawn_worker(svg_bytes, filename, doc_path, base_url)
            except Exception as exc:  # noqa: BLE001
                _log(f"effect() FAILED: {exc!r}")
                inkex.errormsg(f"Open in StitchBase: {exc}")
            # Hosted path returns immediately; local path returns after ~1s upload.


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker_main(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--agent":
        _agent_main(sys.argv[2:])
        return
    if _HAVE_INKEX:
        SendToAI().run()
    else:  # pragma: no cover
        sys.stderr.write("This script must be run inside Inkscape (inkex missing).\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
