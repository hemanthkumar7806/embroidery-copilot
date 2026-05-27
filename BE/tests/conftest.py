"""Pytest configuration for BE tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
root_str = str(ROOT)
while root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

