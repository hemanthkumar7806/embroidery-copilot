"""Bridge config: document path (env then file), allowlist, Inkscape binary."""

import os
from pathlib import Path

DEFAULT_PORT = 9877
DEFAULT_HOST = "localhost"

CURRENT_DOCUMENT_FILE = "current_document"
CONFIG_DIR_ENV = "INKSCAPE_AI_CONFIG_DIR"
DOCUMENT_ENV = "INKSCAPE_DOCUMENT"
ALLOW_ALL_ACTIONS_ENV = "INKSCAPE_MCP_ALLOW_ALL_ACTIONS"
INKSCAPE_BIN_ENV = "INKSCAPE_BIN"


def get_current_document_path_with_source() -> tuple[str | None, str | None]:
    doc = os.getenv(DOCUMENT_ENV)
    if doc and doc.strip():
        return doc.strip(), "env"
    config_dir = get_config_dir()
    path_file = config_dir / CURRENT_DOCUMENT_FILE
    if path_file.exists():
        try:
            t = path_file.read_text(encoding="utf-8").strip()
            if t:
                return t, "config_file"
        except OSError:
            pass
    return None, None

SAFE_ACTIONS = {
    "select-all", "select-clear", "select-by-id", "select-by-class", "select-by-element",
    "path-union", "path-difference", "path-intersection", "path-division", "path-exclusion",
    "path-simplify", "object-to-path", "object-stroke-to-path",
    "selection-group", "selection-ungroup",
    "export-area-page", "export-area-drawing", "export-type", "export-filename", "export-dpi", "export-do",
    "file-save", "file-close",
    "transform-translate", "transform-scale", "transform-rotate",
    "query-x", "query-y", "query-width", "query-height", "query-all",
}


def get_config_dir() -> Path:
    base = os.getenv(CONFIG_DIR_ENV)
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / ".config" / "inkscape-ai"


def get_current_document_path() -> str | None:
    path, _ = get_current_document_path_with_source()
    return path


def set_current_document_path(path: str) -> None:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / CURRENT_DOCUMENT_FILE).write_text(path, encoding="utf-8")


def allow_all_actions() -> bool:
    return os.getenv(ALLOW_ALL_ACTIONS_ENV, "").strip().lower() in ("1", "true", "yes")


def is_safe_action(action: str) -> bool:
    if allow_all_actions():
        return True
    aid = action.split(":", 1)[0]
    return aid in SAFE_ACTIONS
