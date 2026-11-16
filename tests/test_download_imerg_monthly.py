"""Tests for scripts/download_imerg_monthly.py, the IMERG stage of scripts/reproduce.sh.

Spec: the satellite rain check (IMERG) is a bonus item; the rebuild check can skip the IMERG download when NASA's
servers do not answer (D-150; team, 2026-11-14). FIELDSHIFT_SKIP_IMERG=1 means skip: exit 0 with a message, no request and no file
written; any other value runs the stage.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "download_imerg_monthly.py"


def _run(tmp_path: Path, skip: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "FIELDSHIFT_SKIP_IMERG": skip, "PYTHONIOENCODING": "utf-8"}
    code = SCRIPT.read_text(encoding="utf-8")
    return subprocess.run(
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


def test_imerg_stage_is_skipped_with_a_message_when_asked(tmp_path: Path) -> None:
    result = _run(tmp_path, "1")
    assert result.returncode == 0, result.stderr
    assert "IMERG stage skipped" in result.stdout
    assert list(tmp_path.iterdir()) == []  # nothing downloaded, no manifest row


def test_imerg_stage_runs_when_the_switch_is_not_1(tmp_path: Path) -> None:
    result = _run(tmp_path, "0")
    assert "IMERG stage skipped" not in result.stdout
    assert result.returncode != 0  # it went on and stopped at the missing cell list of this empty folder
    assert "cell_weights.csv" in result.stderr
