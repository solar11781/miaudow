"""Tests for finding the project folder (rules/, artifacts/, frontend/dist) when the package is installed.

Spec: 04-TECH-DESIGN §1 and the Dockerfile: the container copies rules/ and artifacts/ to /app and installs the
package with `pip install --no-deps .`, so the package code lives in site-packages, not under /app. The service must
still read /app/rules and /app/artifacts (audit 2026-11-13, part B row 17). An installed package that cannot find
the project folder must fail at start with a message, never serve an empty health answer.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

PROBE = """
import json
from fastapi.testclient import TestClient
from fieldshift.features import season_windows
from fieldshift.api.app import create_app
print(json.dumps({"calendar": str(season_windows.CALENDAR_FILE),
                  "module": season_windows.__file__,
                  "health": TestClient(create_app()).get("/api/health").json()}))
"""


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """The package as `pip install .` lays it out: a copy of src/fieldshift in a folder outside the repository.

    A copy instead of a real pip build keeps the test offline and leaves no build/ folder in the repository.
    """
    site = tmp_path_factory.mktemp("site")
    shutil.copytree(REPO / "src" / "fieldshift", site / "fieldshift", ignore=shutil.ignore_patterns("__pycache__"))
    app = tmp_path_factory.mktemp("app")
    shutil.copytree(REPO / "rules", app / "rules")
    (app / "artifacts").mkdir()
    shutil.copy(REPO / "tests" / "fixtures" / "artifacts" / "risk_table.json", app / "artifacts")
    return site, app


def _run(site: Path, cwd: Path, env_extra: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "FIELDSHIFT_ROOT")}
    env.update({"PYTHONPATH": str(site), **env_extra})
    return subprocess.run(
        [sys.executable, "-"], input=PROBE, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


def test_installed_package_reads_rules_and_artifacts_from_the_project_folder(installed: tuple[Path, Path]) -> None:
    site, app = installed
    r = _run(site, app.parent, {"FIELDSHIFT_ROOT": str(app)})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert Path(out["module"]).is_relative_to(site)  # really the installed copy
    assert Path(out["calendar"]) == app / "rules" / "calendar.yaml"
    assert out["health"] == {
        "status": "ok",
        "artifacts": {"risk_table.json": {"schema_version": "0.4", "generated_at": "2000-01-01T00:00:00+07:00"}},
    }


def test_installed_package_without_the_project_folder_fails_with_a_message(installed: tuple[Path, Path]) -> None:
    site, app = installed
    r = _run(site, app.parent, {})
    assert r.returncode != 0
    assert "FIELDSHIFT_ROOT" in r.stderr


def test_dockerfile_points_the_package_at_its_workdir() -> None:
    text = (REPO / "Dockerfile").read_text(encoding="utf-8")
    workdir = re.search(r"^WORKDIR\s+(\S+)", text, re.MULTILINE).group(1)
    assert re.search(rf"^ENV\s+.*FIELDSHIFT_ROOT={re.escape(workdir)}\b", text, re.MULTILINE)
