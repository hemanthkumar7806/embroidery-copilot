"""Bridge recovery helpers: classify failures, retry, and aggressive cleanup."""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar

logger = logging.getLogger("InkscapeMCPRecovery")

T = TypeVar("T")


class BridgeState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    READY = "READY"
    RECOVERING = "RECOVERING"
    ERROR = "ERROR"


@dataclass
class RecoverySettings:
    host: str
    port: int
    mode: str = "aggressive"
    max_retries: int = 3
    backoff_ms: tuple[int, ...] = (250, 800, 1600)
    kill_policy: str = "full_aggressive"
    kill_cooldown_ms: int = 1200
    allowed_process_patterns: tuple[str, ...] = (
        "inkscape-ai-bridge",
        "inkscape_ai.bridge",
        "start_mcp.py",
        "inkscape-mcp",
    )


def _is_port_open(host: str, port: int, timeout_s: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except Exception:
        return False


def classify_error(message: str) -> str:
    lower = message.lower()
    if "not connected" in lower or "connection to bridge lost" in lower or "failed to connect" in lower:
        return "connectivity"
    if "timeout waiting for bridge response" in lower or "timeout" in lower:
        return "timeout"
    if "document file not found" in lower or "no current document path set" in lower:
        return "document_context"
    return "unknown"


def cleanup_port_owner(port: int) -> bool:
    if port <= 0:
        return False

    try:
        if sys.platform.startswith("win"):
            command = (
                "$conn = Get-NetTCPConnection -LocalPort "
                f"{port} -ErrorAction SilentlyContinue;"
                "if ($conn) {"
                " $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique;"
                " foreach ($pid in $pids) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }"
                "}"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
                text=True,
            )
            return True

        # POSIX fallback: best effort with lsof/kill
        p = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            check=False,
            capture_output=True,
            text=True,
        )
        pids = [line.strip() for line in p.stdout.splitlines() if line.strip()]
        for pid in pids:
            subprocess.run(["kill", "-TERM", pid], check=False, capture_output=True, text=True)
        return len(pids) > 0
    except Exception:
        return False


def _split_patterns(raw: str) -> tuple[str, ...]:
    parts = tuple(chunk.strip() for chunk in raw.split(",") if chunk.strip())
    return parts


def cleanup_known_helpers(patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return False
    try:
        if sys.platform.startswith("win"):
            checks = " -or ".join(
                [f"$_.ProcessName -match '{p}' -or $_.CommandLine -match '{p}'" for p in patterns]
            )
            command = (
                "$procs = Get-CimInstance Win32_Process | "
                f"Where-Object {{ ({checks}) -and ($_.ProcessName -match 'inkscape|python') }};"
                "foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
                text=True,
            )
            return True

        # POSIX fallback
        killed = False
        for pattern in patterns:
            p = subprocess.run(
                ["pgrep", "-f", pattern],
                check=False,
                capture_output=True,
                text=True,
            )
            pids = [line.strip() for line in p.stdout.splitlines() if line.strip()]
            for pid in pids:
                subprocess.run(["kill", "-TERM", pid], check=False, capture_output=True, text=True)
                killed = True
        return killed
    except Exception:
        return False


class BridgeRecoveryManager:
    def __init__(
        self,
        settings: RecoverySettings,
        reconnect: Callable[[], None],
        restart_bridge: Callable[[], None],
        rebind_document: Callable[[], bool],
        is_bridge_alive: Callable[[], bool] | None = None,
        has_document: Callable[[], bool] | None = None,
    ) -> None:
        self.settings = settings
        self._reconnect = reconnect
        self._restart_bridge = restart_bridge
        self._rebind_document = rebind_document
        self._is_bridge_alive = is_bridge_alive
        self._has_document = has_document
        self._last_kill_ts_ms = 0
        self.state = BridgeState.DISCONNECTED
        self.last_actionable_hint = "Click Restart Bridge in Inkscape."

    def preflight(self, require_document: bool) -> None:
        bridge_alive = True if self._is_bridge_alive is None else self._is_bridge_alive()
        has_document = True if not require_document else (
            True if self._has_document is None else self._has_document()
        )
        if bridge_alive and has_document:
            self.state = BridgeState.READY
            return
        self.state = BridgeState.RECOVERING
        if not bridge_alive:
            self.last_actionable_hint = "Bridge is not connected. Click Restart Bridge in Inkscape."
            self._run_recovery("connectivity")
        if require_document and not has_document:
            self.last_actionable_hint = "Document is unavailable. Open your SVG and run Start MCP Server."
            self._run_recovery("document_context")

    def recover_and_retry(
        self,
        operation_name: str,
        execute_once: Callable[[], T],
    ) -> T:
        last_error: Exception | None = None
        attempts = max(1, self.settings.max_retries)
        self.state = BridgeState.CONNECTING

        for attempt in range(1, attempts + 1):
            try:
                result = execute_once()
                self.state = BridgeState.READY
                if attempt > 1:
                    logger.info(
                        "bridge_operation_recovered",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                        },
                    )
                return result
            except Exception as exc:
                last_error = exc
                err_type = classify_error(str(exc))
                logger.warning(
                    "bridge_operation_failed",
                    extra={
                        "operation": operation_name,
                        "attempt": attempt,
                        "max_retries": attempts,
                        "error_type": err_type,
                        "error": str(exc),
                    },
                )
                if attempt >= attempts or err_type == "unknown":
                    self.state = BridgeState.ERROR
                    if err_type == "document_context":
                        self.last_actionable_hint = (
                            "Document is unavailable. Open your SVG and run Start MCP Server."
                        )
                    else:
                        self.last_actionable_hint = (
                            "Bridge is not connected. Click Restart Bridge in Inkscape."
                        )
                    break

                self._run_recovery(err_type)
                delay_ms = self.settings.backoff_ms[min(attempt - 1, len(self.settings.backoff_ms) - 1)]
                time.sleep(delay_ms / 1000.0)

        final_hint = self.last_actionable_hint
        raise Exception(final_hint) from last_error

    def _run_recovery(self, err_type: str) -> None:
        if err_type in ("connectivity", "timeout", "document_context"):
            self.state = BridgeState.RECOVERING
            self._run_cleanup()
            self._reconnect()
            self._restart_bridge()
            self._reconnect()
            self._rebind_document()
            return

    def _run_cleanup(self) -> None:
        now = int(time.time() * 1000)
        if now - self._last_kill_ts_ms < self.settings.kill_cooldown_ms:
            return
        self._last_kill_ts_ms = now

        port_killed = False
        helpers_killed = False
        if self.settings.kill_policy in ("port_only", "full_aggressive"):
            if _is_port_open(self.settings.host, self.settings.port):
                port_killed = cleanup_port_owner(self.settings.port)
        if self.settings.mode == "aggressive" and self.settings.kill_policy == "full_aggressive":
            helpers_killed = cleanup_known_helpers(self.settings.allowed_process_patterns)

        logger.info(
            "bridge_cleanup_attempted",
            extra={
                "mode": self.settings.mode,
                "kill_policy": self.settings.kill_policy,
                "port": self.settings.port,
                "port_killed": port_killed,
                "helpers_killed": helpers_killed,
            },
        )


def load_recovery_settings(host: str, port: int) -> RecoverySettings:
    mode = os.getenv("INKSCAPE_RECOVERY_MODE", "aggressive").strip().lower() or "aggressive"
    max_retries = int(os.getenv("INKSCAPE_RECOVERY_MAX_RETRIES", "3"))
    kill_policy = (
        os.getenv("INKSCAPE_RECOVERY_KILL_POLICY", "full_aggressive").strip().lower()
        or "full_aggressive"
    )
    kill_cooldown_ms = int(os.getenv("INKSCAPE_RECOVERY_KILL_COOLDOWN_MS", "1200"))
    raw_patterns = os.getenv(
        "INKSCAPE_RECOVERY_ALLOWED_PROCESS_PATTERNS",
        "inkscape-ai-bridge,inkscape_ai.bridge,start_mcp.py,inkscape-mcp",
    )
    patterns = _split_patterns(raw_patterns)
    raw = os.getenv("INKSCAPE_RECOVERY_BACKOFF_MS", "250,800,1600")
    backoff = tuple(int(chunk.strip()) for chunk in raw.split(",") if chunk.strip())
    if not backoff:
        backoff = (250, 800, 1600)
    return RecoverySettings(
        host=host,
        port=port,
        mode=mode,
        max_retries=max_retries,
        backoff_ms=backoff,
        kill_policy=kill_policy,
        kill_cooldown_ms=kill_cooldown_ms,
        allowed_process_patterns=patterns,
    )
