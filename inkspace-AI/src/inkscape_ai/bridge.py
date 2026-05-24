"""TCP bridge: same JSON protocol as Blender addon; get_canvas_preview, get_document_info, execute_actions, set_document, action_list."""

import io
import json
import logging
import os
import socket
import threading
import time
import uuid
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any

from .bridge_config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    get_current_document_path,
    get_current_document_path_with_source,
    is_safe_action,
    set_current_document_path,
)
from .document_state import (
    post_write_metadata,
    writes_allowed_for_path,
    write_block_response,
)


def _inkscape_actions_are_query_only(actions: list[str]) -> bool:
    for a in actions:
        if not isinstance(a, str):
            return False
        aid = a.split(":", 1)[0].strip()
        if not aid.startswith("query-"):
            return False
    return bool(actions)
from .design_report_extract import (
    build_design_report_payload,
    build_document_info_from_doc,
    build_document_info_payload,
)
from .inkscape_cli import run_inkscape
from .live_session import (
    append_live_command,
    load_live_session,
    touch_session_updated_at,
    write_live_result,
)

logger = logging.getLogger("InkscapeBridge")

_DEBUG_LOG_PATH = r"e:\user\code\MCP-chatbot\debug-3ebe15.log"


def _debug_session_log_bridge(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "3ebe15",
                        "hypothesisId": hypothesis_id,
                        "location": location,
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None


def _get_doc_path() -> str | None:
    return get_current_document_path()


def _cmd_get_canvas_preview(params: dict) -> dict:
    max_size = params.get("max_size", 800)
    filepath = params.get("filepath")
    area = params.get("area", "page")
    if not filepath:
        return {"error": "filepath required"}
    doc_path = _get_doc_path()
    if not doc_path or not Path(doc_path).exists():
        return {"error": "No current document path set or file not found. Set INKSCAPE_DOCUMENT or run the Inkscape extension."}
    out_path = Path(filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    actions = [
        "export-area-page" if area == "page" else "export-area-drawing",
        "export-type:png",
        f"export-filename:{out_path}",
        "export-dpi:96",
        "export-do",
    ]
    cmd = [doc_path, f"--actions={';'.join(actions)}", "--batch-process"]
    try:
        run_inkscape(cmd, timeout_seconds=120, lock_path=Path(doc_path))
    except Exception as e:
        return {"error": str(e)}
    if not out_path.exists():
        return {"error": "Export did not produce output file"}
    width, height = 0, 0
    if PILImage and max_size and max_size > 0:
        try:
            with PILImage.open(out_path) as img:
                w, h = img.size
                if max(w, h) > max_size:
                    ratio = max_size / max(w, h)
                    new_w, new_h = int(w * ratio), int(h * ratio)
                    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
                    img.save(out_path, "PNG")
                    width, height = new_w, new_h
                else:
                    width, height = w, h
        except Exception as e:
            logger.warning("Resize failed: %s", e)
    if width == 0 and out_path.exists():
        try:
            with PILImage.open(out_path) as img:
                width, height = img.size
        except Exception:
            pass
    return {"success": True, "width": width, "height": height, "filepath": str(out_path)}


def _cmd_get_document_info(params: dict) -> dict:
    doc_path = _get_doc_path()
    raw_env = os.environ.get("INKSCAPE_DOCUMENT", "")
    cfg_p = None
    try:
        from .bridge_config import get_config_dir, CURRENT_DOCUMENT_FILE

        cf = get_config_dir() / CURRENT_DOCUMENT_FILE
        if cf.exists():
            cfg_p = cf.read_text(encoding="utf-8").strip()[:260]
    except OSError:
        cfg_p = "read_error"
    _debug_session_log_bridge(
        "H5",
        "bridge.py:_cmd_get_document_info",
        "resolved_path_sources",
        {
            "active_doc_path_preview": (doc_path or "")[:260],
            "inkscape_document_env_preview": (raw_env or "")[:260],
            "current_document_file_preview": cfg_p or "",
        },
    )
    if not doc_path:
        return {"error": "No current document path set."}
    extended = params.get("extended", False) is True
    payload = build_document_info_payload(doc_path, extended=extended)
    if "error" not in payload and extended:
        _p, src = get_current_document_path_with_source()
        if src:
            payload["document_path_source"] = src
    return payload


def _cmd_execute_actions(params: dict) -> dict:
    actions = params.get("actions") or []
    if not isinstance(actions, list):
        return {"error": "actions must be a list"}
    for a in actions:
        if not isinstance(a, str):
            return {"error": f"Invalid action: {a}"}
        if not is_safe_action(a):
            return {"error": f"Action not allowed (allowlist): {a}. Set INKSCAPE_MCP_ALLOW_ALL_ACTIONS=1 to allow all."}
    doc_path = _get_doc_path()
    if not doc_path or not Path(doc_path).exists():
        return {"error": "No current document path set or file not found."}
    ok, reason = writes_allowed_for_path(doc_path)
    if not ok and not _inkscape_actions_are_query_only(actions):
        return write_block_response(doc_path, reason)

    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
                                        "org.freedesktop.DBus", "/org/freedesktop/DBus",
                                        "org.freedesktop.DBus", None)
        names = proxy.call_sync("ListNames", None, Gio.DBusCallFlags.NO_AUTO_START, 5000, None)
        names_list = names.unpack()[0]
        ink_name = None
        for n in names_list:
            if "org.inkscape.Inkscape" in n:
                ink_name = n
                break
        if not ink_name:
            raise RuntimeError("Inkscape not running or not exposed on DBus")
        doc_group = Gio.DBusActionGroup.get(bus, ink_name, "/org/inkscape/Inkscape/document/1")
        for act in actions:
            if ":" in act:
                name, arg = act.split(":", 1)
                doc_group.activate_action(name, GLib.Variant.new_string(arg))
            else:
                doc_group.activate_action(act, None)
        out = {"success": True}
        if ok:
            out.update(post_write_metadata(doc_path, live_via_dbus=True))
        return out
    except ImportError:
        pass
    except Exception as e:
        logger.info("DBus path failed (%s), using CLI", e)

    acts = ["select-clear"] if any(a.startswith("select-") or a.startswith("query-") for a in actions) else []
    acts += actions
    cmd = [doc_path, f"--actions={';'.join(acts)}", "--batch-process"]
    try:
        run_inkscape(cmd, timeout_seconds=120, lock_path=Path(doc_path))
        out = {"success": True}
        if ok:
            out.update(post_write_metadata(doc_path, live_via_dbus=False))
        return out
    except Exception as e:
        return {"error": str(e)}


def _run_actions_unrestricted(actions: list[str]) -> dict:
    """Execute prevalidated actions without allowlist checks (internal live ops)."""
    doc_path = _get_doc_path()
    if not doc_path or not Path(doc_path).exists():
        return {"error": "No current document path set or file not found."}
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            None,
        )
        names = proxy.call_sync("ListNames", None, Gio.DBusCallFlags.NO_AUTO_START, 5000, None)
        names_list = names.unpack()[0]
        ink_name = None
        for n in names_list:
            if "org.inkscape.Inkscape" in n:
                ink_name = n
                break
        if not ink_name:
            raise RuntimeError("Inkscape not running or not exposed on DBus")
        doc_group = Gio.DBusActionGroup.get(bus, ink_name, "/org/inkscape/Inkscape/document/1")
        for act in actions:
            if ":" in act:
                name, arg = act.split(":", 1)
                doc_group.activate_action(name, GLib.Variant.new_string(arg))
            else:
                doc_group.activate_action(act, None)
        out = {"success": True, "apply_mode": "live_dbus"}
        out.update(post_write_metadata(doc_path, live_via_dbus=True))
        return out
    except ImportError:
        pass
    except Exception as e:
        logger.info("DBus live path failed (%s), using CLI fallback", e)
    cmd = [doc_path, f"--actions={';'.join(actions)}", "--batch-process"]
    try:
        run_inkscape(cmd, timeout_seconds=120, lock_path=Path(doc_path))
        out = {"success": True, "apply_mode": "cli_fallback"}
        out.update(post_write_metadata(doc_path, live_via_dbus=False))
        return out
    except Exception as e:
        return {"error": str(e)}


def _cmd_set_document(params: dict) -> dict:
    path = params.get("path")
    if not path or not isinstance(path, str):
        return {"error": "path required"}
    path = path.strip()
    if not path:
        return {"error": "path required"}
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"error": f"File not found: {p}"}
    set_current_document_path(str(p))
    return {"success": True, "path": str(p)}


def _cmd_action_list(_params: dict) -> dict:
    try:
        out, _ = run_inkscape(["--action-list"], timeout_seconds=10)
        items = []
        for line in out.decode("utf-8").splitlines():
            if " : " in line:
                aid, doc = line.split(" : ", 1)
                items.append({"id": aid.strip(), "doc": doc.strip()})
        return {"actions": items}
    except Exception as e:
        return {"error": str(e)}


def _cmd_get_design_report(params: dict) -> dict:
    doc_path = _get_doc_path()
    if not doc_path or not Path(doc_path).exists():
        return {"error": "No current document path set or file not found. Set INKSCAPE_DOCUMENT or run the Inkscape extension."}
    include_geometry = params.get("include_geometry", False) is True
    include_summary = params.get("include_summary", True) is True
    try:
        import inkex  # noqa: PLC0415

        with open(doc_path, "rb") as f:
            doc = inkex.load_svg(f)
        payload = build_design_report_payload(
            doc,
            doc_path,
            include_geometry=include_geometry,
            include_summary=include_summary,
        )
        out: dict[str, Any] = {
            "elements": payload["elements"],
            "parse_warnings": payload.get("parse_warnings", []),
        }
        if include_summary and payload.get("summary") is not None:
            out["summary"] = payload["summary"]
        return out
    except ImportError:
        return {"error": "inkex library not available"}
    except Exception as e:
        logger.exception("get_design_report failed")
        return {"error": str(e)}


def _cmd_get_design_context(_params: dict) -> dict:
    doc_path = _get_doc_path()
    if not doc_path:
        return {"error": "No current document path set."}
    if not Path(doc_path).exists():
        return {"error": "Document file not found.", "path": doc_path}
    try:
        import inkex  # noqa: PLC0415

        with open(doc_path, "rb") as f:
            doc = inkex.load_svg(f)
        root = doc.getroot()
        doc_info = build_document_info_from_doc(doc, doc_path, extended=True)
        payload = build_design_report_payload(
            doc,
            doc_path,
            include_geometry=True,
            include_summary=True,
        )
        summ = payload.get("summary") or {}
        canvas_metadata: dict[str, Any] = {
            "page_size_mm": summ.get("page_size_mm"),
            "viewBox": root.get("viewBox"),
        }
        try:
            canvas_metadata["document_units"] = getattr(root, "unit", None) or root.get("units")
        except Exception:
            canvas_metadata["document_units"] = None

        return {
            "document_info": doc_info,
            "design_report": {
                "elements": payload["elements"],
                "summary": payload.get("summary"),
                "parse_warnings": payload.get("parse_warnings", []),
            },
            "canvas_metadata": canvas_metadata,
        }
    except ImportError:
        return {"error": "inkex library not available"}
    except Exception as e:
        logger.exception("get_design_context failed")
        return {"error": str(e)}


def _cmd_execute_code(params: dict) -> dict:
    code = params.get("code")
    if not code or not isinstance(code, str):
        return {"error": "code parameter required (string)"}
    
    doc_path = _get_doc_path()
    if not doc_path or not Path(doc_path).exists():
        return {"error": "No current document path set or file not found. Set INKSCAPE_DOCUMENT or run the Inkscape extension."}
    ok, reason = writes_allowed_for_path(doc_path)
    if not ok:
        return write_block_response(doc_path, reason)
    
    try:
        import inkex
        
        with open(doc_path, "rb") as f:
            doc = inkex.load_svg(f)
        
        root = doc.getroot()
        
        namespace = {
            "inkex": inkex,
            "doc": doc,
            "root": root,
        }
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, namespace)
        except Exception as exec_error:
            stderr_content = stderr_capture.getvalue()
            error_msg = str(exec_error)
            if stderr_content:
                error_msg = f"{stderr_content}\n{error_msg}"
            return {"error": f"Code execution failed: {error_msg}"}
        
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()
        
        with open(doc_path, "wb") as f:
            doc.write(f)
        
        result = {"success": True}
        if stdout_content:
            result["stdout"] = stdout_content
        if stderr_content:
            result["stderr"] = stderr_content
        result.update(post_write_metadata(doc_path, live_via_dbus=False))
        return result
    except ImportError:
        return {"error": "inkex library not available"}
    except Exception as e:
        logger.exception("Code execution failed")
        return {"error": f"Failed to execute code: {str(e)}"}


def _cmd_get_live_session(_params: dict) -> dict:
    sess = load_live_session()
    if not sess:
        return {"error": "No live session available. Run Extensions → Inkscape AI → Start MCP Server."}
    return {
        "session_id": sess.get("session_id"),
        "document_path": sess.get("document_path"),
        "lock_status": sess.get("lock_status"),
        "updated_at": sess.get("updated_at"),
        "commands_file": sess.get("commands_file"),
        "results_dir": sess.get("results_dir"),
    }


def _live_actions_for_command(op: str, target: str, payload: dict) -> list[str]:
    if op == "set_color":
        mode = str(payload.get("mode", "fill")).strip().lower()
        if mode not in ("fill", "stroke"):
            raise ValueError("mode must be 'fill' or 'stroke'")
        color = str(payload.get("color", "")).strip()
        if not color:
            raise ValueError("color is required")
        return [
            "select-clear",
            f"select-by-id:{target}",
            f"object-set-property:{mode},{color}",
            "select-clear",
        ]
    if op == "translate":
        dx = payload.get("dx")
        dy = payload.get("dy")
        if dx is None or dy is None:
            raise ValueError("dx and dy are required")
        return [
            "select-clear",
            f"select-by-id:{target}",
            f"transform-translate:{dx},{dy}",
            "select-clear",
        ]
    raise ValueError(f"Unsupported live op: {op}")


def _cmd_live_command(params: dict) -> dict:
    sess = load_live_session()
    if not sess:
        return {"error": "No active live session. Start MCP Server from Inkscape first."}
    session_id = str(params.get("session_id", "")).strip()
    if not session_id:
        return {"error": "session_id required"}
    if session_id != str(sess.get("session_id", "")):
        return {"error": "Session mismatch. Refresh live session and retry."}
    if str(sess.get("lock_status", "")) not in ("confirmed", "temp"):
        return {"error": "Live session is unresolved. Save/open design and restart session."}

    op = str(params.get("op", "")).strip()
    target = str(params.get("target", "")).strip()
    payload = params.get("payload") or {}
    if not op or not target:
        return {"error": "op and target are required"}
    if not isinstance(payload, dict):
        return {"error": "payload must be an object"}

    command_id = str(params.get("command_id", "")).strip() or f"cmd-{uuid.uuid4()}"
    cmd = {
        "version": 1,
        "command_id": command_id,
        "session_id": session_id,
        "op": op,
        "target": target,
        "payload": payload,
        "timestamp": int(time.time() * 1000),
    }
    append_live_command(cmd)
    touch_session_updated_at()

    try:
        actions = _live_actions_for_command(op, target, payload)
    except ValueError as e:
        result = {"success": False, "command_id": command_id, "error": str(e)}
        write_live_result(command_id, result)
        return result

    action_result = _run_actions_unrestricted(actions)
    success = "error" not in action_result
    result = {
        "success": success,
        "command_id": command_id,
        "session_id": session_id,
        "op": op,
        "target": target,
        "payload": payload,
        "transport": "bridge_actions",
        "result": action_result,
    }
    if not success:
        result["error"] = action_result.get("error", "Live command failed")
    write_live_result(command_id, result)
    return result


def execute_command(command: dict) -> dict:
    cmd_type = command.get("type")
    params = command.get("params") or {}
    handlers = {
        "get_canvas_preview": _cmd_get_canvas_preview,
        "get_document_info": _cmd_get_document_info,
        "get_design_report": _cmd_get_design_report,
        "get_design_context": _cmd_get_design_context,
        "execute_actions": _cmd_execute_actions,
        "set_document": _cmd_set_document,
        "action_list": _cmd_action_list,
        "execute_code": _cmd_execute_code,
        "get_live_session": _cmd_get_live_session,
        "live_command": _cmd_live_command,
    }
    handler = handlers.get(cmd_type)
    if not handler:
        return {"status": "error", "message": f"Unknown command: {cmd_type}"}
    try:
        result = handler(params)
        if isinstance(result, dict) and "error" in result:
            return {"status": "error", "message": result["error"], "result": result}
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("Command %s failed", cmd_type)
        return {"status": "error", "message": str(e)}


def _handle_client(client: socket.socket) -> None:
    client.settimeout(180.0)
    buffer = b""
    try:
        while True:
            chunk = client.recv(8192)
            if not chunk:
                break
            buffer += chunk
            try:
                command = json.loads(buffer.decode("utf-8"))
                buffer = b""
                response = execute_command(command)
                client.sendall(json.dumps(response).encode("utf-8"))
            except json.JSONDecodeError:
                continue
    except (ConnectionError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass


def run_server(host: str | None = None, port: int | None = None) -> None:
    host = host or os.getenv("INKSCAPE_MCP_HOST", DEFAULT_HOST)
    port = int(port or os.getenv("INKSCAPE_MCP_PORT", str(DEFAULT_PORT)))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(1)
    sock.settimeout(1.0)
    logger.info("Inkscape MCP bridge listening on %s:%s (set INKSCAPE_MCP_HOST/INKSCAPE_MCP_PORT to change)", host, port)
    running = True

    def accept_loop() -> None:
        nonlocal running
        while running:
            try:
                client, addr = sock.accept()
                logger.info("Client connected: %s", addr)
                t = threading.Thread(target=_handle_client, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                if not running:
                    break

    try:
        accept_loop()
    finally:
        running = False
        try:
            sock.close()
        except Exception:
            pass


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    port = int(os.getenv("INKSCAPE_MCP_PORT", str(DEFAULT_PORT)))
    host = os.getenv("INKSCAPE_MCP_HOST", DEFAULT_HOST)
    run_server(host, port)


if __name__ == "__main__":
    main()
