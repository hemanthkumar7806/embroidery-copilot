"""Document context persistence and rebind support for bridge recovery."""

from __future__ import annotations

import os
from pathlib import Path

from .bridge_config import get_current_document_path


class DocumentContextManager:
    def __init__(self) -> None:
        self._last_path: str | None = None

    def remember(self, path: str) -> None:
        p = path.strip()
        if p:
            self._last_path = p

    def candidate_paths(self) -> list[str]:
        out: list[str] = []
        env_path = os.getenv("INKSCAPE_DOCUMENT", "").strip()
        if env_path:
            out.append(env_path)
        if self._last_path:
            out.append(self._last_path)
        bridge_path = get_current_document_path()
        if bridge_path:
            out.append(bridge_path)
        # preserve order while deduping
        unique: list[str] = []
        seen = set()
        for p in out:
            if p not in seen:
                unique.append(p)
                seen.add(p)
        return unique

    def first_existing_path(self) -> str | None:
        for p in self.candidate_paths():
            if Path(p).expanduser().exists():
                return str(Path(p).expanduser().resolve())
        return None
