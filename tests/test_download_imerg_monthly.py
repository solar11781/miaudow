"""Tests for scripts/download_imerg_monthly.py, the IMERG stage of scripts/reproduce.sh.

Spec: the satellite rain check (IMERG) is a bonus item; the rebuild check skips the IMERG stage when the rain check is
not built (06-IMPLEMENTATION-PLAN section 4, Sun 00:00 row; team, 2026-11-14). FIELDSHIFT_SKIP_IMERG set means skip:
exit 0 with a message, no request and no file written.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "download_imerg_monthly.py"


def test_imerg_stage_is_skipped_with_a_message_when_asked(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "FIELDSHIFT_SKIP_IMERG": "1", "PYTHONIOENCODING": "utf-8"}
    code = SCRIPT.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-"],
        input=code,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "IMERG stage skipped" in result.stdout
    assert list(tmp_path.iterdir()) == []  # nothing downloaded, no manifest row
