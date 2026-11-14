"""Tests for the method response (written before the code), on the real rules files and artifacts.

Spec: UI-UX-SPEC §11 (MethodResponse and its sub-types; the method checks of "Validation in src/api.ts"), §11b (the
method page); 05-DATA-CONTRACTS §5b (metrics.json, gates.json), §7b (method.yaml), §8, §10 (Method: metrics.json,
gates.json, method.yaml, sources.yaml); D-135 (rain_check null = not run); D-160 (studies named by first author and
year, not by our labels P-02 and P-03). Expected values are the files' own rows and the results in docs/EXPERIMENTS.md.
"""

import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from fieldshift.engine.method import method
from fieldshift.engine.rules import load_sources
from fieldshift.engine.schemas import EXPLAIN_KEYS, source_ids_in
from source_trace import check_response

REPO = Path(__file__).resolve().parents[1]
OUR_LABEL = re.compile(r"\bP-0\d")  # D-160: our paper labels P-02, P-03 never show on the method page


def artifact(name: str) -> dict:
    return json.loads((REPO / "artifacts" / name).read_text(encoding="utf-8"))


def method_yaml() -> dict:
    return yaml.safe_load((REPO / "rules" / "method.yaml").read_text(encoding="utf-8"))


def edit_json(root: Path, name: str, change: Callable[[dict], object]) -> None:
    path = root / "artifacts" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture(scope="module")
def resp() -> dict:
    return method(REPO).model_dump(by_alias=True)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A copy of the real rules files and artifacts that one test may change."""
    for folder in ("rules", "artifacts"):
        shutil.copytree(REPO / folder, tmp_path / "root" / folder)
    return tmp_path / "root"


def test_test_years_and_freeze_commit(resp: dict) -> None:
    assert resp["test_years"] == {"first": 2016, "last": 2024}  # EXPERIMENTS E-012: 9 test years 2016-2024
    assert resp["freeze_commit"].startswith("ea7a60c")  # EXPERIMENTS E-012: freeze commit ea7a60c (E-010)


def test_every_metric_row_of_metrics_json_in_file_order(resp: dict) -> None:
    assert resp["metrics"] == artifact("metrics.json")["metrics"]
    assert len(resp["metrics"]) == 156  # EXPERIMENTS: E-012 96 rows + E-013/E-017 4 rows + E-018/E-008 56 rows


def test_every_gate_in_file_order(resp: dict) -> None:
    assert resp["gates"] == artifact("gates.json")["gates"]
    verdicts = {(g["gate"], g["season"]): g["passed"] for g in resp["gates"]}
    assert verdicts == {  # EXPERIMENTS E-012
        ("G1", "spring"): True,
        ("G2", "spring"): False,
        ("G3", "spring"): True,
        ("G4", "spring"): True,
        ("G1", "winter"): True,
        ("G2", "winter"): True,
        ("G3", "winter"): True,
        ("G4", "winter"): True,
        ("G1", "summer_autumn"): False,
    }


def test_weather_claims_and_reports(resp: dict) -> None:
    assert resp["weather_claims"] == artifact("metrics.json")["weather_claims"]
    made = {c["season"]: c["made"] for c in resp["weather_claims"]}
    assert made == {"spring": False, "winter": True}  # EXPERIMENTS E-012: spring claim not made, winter claim made
    assert resp["reports"] == artifact("metrics.json")["reports"]


def test_method_texts_come_from_method_yaml(resp: dict) -> None:
    texts = method_yaml()
    assert resp["coverage"] == texts["coverage"]
    assert resp["explain_terms"] == texts["explain_terms"]
    assert resp["limitations"] == texts["limitations"]


def test_coverage_cells_once_and_explain_terms_in_order(resp: dict) -> None:
    cells = [(c["row_key"], c["axis"]) for c in resp["coverage"]]
    assert len(cells) == len(set(cells)) == 30  # UI-UX-SPEC §11b coverage table: 5 rows x 6 axes
    assert tuple(t["key"] for t in resp["explain_terms"]) == EXPLAIN_KEYS  # UI-UX-SPEC §11b item 3


def test_limitations_are_non_empty_lines_in_both_languages(resp: dict) -> None:
    assert resp["limitations"]
    for line in resp["limitations"]:
        assert set(line) == {"vi", "en"}
        assert line["vi"].strip()
        assert line["en"].strip()


def test_datasets_not_used_come_from_method_yaml_each_with_its_reason_and_sources(resp: dict) -> None:
    assert resp["datasets_not_used"] == method_yaml()["datasets_not_used"]
    # planning research/datasets-considered.md rows whose facts have a REFERENCES source
    assert [d["dataset"] for d in resp["datasets_not_used"]] == [
        "ECOSTRESS",
        "Landsat",
        "VIIRS",
        "Sentinel-2 (ESA)",
        "GLDAS",
        "GRACE / GRACE-FO",
        "GEDI",
        "FAO GAEZ",
        "ERA5 (ECMWF)",
    ]
    era5 = next(d for d in resp["datasets_not_used"] if d["dataset"] == "ERA5 (ECMWF)")
    assert "R-N09" in era5["source_ids"]  # REFERENCES R-N09: the Copernicus CDS ERA5 page holds its facts
    gedi = next(d for d in resp["datasets_not_used"] if d["dataset"] == "GEDI")
    assert gedi["source_ids"] == ["R-N07", "R-N10"]  # CMR GEDI02_A start date; GEDI mission overview page
    register = load_sources(REPO)
    for entry in resp["datasets_not_used"]:
        assert entry["reason"]["vi"].strip()
        assert entry["reason"]["en"].strip()
        assert entry["source_ids"]
        assert set(entry["source_ids"]) <= register.keys(), entry["dataset"]


def test_no_soilgrids_source_in_the_method_response(resp: dict) -> None:
    # UI-UX-SPEC T27 (D-97): no API response contains the SoilGrids source ids R-D02 or R-D03
    text = json.dumps(resp)
    assert "R-D02" not in text
    assert "R-D03" not in text


def test_a_dataset_not_used_without_a_source_fails_naming_the_file(root: Path) -> None:
    path = root / "rules" / "method.yaml"
    texts = yaml.safe_load(path.read_text(encoding="utf-8"))
    texts["datasets_not_used"][0]["source_ids"] = []
    path.write_text(yaml.safe_dump(texts, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match=r"method\.yaml"):
        method(root)


def test_the_ndvi_term_cites_nasas_ndvi_page(resp: dict) -> None:
    ndvi = next(t for t in resp["explain_terms"] if t["key"] == "ndvi")
    assert ndvi["source_ids"] == ["R-N08"]  # D-165: NASA Earth Observatory, Measuring Vegetation (NDVI & EVI)
    # earthobservatory.nasa.gov/features/MeasuringVegetation redirects (301) to this address (read 2026-11-14)
    url = "https://science.nasa.gov/earth/earth-observatory/measuring-vegetation-ndvi-evi"
    assert resp["sources"]["R-N08"]["url"] == url


def test_the_ndvi_texts_say_what_the_app_shows(resp: dict) -> None:
    # the science page shows a MODIS NDVI chart (REFERENCES R-N11) and the observatory page Sentinel-2 NDVI images
    # (D-169 audit); 03-ML-SPEC keeps in-season vegetation signals out of the model inputs (leakage)
    ndvi = next(t for t in resp["explain_terms"] if t["key"] == "ndvi")["text"]
    assert "Not used in the yield model" in ndvi["en"]
    assert "Không dùng trong mô hình năng suất" in ndvi["vi"]
    assert "science page" in ndvi["en"]
    assert "Khoa học" in ndvi["vi"]
    assert "as a chart of greenness" in ndvi["en"]  # /khoa-hoc NdviChart: a chart with numbers, not a picture
    assert "dưới dạng biểu đồ độ xanh" in ndvi["vi"]
    reasons = {d["dataset"]: d["reason"] for d in resp["datasets_not_used"]}
    sentinel = reasons["Sentinel-2 (ESA)"]
    assert "Not used in the model" in sentinel["en"]
    assert "Không dùng trong mô hình" in sentinel["vi"]
    assert "observatory page" in sentinel["en"]
    assert "Đài quan sát" in sentinel["vi"]
    landsat = reasons["Landsat"]
    assert "no number in this app" not in landsat["en"]
    assert "không con số nào" not in landsat["vi"]


def test_rain_check_is_not_run(resp: dict) -> None:
    assert resp["rain_check"] is None  # D-135: null = not run (queue item 45 not built)


def test_sources_hold_exactly_the_ids_used_and_every_id_traces(resp: dict) -> None:
    used = set(source_ids_in({k: v for k, v in resp.items() if k != "sources"}))
    assert set(resp["sources"]) == used
    assert {"E-008", "E-010", "E-012", "E-013", "E-017", "E-018"} <= used  # experiment ids of metrics.json
    assert check_response(resp, None) == []


def test_no_paper_labels_in_the_method_texts(resp: dict) -> None:
    for cell in resp["coverage"]:
        for text in (cell["crop"], cell["text"]):
            assert not OUR_LABEL.search(text["vi"] + text["en"]), cell["row_key"]
    for term in resp["explain_terms"]:
        for text in (term["title"], term["text"]):
            assert not OUR_LABEL.search(text["vi"] + text["en"]), term["key"]
    for line in resp["limitations"]:
        assert not OUR_LABEL.search(line["vi"] + line["en"]), line


def test_disagreeing_freeze_commits_fail_loudly(root: Path) -> None:
    edit_json(root, "gates.json", lambda data: data.update(freeze_commit="0000000"))
    with pytest.raises(ValueError, match="freeze_commit"):
        method(root)


def test_a_bad_metric_row_fails_naming_the_file(root: Path) -> None:
    edit_json(root, "metrics.json", lambda data: data["metrics"][0].update(model_id="m9"))
    with pytest.raises(ValueError, match=r"metrics\.json"):
        method(root)


def test_an_id_without_source_facts_fails_loudly(root: Path) -> None:
    edit_json(root, "metrics.json", lambda data: data["reports"][0].update(source_ids=["E-999"]))
    with pytest.raises(ValueError, match="E-999"):
        method(root)
