"""File locations of the governed data layer (docs/07-ARCHITECTURE-AND-CONTRACTS.md).

`MIAUDOW_CANONICAL_DIR` may point the API at another built copy of `data/canonical/` (tests use it).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
RULES = DATA / "rules"
REFERENCE = DATA / "reference"
API_RULES = ROOT / "api" / "rules"
BUILD_COMMAND = r".venv\Scripts\python pipeline/build_canonical.py"


def canonical_dir() -> Path:
    """The folder of the built canonical files (read at call time so tests can redirect it)."""
    return Path(os.getenv("MIAUDOW_CANONICAL_DIR", str(DATA / "canonical")))
