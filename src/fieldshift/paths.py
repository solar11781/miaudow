"""The project folder that holds rules/, artifacts/ and frontend/dist (04-TECH-DESIGN §1).

Plain words: in a source checkout this is the repository root. An installed package (the Dockerfile runs
`pip install .`) lives in site-packages, so the folder must be given in FIELDSHIFT_ROOT (the Dockerfile sets it).
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """$FIELDSHIFT_ROOT if set, else the source checkout; raises if that folder has no rules/ (never a silent guess)."""
    env = os.environ.get("FIELDSHIFT_ROOT")
    root = Path(env) if env else Path(__file__).resolve().parents[2]
    if not (root / "rules").is_dir():
        raise RuntimeError(f"no rules/ folder in {root}: set FIELDSHIFT_ROOT to the project folder")
    return root
