"""MCP server: connect to bridge, expose get_canvas_screenshot, get_document_info, execute_inkscape_actions, set_document, action_list."""

import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context, FastMCP, Image

from .bridge_config import DEFAULT_HOST, DEFAULT_PORT
from .document_context_manager import DocumentContextManager
from .recovery_manager import BridgeRecoveryManager, cleanup_port_owner, load_recovery_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("InkscapeMCP")


@dataclass
class InkscapeConnection:
    host: str
    port: int
    sock: socket.socket | None = None

    def connect(self) -> bool:
        if self.sock:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info("Connected to Inkscape bridge at %s:%s", self.host, self.port)
            return True
        except Exception as e:
            logger.error("Failed to connect to bridge: %s", e)
            self.sock = None
            return False

    def disconnect(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error("Error disconnecting: %s", e)
            finally:
                self.sock = None

    def _receive_full(self, buffer_size: int = 8192) -> bytes:
        chunks = []
        self.sock.settimeout(180.0)
        while True:
            chunk = self.sock.recv(buffer_size)
            if not chunk:
                if not chunks:
                    raise ConnectionError("Connection closed")
                break
            chunks.append(chunk)
            try:
                data = b"".join(chunks)
                json.loads(data.decode("utf-8"))
                return data
            except json.JSONDecodeError:
                continue

    def send_command(self, command_type: str, params: dict[str, Any] | None = None) -> dict:
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Inkscape bridge")
        command = {"type": command_type, "params": params or {}}
        try:
            self.sock.sendall(json.dumps(command).encode("utf-8"))
            self.sock.settimeout(180.0)
            response_data = self._receive_full()
            response = json.loads(response_data.decode("utf-8"))
            if response.get("status") == "error":
                raise Exception(response.get("message", "Unknown error from bridge"))
            return response.get("result", {})
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            self.sock = None
            raise Exception(f"Connection to bridge lost: {e}") from e
        except socket.timeout:
            self.sock = None
            raise Exception("Timeout waiting for bridge response") from None


_connection: InkscapeConnection | None = None
_document_context = DocumentContextManager()
_bridge_restart_attempted = False

COMMANDS_REQUIRING_DOCUMENT = {
    "get_canvas_preview",
    "get_design_report",
    "get_design_context",
    "execute_actions",
    "execute_code",
}


def get_connection() -> InkscapeConnection:
    global _connection
    if _connection is not None:
        try:
            _connection.send_command("get_document_info")
            return _connection
        except Exception:
            try:
                _connection.disconnect()
            except Exception:
                pass
            _connection = None
    host = os.getenv("INKSCAPE_MCP_HOST", DEFAULT_HOST)
    port = int(os.getenv("INKSCAPE_MCP_PORT", str(DEFAULT_PORT)))
    _connection = InkscapeConnection(host=host, port=port)
    if not _connection.connect():
        _connection = None
        raise Exception("Could not connect to Inkscape bridge. Start the bridge (e.g. inkscape-ai-bridge or from Extensions → Inkscape AI → Start MCP Server).")
    return _connection


def _reconnect_connection() -> None:
    global _connection
    if _connection:
        try:
            _connection.disconnect()
        except Exception:
            pass
    _connection = None
    get_connection()


def _spawn_bridge_process() -> bool:
    host = os.getenv("INKSCAPE_MCP_HOST", DEFAULT_HOST)
    port = int(os.getenv("INKSCAPE_MCP_PORT", str(DEFAULT_PORT)))
    try:
        cleanup_port_owner(port)
        env = os.environ.copy()
        subprocess.Popen(
            [sys.executable, "-m", "inkscape_ai.bridge"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=(os.name != "nt"),
        )
    except Exception:
        return False
    # Quick readiness probes; keep user flow silent.
    for _ in range(5):
        try:
            with socket.create_connection((host, port), timeout=0.35):
                return True
        except Exception:
            continue
    return False


def _restart_bridge_process() -> None:
    global _bridge_restart_attempted
    if _bridge_restart_attempted:
        return
    _bridge_restart_attempted = True
    _spawn_bridge_process()


def _is_bridge_alive() -> bool:
    host = os.getenv("INKSCAPE_MCP_HOST", DEFAULT_HOST)
    port = int(os.getenv("INKSCAPE_MCP_PORT", str(DEFAULT_PORT)))
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except Exception:
        return False


def _has_document_context() -> bool:
    # Bridge tracks current document independently; local cache may be empty.
    # Avoid forcing recovery based only on local context guesses.
    return True


def _rebind_document_context() -> bool:
    conn = get_connection()
    path = _document_context.first_existing_path()
    if not path:
        return False
    try:
        conn.send_command("set_document", {"path": path})
        _document_context.remember(path)
        logger.info("document_context_rebound", path=path)
        return True
    except Exception:
        return False


def execute_with_recovery(command_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    global _bridge_restart_attempted
    _bridge_restart_attempted = False
    conn = get_connection()
    settings = load_recovery_settings(conn.host, conn.port)
    recovery = BridgeRecoveryManager(
        settings=settings,
        reconnect=_reconnect_connection,
        restart_bridge=_restart_bridge_process,
        rebind_document=_rebind_document_context,
        is_bridge_alive=_is_bridge_alive,
        has_document=_has_document_context,
    )
    recovery.preflight(require_document=command_type in COMMANDS_REQUIRING_DOCUMENT)
    return recovery.recover_and_retry(
        operation_name=command_type,
        execute_once=lambda: get_connection().send_command(command_type, params),
    )


def _fallback_message(error: Exception | str) -> str:
    text = str(error)
    lower = text.lower()
    if "blocked:" in lower or "set_document" in lower and "save your" in lower:
        return text
    if "file not found" in lower or "no current document" in lower:
        return text
    if "document" in lower:
        return "Document is unavailable. Open your SVG and run Start MCP Server."
    return "Bridge is not connected. Click Restart Bridge in Inkscape."


def _format_write_tool_result(result: dict, headline: str = "Success.") -> str:
    lines = [headline]
    if result.get("target_path"):
        lines.append(f"Target file: {result['target_path']}")
    if "is_persisted" in result:
        lines.append(f"Persisted (safe for edits): {result['is_persisted']}")
    if result.get("refresh_attempted") is not None:
        lines.append(
            f"Refresh: attempted={result.get('refresh_attempted')}, "
            f"result={result.get('refresh_result', '')}"
        )
    if result.get("reload_hint"):
        lines.append(result["reload_hint"])
    return "\n".join(lines)


def _format_live_result(result: dict, headline: str = "Live command executed.") -> str:
    lines = [headline]
    if result.get("session_id"):
        lines.append(f"Session: {result['session_id']}")
    if result.get("command_id"):
        lines.append(f"Command ID: {result['command_id']}")
    if result.get("target"):
        lines.append(f"Target element: {result['target']}")
    if result.get("op"):
        lines.append(f"Operation: {result['op']}")
    nested = result.get("result") or {}
    if nested.get("target_path"):
        lines.append(f"Target file: {nested['target_path']}")
    if nested.get("reload_hint"):
        lines.append(nested["reload_hint"])
    if not result.get("success", False):
        lines.append(f"Error: {result.get('error') or nested.get('error', 'unknown error')}")
    return "\n".join(lines)


@asynccontextmanager
async def lifespan(server: FastMCP):
    try:
        yield {}
    finally:
        global _connection
        if _connection:
            _connection.disconnect()
            _connection = None


mcp = FastMCP("InkscapeMCP", lifespan=lifespan)


@mcp.tool()
def get_canvas_screenshot(
    ctx: Context,
    max_size: int = 800,
    area: str = "page",
) -> Image:
    """Capture the current Inkscape document as a PNG image so the AI can see the design. area: 'page' or 'drawing'."""
    if area not in ("page", "drawing"):
        area = "page"
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"inkscape_preview_{os.getpid()}.png")
    try:
        result = execute_with_recovery(
            "get_canvas_preview",
            {
                "max_size": max_size,
                "filepath": temp_path,
                "area": area,
            },
        )
        if "error" in result:
            raise Exception(result["error"])
        if not os.path.exists(temp_path):
            raise Exception("Preview file was not created")
        with open(temp_path, "rb") as f:
            data = f.read()
        return Image(data=data, format="png")
    except Exception as exc:
        raise Exception(_fallback_message(exc)) from exc
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@mcp.tool()
def get_document_info(ctx: Context, extended: bool = False) -> str:
    """Get current document path, name, and dimensions (width, height, viewBox). If extended is True, adds page_size_mm, resolved path, and temp/persisted file heuristics."""
    try:
        result = execute_with_recovery("get_document_info", {"extended": extended})
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        return _fallback_message(result["error"])
    return json.dumps(result, indent=2)


@mcp.tool()
def get_design_report(
    ctx: Context,
    include_geometry: bool = False,
    include_summary: bool = True,
) -> str:
    """Get a structured report of Ink/Stitch elements: id, stitch_type, params; optional geometry (node/segment counts, path length mm, bbox, open/closed, transforms, layers). If include_summary is True (default), includes document-level summary (counts, complexity hint, data completeness). Read-only."""
    try:
        result = execute_with_recovery(
            "get_design_report",
            {
                "include_geometry": include_geometry,
                "include_summary": include_summary,
            },
        )
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        return _fallback_message(result["error"])
    return json.dumps(result, indent=2)


@mcp.tool()
def get_design_context(ctx: Context) -> str:
    """Combined JSON for rule-engine use: extended document_info, full design report (geometry + summary), and canvas_metadata (no screenshot). Single bridge round-trip; loads SVG once."""
    try:
        result = execute_with_recovery("get_design_context", {})
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        return _fallback_message(result["error"])
    return json.dumps(result, indent=2)


@mcp.tool()
def execute_inkscape_actions(ctx: Context, actions: list[str]) -> str:
    """Run Inkscape actions on the current document (e.g. select-all, transform-rotate:90). On Windows the file is updated on disk; reload in Inkscape to see changes."""
    try:
        result = execute_with_recovery("execute_actions", {"actions": actions})
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        err = result["error"]
        if isinstance(err, str):
            return _fallback_message(err)
        return _fallback_message(str(err))
    return _format_write_tool_result(result)


@mcp.tool()
def set_document(ctx: Context, path: str) -> str:
    """Set the current document path for the bridge (e.g. after opening a different file in Inkscape)."""
    try:
        result = execute_with_recovery("set_document", {"path": path})
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        return _fallback_message(result["error"])
    _document_context.remember(path)
    return f"Current document set to: {result.get('path', path)}"


@mcp.tool()
def action_list(ctx: Context) -> str:
    """List available Inkscape actions (id and short description). Use these with execute_inkscape_actions."""
    try:
        result = execute_with_recovery("action_list")
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        return _fallback_message(result["error"])
    actions = result.get("actions") or []
    lines = [f"- {a.get('id', '')}: {a.get('doc', '')}" for a in actions]
    return "\n".join(lines) if lines else "No actions returned."


@mcp.tool()
def execute_inkscape_code(ctx: Context, code: str) -> str:
    """Execute arbitrary Python code in Inkscape with access to inkex library and SVG DOM manipulation. The code has access to 'inkex', 'doc' (the SVG document), and 'root' (the SVG root element). Make sure to do it step-by-step by breaking it into smaller chunks."""
    try:
        result = execute_with_recovery("execute_code", {"code": code})
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        err = result["error"]
        if isinstance(err, str):
            return _fallback_message(err)
        return _fallback_message(str(err))

    body = _format_write_tool_result(result, headline="Code executed successfully.")
    output_parts = []
    if result.get("stdout"):
        output_parts.append(f"Output:\n{result['stdout']}")
    if result.get("stderr"):
        output_parts.append(f"Warnings/Errors:\n{result['stderr']}")
    if output_parts:
        return body + "\n\n" + "\n".join(output_parts)
    return body


@mcp.tool()
def get_live_session_status(ctx: Context) -> str:
    """Get current hybrid live session status (session id, lock status, document path)."""
    try:
        result = execute_with_recovery("get_live_session", {})
    except Exception as exc:
        return _fallback_message(exc)
    if "error" in result:
        return _fallback_message(result["error"])
    return json.dumps(result, indent=2)


@mcp.tool()
def live_set_color(ctx: Context, element_id: str, color: str, mode: str = "fill") -> str:
    """Apply live color change to element id in active Inkscape session."""
    sess = execute_with_recovery("get_live_session", {})
    if "error" in sess:
        return _fallback_message(sess["error"])
    sid = str(sess.get("session_id", "")).strip()
    if not sid:
        return "Live session unavailable. Run Start MCP Server in Inkscape and retry."
    result = execute_with_recovery(
        "live_command",
        {
            "session_id": sid,
            "op": "set_color",
            "target": element_id,
            "payload": {"color": color, "mode": mode},
        },
    )
    if "error" in result:
        return _fallback_message(result["error"])
    return _format_live_result(result, headline="Live set_color completed.")


@mcp.tool()
def live_translate(ctx: Context, element_id: str, dx: float, dy: float) -> str:
    """Translate element by dx,dy in active Inkscape live session."""
    sess = execute_with_recovery("get_live_session", {})
    if "error" in sess:
        return _fallback_message(sess["error"])
    sid = str(sess.get("session_id", "")).strip()
    if not sid:
        return "Live session unavailable. Run Start MCP Server in Inkscape and retry."
    result = execute_with_recovery(
        "live_command",
        {
            "session_id": sid,
            "op": "translate",
            "target": element_id,
            "payload": {"dx": dx, "dy": dy},
        },
    )
    if "error" in result:
        return _fallback_message(result["error"])
    return _format_live_result(result, headline="Live translate completed.")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
