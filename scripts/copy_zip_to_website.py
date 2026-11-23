#!/usr/bin/env python3
"""Copy the built extension zip into website/downloads/ for deployment.

Run scripts/build_extension_zip.py first. Kept as a separate step so the
website's publish directory only ever contains a freshly built zip, never a
committed/stale one.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_ZIP = ROOT / "dist" / "StitchBase.zip"
DEST_DIR = ROOT / "website" / "downloads"
DEST_ZIP = DEST_DIR / "StitchBase.zip"


def main() -> None:
    if not SRC_ZIP.exists():
        sys.exit(
            f"{SRC_ZIP} not found. Run scripts/build_extension_zip.py first."
        )

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_ZIP, DEST_ZIP)
    print(f"Copied {SRC_ZIP} -> {DEST_ZIP}")


if __name__ == "__main__":
    main()
