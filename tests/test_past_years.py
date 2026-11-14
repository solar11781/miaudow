"""Tests for the past-years response (written before the code). Placeholder fixtures in tests/fixtures/engine.

Spec: 05-DATA-CONTRACTS §10 (rules from rules/conditions.yaml §6c; years from the `level` `year` rows of
artifacts/hazard_labels.json §4b; sources from rules/sources.yaml §8 for every id used); §4b API conversion: the share
x 100 rounded half up to an integer (decimal.ROUND_HALF_UP, D-95, D-102), unit "%" in both languages, source_ids =
[threshold_source_id, values_source_ids..., computed_by], null stays null; UI-UX-SPEC §11 PastYearsResponse.
Expected values are hand-computed from the fixture rows.
"""

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from fieldshift.engine.past_years import past_years
from source_trace import check_response

FIX = Path(__file__).resolve().parent / "fixtures" / "engine"
PCT = {"vi": "%", "en": "%"}
IDS = ["R-A01", "R-N01", "R-N02", "E-019"]


def pct(v: str) -> dict:
    return {"value": v, "unit": PCT, "source_ids": IDS}


def response() -> dict:
    return past_years("nghe_an", FIX).model_dump(by_alias=True)


def test_year_rows_are_whole_percent_rounded_half_up_with_their_sources() -> None:
    years = response()["years"]
    assert years == [
        {
            "year": 1995,  # 0.125 -> 12.5 -> 13; 0.995 -> 99.5 -> 100; 0.12449 -> 12.449 -> 12; null stays null
            "shares": {
                "heavy_rain": pct("13"),
                "heat": pct("0"),
                "drought_rain_consecutive": pct("100"),
                "drought_rain_any2": None,
                "cold": pct("12"),
            },
        },
        {
            "year": 1996,  # 0.005 -> 0.5 -> 1; 0.994 -> 99.4 -> 99; 0.0449 -> 4.49 -> 4
            "shares": {
                "heavy_rain": pct("1"),
                "heat": pct("100"),
                "drought_rain_consecutive": pct("99"),
                "drought_rain_any2": pct("50"),
                "cold": pct("4"),
            },
        },
    ]


def test_rules_come_in_rule_code_order_without_the_article_field() -> None:
    rules = response()["rules"]
    assert [r["code"] for r in rules] == ["heavy_rain", "heat", "drought_rain_consecutive", "drought_rain_any2", "cold"]
    assert rules[0] == {
        "code": "heavy_rain",
        "label": {"vi": "[heavy rain label]", "en": "[heavy rain label]"},
        "rule_text": {"vi": "[quoted article text]", "en": "[translation]"},
        "threshold_source_id": "R-A01",
        "values_source_ids": ["R-N01", "R-N02"],
        "computed_by": "E-019",
    }


def test_sources_hold_exactly_the_ids_used_and_every_id_traces() -> None:
    resp = response()
    assert sorted(resp["sources"]) == sorted(IDS)  # R-P02 is in the fixture file but unused
    assert check_response(resp, None) == []


def test_province_and_cell_count() -> None:
    resp = response()
    assert (resp["province"], resp["n_cells"]) == ("nghe_an", 7)  # n_cells of the fixture rows


def copy_with_rows(tmp_path: Path, change: Callable[[list[dict]], object]) -> Path:
    root = tmp_path / "root"
    shutil.copytree(FIX, root)
    path = root / "artifacts" / "hazard_labels.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data["rows"])
    path.write_text(json.dumps(data), encoding="utf-8")
    return root


def year_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["level"] == "year"]


def test_a_missing_year_rule_row_fails_loudly(tmp_path: Path) -> None:
    root = copy_with_rows(tmp_path, lambda rows: rows.remove(year_rows(rows)[0]))
    with pytest.raises(ValueError, match="1996"):
        past_years("nghe_an", root)


def test_a_duplicate_year_rule_row_fails_loudly(tmp_path: Path) -> None:
    root = copy_with_rows(tmp_path, lambda rows: rows.append(dict(year_rows(rows)[0])))
    with pytest.raises(ValueError, match="1996"):
        past_years("nghe_an", root)


def test_disagreeing_cell_counts_fail_loudly(tmp_path: Path) -> None:
    root = copy_with_rows(tmp_path, lambda rows: year_rows(rows)[0].update(n_cells=8))
    with pytest.raises(ValueError, match="n_cells"):
        past_years("nghe_an", root)


def test_an_id_without_source_facts_fails_loudly(tmp_path: Path) -> None:
    root = copy_with_rows(tmp_path, lambda rows: year_rows(rows)[0].update(computed_by="E-999"))
    with pytest.raises(ValueError, match="E-999"):
        past_years("nghe_an", root)
