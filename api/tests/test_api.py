"""HTTP routes via fastapi.testclient."""

import pytest
from fastapi.testclient import TestClient

from miaudow_api import app as app_module
from miaudow_api import canonical, evidence


@pytest.fixture(scope="module")
def client():
    with TestClient(app_module.create_app()) as c:
        yield c


def test_health_reports_cores_and_datasets_without_secrets(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-value-123")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["cores"]["copilot"] == {"status": "not_configured", "engine": "deterministic"}
    assert "secret-value-123" not in r.text
    ids = {d["dataset_id"]: d["ingestion_status"] for d in body["datasets"]}
    assert ids["nasa_power_daily"] == "INGESTED"
    assert ids["sentinel2_l2a"] == "CONTRACT_ONLY"
    monkeypatch.setenv("ANTHROPIC_MODEL", "some-model")
    assert client.get("/api/health").json()["cores"]["copilot"]["engine"] == "claude"


def test_catalog(client):
    body = client.get("/api/catalog").json()
    assert {"datasets", "methods", "sources", "metrics"} <= set(body)
    method_ids = {m["method_id"] for m in body["methods"]}
    assert {"E-019", "E-022", "sum_daily_precip_complete_month"} <= method_ids


def test_climate_routes(client):
    r = client.get("/api/climate/year/2020")
    assert r.status_code == 200
    assert all(rec["is_field_measurement"] is False for rec in r.json())
    assert client.get("/api/climate/year/1900").status_code == 422
    m = client.get("/api/climate/monthly", params={"year": 2020, "cell": "18.5_105.625"})
    assert m.status_code == 200
    assert client.get("/api/climate/monthly", params={"year": 2020, "cell": "x"}).status_code == 422
    assert client.get("/api/climate/live", params={"year": 1970}).status_code == 422


def test_evidence_route(client):
    r = client.post("/api/evidence/search", json={"query": "lạc cần bao nhiêu nước", "k": 3})
    assert r.status_code == 200
    assert r.json()["abstained"] is False
    r = client.post("/api/evidence/search", json={"query": "cách nấu phở bò"})
    assert r.json()["abstained"] is True
    assert client.post("/api/evidence/search", json={"query": "x"}).status_code == 422


def test_decision_routes(client):
    plans = client.get("/api/decision/plans").json()
    assert [p["plan_id"] for p in plans] == ["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]
    r = client.post("/api/decision/compare", json={"priority": "income", "plan_ids": ["cc4", "cc1"], "years": [2020]})
    assert r.status_code == 200
    assert [p["plan_id"] for p in r.json()["plans"]] == ["cc1", "cc4"]
    assert client.post("/api/decision/compare", json={"plan_ids": ["zz"]}).status_code == 422
    assert client.post("/api/decision/compare", json={"years": [1990]}).status_code == 422
    assert client.post("/api/decision/compare", json={"priority": "rank"}).status_code == 422


def test_voice_benchmark_route(client):
    assert client.get("/api/voice/benchmark").json()["status"] == "no_data"


def test_rate_limiter_window():
    now = [0.0]
    limiter = app_module.RateLimiter(2, 10.0, clock=lambda: now[0])
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    now[0] = 10.5
    assert limiter.allow("a")


def test_rate_limit_setting_must_be_valid(monkeypatch):
    monkeypatch.setenv("MIAUDOW_COPILOT_RATE", "lots")
    with pytest.raises(ValueError, match="MIAUDOW_COPILOT_RATE"):
        app_module.RateLimiter.from_env()


def test_missing_canonical_file_gives_503_with_the_build_command(tmp_path, monkeypatch):
    monkeypatch.setenv("MIAUDOW_CANONICAL_DIR", str(tmp_path))
    canonical.clear()
    evidence.load_passages.cache_clear()
    evidence.default_index.cache_clear()
    try:
        with TestClient(app_module.create_app()) as c:
            r = c.get("/api/climate/year/2020")
            assert r.status_code == 503
            assert "build_canonical.py" in r.json()["build_command"]
            assert c.get("/api/health").json()["status"] == "degraded"
            assert c.post("/api/evidence/search", json={"query": "lạc cần nước"}).status_code == 503
    finally:
        monkeypatch.delenv("MIAUDOW_CANONICAL_DIR")
        canonical.clear()
        evidence.load_passages.cache_clear()
        evidence.default_index.cache_clear()
