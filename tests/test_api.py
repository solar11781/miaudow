"""Tests for the backend skeleton (written before the code, D-29). Fake data only (D-80).

Spec: UI-UX-SPEC §11 HealthResponse {status: "ok", artifacts: {file name: {schema_version, generated_at}}};
04-TECH-DESIGN §1 and D-76: the FastAPI service serves the built frontend and returns index.html for every frontend
route of UI-UX-SPEC §6 (browser history routing, D-102); unknown /api paths are 404, never index.html;
D-92 / 04 §10: uvicorn runs with --no-access-log.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from fieldshift.api.app import FRONTEND_ROUTES, create_app

FIX = Path("tests/fixtures/artifacts")


def test_health_lists_each_artifact_with_version_and_time() -> None:
    r = TestClient(create_app(artifacts_dir=FIX)).get("/api/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "artifacts": {"risk_table.json": {"schema_version": "0.4", "generated_at": "2000-01-01T00:00:00+07:00"}},
    }


def test_health_without_artifacts_is_still_ok(tmp_path: Path) -> None:
    r = TestClient(create_app(artifacts_dir=tmp_path / "none")).get("/api/health")
    assert r.json() == {"status": "ok", "artifacts": {}}


def test_frontend_routes_return_index_html(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    c = TestClient(create_app(artifacts_dir=FIX, frontend_dir=tmp_path))
    assert set(FRONTEND_ROUTES) == {
        "/",
        "/ruong",
        "/nam",
        "/uu-tien",
        "/phuong-an",
        "/khong-co-phuong-an",
        "/phuong-phap",
        "/gioi-thieu",
        "/nguon",
    }  # UI-UX-SPEC §6 (built routes)
    for route in FRONTEND_ROUTES:
        r = c.get(route)
        assert r.status_code == 200
        assert "app" in r.text
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/api/nothing").status_code == 404


def test_start_command_turns_off_the_access_log() -> None:
    assert "--no-access-log" in Path("Dockerfile").read_text(encoding="utf-8")
