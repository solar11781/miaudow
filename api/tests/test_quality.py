"""Data-quality checks (pipeline/check_quality.py): the real report holds, and every corrupted fixture is caught and
reported as a visible warn or fail, never dropped."""

import copy
import csv
import hashlib
import json
import sys

import pytest

from miaudow_api import canonical
from miaudow_api.paths import ROOT

sys.path.insert(0, str(ROOT / "pipeline"))

import check_quality as cq  # noqa: E402


def status(checks, check_id):
    return next(c for c in checks if c.check_id == check_id).status


@pytest.fixture(scope="module")
def report():
    return cq.run_checks(ROOT)


def test_real_report_is_complete_and_honest(report):
    ids = [c.check_id for c in report.checks]
    assert len(ids) == len(set(ids))
    assert report.counts["total"] == len(report.checks)
    assert report.counts["fail"] == sum(1 for c in report.checks if c.status == "fail")
    for c in report.checks:
        assert c.detail.vi and c.detail.en and isinstance(c.evidence, dict)
    # the integrity of every raw file the product uses holds on the committed data
    integrity = [c for c in report.checks if c.category == "integrity"]
    assert integrity and all(c.status == "pass" for c in integrity), [
        c.check_id for c in integrity if c.status != "pass"
    ]
    # known limitations are visible, not hidden
    assert status(report.checks, "version-sentinel2-baselines") == "warn"
    assert status(report.checks, "missing-modis-dates") == "warn"
    assert status(report.checks, "time-leap-year-aggregation") == "pass"


def test_committed_quality_file_matches_a_fresh_run(report):
    stored = json.loads((ROOT / "data" / "canonical" / "quality.json").read_text(encoding="utf-8"))
    assert [(c["check_id"], c["status"]) for c in stored["checks"]] == [(c.check_id, c.status) for c in report.checks]


# ---------------------------------------------------------------- corrupted fixtures


def power_payload(days: dict, unit="mm/day", lat=19.0, lon=105.625) -> dict:
    return {
        "geometry": {"coordinates": [lon, lat, 10.0]},
        "header": {"api": {"version": "v2.10.3"}, "start": "20000101", "end": "20000105"},
        "parameters": {"PRECTOTCORR": {"units": unit}},
        "properties": {"parameter": {"PRECTOTCORR": days}},
    }


def test_power_file_with_a_duplicate_day_a_gap_a_fill_value_and_negative_rain_is_caught(tmp_path):
    d = tmp_path / "power"
    d.mkdir()
    good = {"20000101": 1.0, "20000102": 0.0, "20000103": 2.5, "20000104": 0.0, "20000105": 3.0}
    (d / "power_good.json").write_text(json.dumps(power_payload(good)), encoding="utf-8")
    assert {c.check_id: c.status for c in cq.power_checks([d], tmp_path)}["time-power-continuity"] == "pass"
    # a duplicated key (json.loads alone would hide it), a missing day, a -999 and a negative value
    text = json.dumps(power_payload({"20000101": 1.0, "20000102": -999.0, "20000104": -3.0, "20000105": 2.0}))
    text = text.replace('"20000105": 2.0', '"20000105": 2.0, "20000105": 4.0')
    (d / "power_bad.json").write_text(text, encoding="utf-8")
    checks = {c.check_id: c for c in cq.power_checks([d], tmp_path)}
    assert checks["time-power-continuity"].status == "fail"
    assert checks["time-power-continuity"].evidence["duplicate_keys"] == {"power_bad.json": 1}
    assert checks["time-power-continuity"].evidence["gaps"] == {"power_bad.json:PRECTOTCORR": 1}
    assert checks["missing-power-fill-values"].status == "warn"
    assert checks["units-power-ranges"].status == "fail"


def test_power_unit_change_is_caught(tmp_path):
    d = tmp_path / "power"
    d.mkdir()
    days = {f"2000010{i}": 1.0 for i in range(1, 6)}
    (d / "power_inch.json").write_text(json.dumps(power_payload(days, unit="in/day")), encoding="utf-8")
    assert {c.check_id: c.status for c in cq.power_checks([d], tmp_path)}["units-power-declared"] == "fail"


def test_sha_mismatch_and_missing_file_fail(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    good = hashlib.sha256(f.read_bytes()).hexdigest()
    assert cq.sha_check("x", "d", f, good, tmp_path, "MANIFEST.json").status == "pass"
    f.write_text("a,b\n1,3\n", encoding="utf-8")  # one byte changed
    assert cq.sha_check("x", "d", f, good, tmp_path, "MANIFEST.json").status == "fail"
    assert cq.sha_check("x", "d", tmp_path / "gone.csv", good, tmp_path, "MANIFEST.json").status == "fail"
    assert cq.sha_check("x", "d", f, None, tmp_path, "MANIFEST.json").status == "warn"


def test_chirps_duplicates_negatives_and_gaps_are_caught(tmp_path):
    path = tmp_path / "chirps.csv"
    rows = [{"cell_id": "c1", "year": 2000, "month": m, "precip_mm": 10.0} for m in range(1, 13)]
    rows[3]["precip_mm"] = -5.0
    rows.append(dict(rows[0]))  # duplicate month
    rows.append({"cell_id": "c2", "year": 2000, "month": 1, "precip_mm": ""})  # incomplete area, empty value
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cell_id", "year", "month", "precip_mm"])
        w.writeheader()
        w.writerows(rows)
    checks = {c.check_id: c.status for c in cq.chirps_checks(path, tmp_path)}
    assert checks == {"time-chirps-months": "fail", "units-chirps-ranges": "fail", "missing-chirps-values": "warn"}


def test_vegetation_ndvi_out_of_range_and_duplicate_dates_fail():
    veg = copy.deepcopy(canonical.load("vegetation.json"))
    assert {c.check_id: c.status for c in cq.vegetation_checks(veg, None, None, ROOT)}["units-sentinel2-ndvi"] == "pass"
    veg["scenes"][0]["ndvi_median"] = 1.3
    veg["scenes"][1]["date"] = veg["scenes"][0]["date"]
    checks = {c.check_id: c.status for c in cq.vegetation_checks(veg, None, None, ROOT)}
    assert checks["units-sentinel2-ndvi"] == "fail"
    assert checks["time-sentinel2-scenes"] == "fail"
    assert checks["version-sentinel2-baselines"] == "warn"  # cannot be read without scenes.csv: said, not hidden


def test_modis_off_cycle_dates_and_bad_ndvi_fail():
    ndvi = copy.deepcopy(canonical.load("ndvi_modis.json"))
    ndvi["dates"][5] = "2015-03-20"  # not a 16-day composite start
    ndvi["median"][7] = -1.5
    checks = {c.check_id: c.status for c in cq.modis_checks(ndvi, None)}
    assert checks["time-modis-dates"] == "fail"
    assert checks["units-modis-ndvi"] == "fail"
    assert checks["version-modis-collection"] == "warn"


def test_geometry_errors_are_caught():
    adm1 = json.loads(
        (ROOT / "data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson").read_text(encoding="utf-8")
    )
    geo = canonical.load("geo.json")
    dl = copy.deepcopy(canonical.load("geo_do_luong.json"))
    clim = canonical.load("climate.json")
    ok = {c.check_id: c.status for c in cq.geometry_checks(adm1, geo, dl, clim, None)}
    assert ok["crs-do-luong-in-nghe-an"] == "pass" and ok["crs-study-point-in-do-luong"] == "pass"
    # move the district 2° east (into Laos/the sea) and the study point out of it
    ring = dl["do_luong"]["outline"]
    dl["do_luong"]["outline"] = [[[x + 2.0, y] for x, y in r] for r in ring] if isinstance(ring[0][0], list) else ring
    dl["study_point"]["lon"] += 5.0
    bad = {c.check_id: c.status for c in cq.geometry_checks(adm1, geo, dl, clim, None)}
    assert bad["crs-do-luong-in-nghe-an"] == "fail" and bad["crs-study-point-in-do-luong"] == "fail"
    # swapped lon/lat in the province outline
    swapped = copy.deepcopy(adm1)
    for f in swapped["features"]:
        if f["properties"]["shapeISO"] == "VN-22":
            g = f["geometry"]
            if g["type"] == "Polygon":
                g["coordinates"] = [[[y, x] for x, y in r] for r in g["coordinates"]]
            else:
                g["coordinates"] = [[[[y, x] for x, y in r] for r in p] for p in g["coordinates"]]
    assert {c.check_id: c.status for c in cq.geometry_checks(swapped, None, None, None, None)}[
        "crs-nghe-an-outline"
    ] == "fail"


def test_a_power_cell_far_from_the_province_fails():
    adm1 = json.loads(
        (ROOT / "data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson").read_text(encoding="utf-8")
    )
    clim = copy.deepcopy(canonical.load("climate.json"))
    clim["cells"][0] = {**clim["cells"][0], "id": "10.0_100.0", "lat": 10.0, "lon": 100.0}
    checks = {c.check_id: c.status for c in cq.geometry_checks(adm1, None, None, clim, None)}
    assert checks["crs-power-cells-in-bbox"] == "fail"


def test_missing_licence_fails_and_unstored_p02_passes():
    cat = copy.deepcopy(canonical.load("catalog.json"))
    cat["datasets"][0]["license"] = ""
    docs = json.loads((ROOT / "data/raw/documents/MANIFEST.json").read_text(encoding="utf-8"))
    checks = {c.check_id: c.status for c in cq.licence_checks(cat, {"attribution": ""}, None, None, docs)}
    assert checks[f"licence-{cat['datasets'][0]['dataset_id']}"] == "fail"
    assert checks["licence-sentinel2-attribution"] == "fail"
    assert checks["licence-gibs-acknowledgement"] == "fail"
    assert checks["licence-document-p02"] == "pass"
    docs["documents"][-1]["chunks_file"] = "data/raw/documents/p02/chunks.jsonl"  # a stored copy would be a breach
    assert {c.check_id: c.status for c in cq.licence_checks(cat, None, None, None, docs)}[
        "licence-document-p02"
    ] == "fail"


def test_climate_canonical_negative_rain_and_annual_mismatch_fail():
    clim = copy.deepcopy(canonical.load("climate.json"))
    row = clim["series"]["farmland_weighted"]["2010"]
    row["monthly_rain_mm"][0] = -1.0
    row["annual_rain_mm"] += 50
    checks = {c.check_id: c.status for c in cq.climate_canonical_checks(clim)}
    assert checks["units-climate-canonical"] == "fail"


def test_missing_inputs_fail_visibly(tmp_path):
    checks = cq.run_checks(tmp_path, tmp_path)
    fails = {c.check_id for c in checks.checks if c.status == "fail"}
    assert {"integrity-nasa_power_daily", "time-chirps-months", "units-sentinel2-ndvi", "time-modis-dates"} <= fails
    assert checks.counts["fail"] == len(fails)
