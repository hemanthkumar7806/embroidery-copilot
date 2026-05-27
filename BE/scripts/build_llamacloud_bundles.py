#!/usr/bin/env python3
"""Combine docs/*.md into a few bundle files for LlamaCloud (free tier: 50 files max).

Does NOT modify anything under docs/ or inkspace-AI/.
Skips paths containing 'inkscape' or 'inkspace' (Inkscape bridge setup stays local only).

Output: BE/data/llamacloud_bundles/*.md (typically ~8 files, well under 50)

Usage:
  uv run python scripts/build_llamacloud_bundles.py
  uv run python scripts/ingest_llamacloud_bundles.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings

DOCS_ROOT = settings.DOCS_DIR.resolve()
OUT_DIR = settings.DATA_DIR / "llamacloud_bundles"
EXCLUDE_PATH_PARTS = ("inkscape", "inkspace")
MAX_BUNDLE_CHARS = 180_000


def _should_skip(rel_posix: str) -> bool:
    low = rel_posix.lower()
    return any(part in low for part in EXCLUDE_PATH_PARTS)


def _bundle_key(rel: Path) -> str:
    parts = rel.parts
    if len(parts) == 1:
        return "00-general"
    if parts[0] == "sources" and len(parts) >= 2:
        return f"sources-{parts[1]}"
    if parts[0] == "rules":
        return "rules"
    return "misc"


def _safe_bundle_filename(key: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", key.lower()).strip("-") + ".md"


def _combine_files(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in sorted(paths):
        rel = path.relative_to(DOCS_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        parts.append(f"\n\n---\n\n# Source: docs/{rel}\n\n{text}")
    header = (
        "# Combined embroidery knowledge bundle\n\n"
        "Merged from project docs for LlamaCloud indexing. "
        "Original files are unchanged under docs/.\n"
    )
    return header + "".join(parts)


def main() -> None:
    if not DOCS_ROOT.exists():
        raise SystemExit(f"Docs folder not found: {DOCS_ROOT}")

    groups: dict[str, list[Path]] = defaultdict(list)
    skipped: list[str] = []

    for path in sorted(DOCS_ROOT.rglob("*.md")):
        rel = path.relative_to(DOCS_ROOT)
        rel_posix = rel.as_posix()
        if _should_skip(rel_posix):
            skipped.append(rel_posix)
            continue
        groups[_bundle_key(rel)].append(path)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.md"):
        old.unlink()

    written: list[Path] = []
    for key in sorted(groups.keys()):
        paths = groups[key]
        combined = _combine_files(paths)
        base_name = _safe_bundle_filename(key)

        if len(combined) <= MAX_BUNDLE_CHARS:
            out = OUT_DIR / base_name
            out.write_text(combined, encoding="utf-8")
            written.append(out)
            print(f"  {out.name} <- {len(paths)} file(s), {len(combined)//1024} KB")
        else:
            # Split large groups (e.g. inkstitch) into part 1 / part 2
            mid = len(paths) // 2
            for part_idx, chunk_paths in enumerate([paths[:mid], paths[mid:]], start=1):
                chunk_text = _combine_files(chunk_paths)
                stem = base_name.removesuffix(".md")
                out = OUT_DIR / f"{stem}-part{part_idx}.md"
                out.write_text(chunk_text, encoding="utf-8")
                written.append(out)
                print(f"  {out.name} <- {len(chunk_paths)} file(s), {len(chunk_text)//1024} KB")

    print()
    print(f"Wrote {len(written)} bundle(s) to {OUT_DIR}")
    print(f"Skipped {len(skipped)} inkscape/inkspace doc(s) (left untouched in docs/):")
    for s in skipped:
        print(f"  - docs/{s}")
    print()
    print(f"LlamaCloud free tier allows 50 files/org; you need {len(written)} for full corpus.")
    print("Next: uv run python scripts/ingest_llamacloud_bundles.py")


if __name__ == "__main__":
    main()
