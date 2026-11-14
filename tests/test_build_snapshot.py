"""The demo-day snapshot (scripts/build_snapshot.py) holds exactly what the API answers now, so a stale copy fails CI.

Spec: 04-TECH-DESIGN section 1 and section 9 runbook (fallback for judging: a static snapshot of real API responses,
D-150; the placeholder fixtures are never shown as results). Rebuild with: PYTHONPATH=src python scripts/build_snapshot.py
"""

import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fieldshift.api.app import create_app

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_snapshot", REPO / "scripts" / "build_snapshot.py")
build_snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_snapshot)

SNAPSHOT = REPO / "frontend" / "snapshot"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(root=REPO))


@pytest.fixture(scope="module")
def index() -> dict:
    return json.loads((SNAPSHOT / "index.json").read_text(encoding="utf-8"))


def test_past_years_and_method_equal_the_api(client: TestClient) -> None:
    past = client.get("/api/past-years", params={"province": "nghe_an"})
    assert json.loads((SNAPSHOT / "past-years.json").read_text(encoding="utf-8")) == past.json()
    assert json.loads((SNAPSHOT / "method.json").read_text(encoding="utf-8")) == client.get("/api/method").json()
    figure = client.get("/api/figures/nghe_an_grid.svg").content
    assert (SNAPSHOT / "figures" / "nghe_an_grid.svg").read_bytes() == figure


def test_every_saved_compare_equals_the_api(client: TestClient, index: dict) -> None:
    for entry in index["compare"]:
        body = {"province": "nghe_an", "land": entry["land"], "years": entry["years"], "priority": entry["priority"]}
        saved = json.loads((SNAPSHOT / entry["file"]).read_text(encoding="utf-8"))
        assert saved == client.post("/api/compare", json=body).json(), entry["file"]


def test_index_lists_the_demo_set_and_every_compare_file(client: TestClient, index: dict) -> None:
    past = client.get("/api/past-years", params={"province": "nghe_an"}).json()
    expected = [(c["land"], c["priority"], c["years"]) for c in build_snapshot.demo_set(past)]
    assert [(e["land"], e["priority"], e["years"]) for e in index["compare"]] == expected
    on_disk = sorted(p.relative_to(SNAPSHOT).as_posix() for p in (SNAPSHOT / "compare").glob("*.json"))
    assert sorted(e["file"] for e in index["compare"]) == on_disk
    assert index["commit"]
    assert index["made_at"]


def test_demo_years_follow_the_rule_in_the_docstring() -> None:
    # rule of scripts/build_snapshot.py: the 3 years with the largest consecutive-drought share (latest first on ties),
    # plus the year with the largest cold share; and the latest past year alone
    def share(s: str | None) -> dict | None:
        return None if s is None else {"value": s}

    def row(year: int, drought: str | None, cold: str | None) -> dict:
        return {"year": year, "shares": {"drought_rain_consecutive": share(drought), "cold": share(cold)}}

    past = {"years": [row(2001, "100", "4"), row(2002, "80", "53"), row(2003, "100", None), row(2004, "100", "0")]}
    assert build_snapshot.demo_years(past) == [[2001, 2002, 2003, 2004], [2004]]
    assert len(build_snapshot.demo_set(past)) == 2 * 4 * 2  # both API land types x the four priorities x 2 year sets
