"""Session and IPC helpers for hybrid live command prototype."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .bridge_config import get_config_dir

LIVE_SESSION_FILE = "live_session.json"
LIVE_COMMANDS_FILE = "live_commands.jsonl"
LIVE_RESULTS_DIR = "live_results"


def _config_dir() -> Path:
    d = get_config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_file_path() -> Path:
    return _config_dir() / LIVE_SESSION_FILE


def commands_file_path() -> Path:
    return _config_dir() / LIVE_COMMANDS_FILE


def results_dir_path() -> Path:
    d = _config_dir() / LIVE_RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_live_session(document_path: str, extension_pid: int, lock_status: str = "confirmed") -> dict[str, Any]:
    now_ms = int(time.time() * 1000)
    sid = f"live-{uuid.uuid4()}"
    payload: dict[str, Any] = {
        "version": 1,
        "session_id": sid,
        "document_path": document_path,
        "lock_status": lock_status,
        "extension_pid": extension_pid,
        "started_at": now_ms,
        "updated_at": now_ms,
        "commands_file": str(commands_file_path()),
        "results_dir": str(results_dir_path()),
    }
    session_file_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_live_session() -> dict[str, Any] | None:
    sf = session_file_path()
    if not sf.exists():
        return None
    try:
        return json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def touch_session_updated_at() -> None:
    sess = load_live_session()
    if not sess:
        return
    sess["updated_at"] = int(time.time() * 1000)
    session_file_path().write_text(json.dumps(sess, indent=2), encoding="utf-8")


def append_live_command(command: dict[str, Any]) -> None:
    cf = commands_file_path()
    with open(cf, "a", encoding="utf-8") as f:
        f.write(json.dumps(command, ensure_ascii=False) + "\n")


def write_live_result(command_id: str, result: dict[str, Any]) -> Path:
    p = results_dir_path() / f"{command_id}.json"
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

