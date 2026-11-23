#!/usr/bin/env python3
"""Build the Inkscape AI extension delivery zip.

Packs the extension + installers under a single top-level folder and sets the
Unix executable bit on the shell installers so macOS/Linux users can run them
without a manual chmod (Windows' Compress-Archive cannot preserve this).
"""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "inkscape_extension"
OUT_DIR = ROOT / "dist"
TOP_LEVEL = "StitchBase"
OUT_ZIP = OUT_DIR / f"{TOP_LEVEL}.zip"

# (filename, is_executable)
FILES = [
    ("send_to_ai.py", False),
    ("send_to_ai.inx", False),
    ("INSTALL.txt", False),
    ("Install-Windows.bat", False),
    ("install.ps1", False),
    ("Install-Mac.command", True),
    ("Install-Linux.sh", True),
]

EXEC_ATTR = (stat.S_IFREG | 0o755) << 16
DATA_ATTR = (stat.S_IFREG | 0o644) << 16


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()

    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, is_exec in FILES:
            src = SRC_DIR / name
            data = src.read_bytes()
            info = zipfile.ZipInfo(f"{TOP_LEVEL}/{name}")
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = EXEC_ATTR if is_exec else DATA_ATTR
            zf.writestr(info, data)

    print(f"Built {OUT_ZIP}")
    with zipfile.ZipFile(OUT_ZIP) as zf:
        for i in zf.infolist():
            mode = (i.external_attr >> 16) & 0o777
            print(f"  {i.filename:45} {i.file_size:>6}  mode={oct(mode)}")


if __name__ == "__main__":
    main()
