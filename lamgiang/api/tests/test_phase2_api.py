"""Phase-2 HTTP routes: every number carries unit, time window, place and source; optional files missing give an
explicit unavailable state; imagery is never offered as evidence; no secret is ever echoed."""

import shutil

import pytest
from fastapi.testclient import TestClient

from miaudow_api import app as app_module
from miaudow_api import canonical, climate_ml, evidence
from miaudow_api.paths import DATA


@pytest.fixture(scope="module")
def client():
    with TestClient(app_module.create_app()) as c:
        yield c


def assert_series(s: dict) -> None:
    assert s["unit"], s["quantity"]
    assert s["time_window"]["start"] and s["time_window"]["end"]
    assert s["place"]["place_id"] and s["place"]["name"]["vi"] and s["place"]["name"]["en"]
    prov = s["provenance"]
    assert prov["dataset_id"] and prov["source_id"] and prov["method_id"]
    assert prov["is_forecast"] is False and prov["is_field_measurement"] is False
    assert len(s["values"]) == len(s["periods"])


def test_data_catalog_is_the_catalog(client):
    assert client.get("/api/data/catalog").json() == client.get("/api/catalog").json()


def test_data_quality_report(client):
    body = client.get("/api/data/quality").json()
    assert body["status"] == "available"
    report = body["report"]
    checks = report["checks"]
    assert report["counts"]["total"] == len(checks)
    for status in ("pass", "warn", "fail"):
        assert report["counts"][status] == sum(1 for c in checks if c["status"] == status)
    assert len({c["check_id"] for c in checks}) == len(checks)
    categories = {c["category"] for c in checks}
    assert {
        "integrity",
        "crs_bounds",
        "time",
        "units_ranges",
        "missing",
        "resolution",
        "licence",
        "version",
    } <= categories
    assert all(c["detail"]["vi"] and c["detail"]["en"] for c in checks)


def test_data_coverage(client):
    rows = client.get("/api/data/coverage").json()
    by_id = {r["dataset_id"]: r for r in rows}
    cat_ids = {d["dataset_id"] for d in client.get("/api/catalog").json()["datasets"]}
    assert set(by_id) == cat_ids
    power = by_id["nasa_power_daily"]
    assert power["time_span"] == {"start": "1990-01-01", "end": "2024-12-31", "label": None}
    assert power["counts"]["cells"] == 5 and power["missing"]["missing_months"] == 0
    assert by_id["modis_mod13q1_ndvi"]["missing"]["dates_without_valid_pixel"] == 35
    assert by_id["sentinel2_l2a_do_luong_vi"]["counts"]["scenes_used"] == 59
    assert by_id["nasa_hlss30"]["ingestion_status"] == "BLOCKED" and by_id["nasa_hlss30"]["counts"]["downloaded"] == 0


def test_climate_history(client):
    r = client.get("/api/climate/history", params={"cell": "farmland_weighted", "from": 2008, "to": 2010})
    assert r.status_code == 200
    body = r.json()
    assert body["years"] == [2008, 2009, 2010]
    by_q = {s["quantity"]: s for s in body["series"]}
    assert {"annual_rain_total_power", "annual_rain_total_chirps", "hot_days_power"} <= set(by_q)
    for s in body["series"]:
        assert_series(s)
    clim = canonical.load("climate.json")
    assert by_q["annual_rain_total_power"]["values"][2] == clim["series"]["farmland_weighted"]["2010"]["annual_rain_mm"]
    assert by_q["annual_rain_total_power"]["provenance"]["source_id"] == "R-N01"
    assert by_q["annual_rain_total_chirps"]["provenance"]["dataset_id"] == "chirps_v3_monthly"
    site = client.get("/api/climate/history", params={"cell": "site_luu_son"}).json()
    assert [u["what"] for u in site["unavailable"]] == ["nasa_power_daily"]
    assert client.get("/api/climate/history", params={"from": 2010, "to": 2005}).status_code == 422
    assert client.get("/api/climate/history", params={"cell": "nowhere"}).status_code == 422
    assert client.get("/api/climate/history", params={"from": 1950}).status_code == 422


def test_climate_anomalies_side_by_side(client):
    body = client.get("/api/climate/anomalies", params={"year": 2010}).json()
    areas = {a["place"]["place_id"]: a for a in body["areas"]}
    assert set(areas) == {"farmland_weighted", "19.5_105.0", "19.5_105.625", "19.0_105.0", "19.0_105.625",
                          "18.5_105.625", "site_luu_son"}  # fmt: skip
    farm = {s["quantity"]: s for s in areas["farmland_weighted"]["series"]}
    assert {"rain_anomaly_pct_power", "rain_anomaly_pct_chirps"} <= set(farm)
    clim = canonical.load("climate.json")
    assert farm["rain_anomaly_pct_power"]["values"] == clim["series"]["farmland_weighted"]["2010"]["anomaly_pct"]
    assert farm["rain_anomaly_pct_power"]["unit"] == "%"
    for a in body["areas"]:
        for s in a["series"]:
            assert_series(s)
            assert len(s["values"]) == 12
    assert areas["site_luu_son"]["unavailable"][0]["what"] == "nasa_power_daily"
    assert client.get("/api/climate/anomalies", params={"year": 1980}).status_code == 422


def test_climate_analogs(client):
    body = client.get("/api/climate/analogs", params={"year": 2010, "k": 4}).json()
    assert body["target_year"] == 2010 and len(body["analogs"]) == 4
    assert body["provenance"]["source_id"] == "R-N01"
    assert body["evaluation"]["n_cases"] == 33
    assert isinstance(body["evaluation"]["beats_baselines"], bool)
    assert body["evaluation"]["verdict"]["vi"] and body["evaluation"]["verdict"]["en"]
    assert body["limitations"]
    assert client.get("/api/climate/analogs", params={"year": 2010, "k": 0}).status_code == 422
    assert client.get("/api/climate/analogs", params={"year": 1900}).status_code == 422


def test_climate_anomaly_years(client):
    body = client.get("/api/climate/anomaly-years").json()
    assert len(body["years"]) == 34
    assert body["threshold"] > 0 and len(body["percentile_bounds_mm"]) == 2
    assert body["score_unit"].startswith("robust z")
    assert body["provenance"]["is_forecast"] is False
    assert body["evaluation"]["beats_baselines"] is False


def test_geo_regions(client):
    regions = {r["region_id"]: r for r in client.get("/api/geo/regions").json()}
    assert {"nghe_an", "do_luong", "luu_son_point", "luu_son_commune"} <= set(regions)
    cells = [r for r in regions.values() if r["kind"] == "grid_cell"]
    assert len(cells) == 5 and abs(sum(r["weight"] for r in cells) - 1) < 1e-6
    assert regions["luu_son_commune"]["status"] == "unavailable" and regions["luu_son_commune"]["geometry"] is None
    for r in regions.values():
        assert r["source"]
        if r["status"] == "available":
            assert r["licence"] and r["geometry"]["type"] in ("Polygon", "Point")


def test_geo_layers_never_present_imagery_as_evidence(client):
    layers = client.get("/api/geo/layers").json()
    assert all(x["kind"] in ("visual", "data") for x in layers)
    gibs = [x for x in layers if x["group"] == "gibs"]
    assert len(gibs) == 14
    assert all(x["kind"] == "visual" and x["validation_status"] == "ILLUSTRATIVE" for x in gibs)
    s2 = [x for x in layers if x["group"] == "sentinel2_ndvi"]
    assert len(s2) == 6
    for x in s2:
        assert x["kind"] == "data" and len(x["bounds"]) == 4 and x["unit"].startswith("NDVI")
        assert [s["value"] for s in x["legend"]] == [0.0, 0.4, 0.8]
        assert "Copernicus" in x["attribution"]
    assert all(x["licence"] for x in layers)


def test_satellite_routes(client):
    sc = client.get("/api/satellite/scenes").json()
    assert sc["status"] == "available" and len(sc["scenes"]) == 59
    assert sc["units"]["ndvi_median"].startswith("NDVI") and sc["attribution"]
    assert sc["provenance"]["is_field_measurement"] is False
    veg = client.get("/api/satellite/vegetation").json()
    assert veg["sentinel2_status"] == "available" and len(veg["composites"]) == 6
    assert all(-1 <= c["ndvi_median"] <= 1 for c in veg["composites"])
    assert veg["modis_status"] == "available"
    med = next(s for s in veg["modis"] if s["quantity"] == "modis_ndvi_median")
    assert_series(med)
    assert sum(1 for v in med["values"] if v is None) == 35  # missing dates stay missing
    assert veg["comparability"]


def test_research_routes(client):
    docs = {d["doc_id"]: d for d in client.get("/api/research/documents").json()}
    assert docs["p02"]["status"] == "recorded_only" and docs["p02"]["chunk_count"] == 0
    assert docs["qd18_2021"]["status"] == "full_text" and docs["qd18_2021"]["chunk_count"] == 278
    assert all(d["licence_basis"] for d in docs.values())
    q = {"query": "lạc cần bao nhiêu nước", "k": 3}
    assert client.post("/api/research/search", json=q).json() == client.post("/api/evidence/search", json=q).json()


def test_crop_compare_is_the_decision_compare(client):
    q = {"water": "canal_end", "years": [2020]}
    a = client.post("/api/crop/compare", json=q)
    assert a.status_code == 200
    assert a.json() == client.post("/api/decision/compare", json=q).json()
    assert [p["plan_id"] for p in a.json()["plans"]] == ["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]
    assert client.post("/api/crop/compare", json={"plan_ids": ["zz"]}).status_code == 422


def test_ai_capabilities_report_presence_never_values(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-value-456")
    monkeypatch.setenv("ANTHROPIC_MODEL", "model-id-789")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "pw-secret-000")
    r = client.get("/api/ai/capabilities")
    assert "secret-value-456" not in r.text and "model-id-789" not in r.text and "pw-secret-000" not in r.text
    caps = {c["core_id"]: c for c in r.json()}
    assert caps["copilot"]["status"] == "working"
    assert all(c["present"] for c in caps["copilot"]["credentials"])
    monkeypatch.delenv("ANTHROPIC_MODEL")
    caps = {c["core_id"]: c for c in client.get("/api/ai/capabilities").json()}
    assert caps["copilot"]["status"] == "deterministic"
    assert {c["status"] for c in caps.values()} <= {"working", "deterministic", "blocked"}


def test_model_evaluations(client):
    evals = {e["evaluation_id"]: e for e in client.get("/api/models/evaluations").json()}
    assert {"E-012", "retrieval_2026-11-14", "climate_ml_2026-11-14"} <= set(evals)
    assert all(e["status"] == "available" for e in evals.values())
    assert evals["E-012"]["summary"]["gates"]
    assert evals["retrieval_2026-11-14"]["summary"]["ranking"]["recall@1"] == 0.481
    ml = evals["climate_ml_2026-11-14"]["summary"]
    assert ml["analogs_proxy"]["n_cases"] == 33 and "hit_rates" in ml["analogs_out_of_sample"]


def test_unavailable_states_when_optional_files_are_missing(tmp_path, monkeypatch):
    """Only the core canonical files: every Phase-2 route answers 200 with an explicit unavailable state."""
    for name in canonical.FILES:
        shutil.copy(DATA / "canonical" / name, tmp_path / name)
    monkeypatch.setenv("MIAUDOW_CANONICAL_DIR", str(tmp_path))
    monkeypatch.setattr(climate_ml, "EVAL_FILE", tmp_path / "no_eval.json")
    canonical.clear()
    evidence.load_passages.cache_clear()
    evidence.default_index.cache_clear()
    try:
        with TestClient(app_module.create_app()) as c:
            q = c.get("/api/data/quality").json()
            assert q["status"] == "unavailable" and q["report"] is None
            assert "check_quality.py" in q["unavailable"]["how_to_fix"]
            veg = c.get("/api/satellite/vegetation").json()
            assert veg["sentinel2_status"] == "unavailable" and veg["modis_status"] == "unavailable"
            assert {u["what"] for u in veg["unavailable"]} == {"vegetation.json", "ndvi_modis.json"}
            assert all(u["how_to_fix"] for u in veg["unavailable"])
            assert c.get("/api/satellite/scenes").json()["status"] == "unavailable"
            groups = {x["group"] for x in c.get("/api/geo/layers").json()}
            assert "gibs" not in groups and "sentinel2_ndvi" not in groups
            regions = {r["region_id"]: r for r in c.get("/api/geo/regions").json()}
            assert regions["do_luong"]["status"] == "unavailable"
            evals = {e["evaluation_id"]: e for e in c.get("/api/models/evaluations").json()}
            assert evals["climate_ml_2026-11-14"]["status"] == "unavailable"
            assert "run_climate_ml_eval.py" in evals["climate_ml_2026-11-14"]["summary"]["how_to_fix"]
            assert c.get("/api/climate/analogs", params={"year": 2010}).status_code == 200
    finally:
        monkeypatch.delenv("MIAUDOW_CANONICAL_DIR")
        canonical.clear()
        climate_ml.clear()
        evidence.load_passages.cache_clear()
        evidence.default_index.cache_clear()


def test_core_file_missing_still_gives_503(tmp_path, monkeypatch):
    monkeypatch.setenv("MIAUDOW_CANONICAL_DIR", str(tmp_path))
    canonical.clear()
    try:
        with TestClient(app_module.create_app()) as c:
            r = c.get("/api/climate/anomalies", params={"year": 2010})
            assert r.status_code == 503 and "build_canonical.py" in r.json()["build_command"]
            assert c.get("/api/geo/regions").status_code == 503
    finally:
        monkeypatch.delenv("MIAUDOW_CANONICAL_DIR")
        canonical.clear()
        climate_ml.clear()
        evidence.load_passages.cache_clear()
        evidence.default_index.cache_clear()
