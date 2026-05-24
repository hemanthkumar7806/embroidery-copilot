"""Document path classification for read vs write policy (real file first)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .bridge_config import get_config_dir

ALLOW_TEMP_WRITES_ENV = "INKSCAPE_AI_ALLOW_TEMP_WRITES"


def allow_temp_writes() -> bool:
    return os.getenv(ALLOW_TEMP_WRITES_ENV, "").strip().lower() in ("1", "true", "yes")


def classify_document_path(path: str) -> dict:
    """
    Single source of truth for temp vs persisted heuristic.
    Writes should target is_persisted True unless allow_temp_writes().
    """
    p = Path(path).expanduser()
    exists = p.is_file()
    if exists:
        pr = p.resolve()
        resolved = str(pr)
    else:
        pr = p
        resolved = str(p)

    temp_dir = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
    path_norm = os.path.normcase(os.path.abspath(str(pr)))
    sep = os.sep
    is_os_temp = path_norm == temp_dir or path_norm.startswith(temp_dir + sep)

    try:
        cfg = get_config_dir().resolve()
        is_config_temp_doc = (
            exists
            and pr.name == "temp_document.svg"
            and pr.parent.resolve() == cfg
        )
    except OSError:
        is_config_temp_doc = False

    name_lower = pr.name.lower()
    is_ink_ext_pattern = name_lower.startswith("ink_ext_") or "ink_ext_" in name_lower

    is_temp_like = is_os_temp or is_config_temp_doc
    if is_ink_ext_pattern:
        is_temp_like = True

    is_persisted = exists and not is_temp_like

    return {
        "resolved_path": resolved,
        "exists": exists,
        "is_temp_like": is_temp_like,
        "is_persisted": is_persisted,
        "policy": {
            "is_os_temp": is_os_temp,
            "is_config_temp_document": is_config_temp_doc,
            "is_ink_ext_pattern": is_ink_ext_pattern,
        },
    }


def writes_allowed_for_path(path: str | None) -> tuple[bool, str | None]:
    if allow_temp_writes():
        return True, None
    if not path or not str(path).strip():
        return False, "No current document path set."
    p = Path(path).expanduser()
    if not p.is_file():
        return False, "No current document path set or file not found."
    cls = classify_document_path(path)
    if not cls["is_persisted"]:
        return (
            False,
            "Blocked: current document looks temporary or unsuitable for writes. "
            "Save your design to a real .svg path, open it in Inkscape, run "
            "Extensions → Inkscape AI → Start MCP Server, or call set_document "
            f"with that path. (resolved: {cls['resolved_path']})",
        )
    return True, None


def write_block_response(doc_path: str | None, reason: str) -> dict:
    cls = classify_document_path(doc_path) if doc_path else {}
    out: dict = {"error": reason}
    if doc_path:
        out["target_path"] = cls.get("resolved_path", doc_path)
        out["is_temp_like"] = cls.get("is_temp_like", True)
        out["is_persisted"] = cls.get("is_persisted", False)
    return out


def post_write_metadata(doc_path: str, *, live_via_dbus: bool) -> dict:
    cls = classify_document_path(doc_path)
    meta = {
        "target_path": cls["resolved_path"],
        "is_temp_like": cls["is_temp_like"],
        "is_persisted": cls["is_persisted"],
    }
    if live_via_dbus:
        meta["refresh_attempted"] = True
        meta["refresh_result"] = "live_via_dbus"
        return meta
    meta["refresh_attempted"] = False
    meta["refresh_result"] = "manual_reload_suggested"
    meta["reload_hint"] = (
        "Document changed on disk; reload in Inkscape (File → Reload) to see updates."
    )
    return meta
