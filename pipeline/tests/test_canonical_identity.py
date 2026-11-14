"""The canonical builder reproduces the web app's data files, and its climate rules hold (complete months, leap days).

Identity: pipeline/build_canonical.py rebuilds hazards, soil, geo and model from data/raw and data/reference, and the
result equals web/src/data/generated/*.json (the web builder's output) and data/canonical/*.json; only generated_at
may differ.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "api", ROOT / "pipeline"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_canonical as bc  # noqa: E402

WEB = ROOT / "web" / "src" / "data" / "generated"
CANON = ROOT / "data" / "canonical"
NAMES = ("hazards", "soil", "geo", "model")


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "generated_at"}


@pytest.fixture(scope="module")
def rebuilt() -> dict:
    cells = bc.load_cells()
    daily, _ = bc.load_daily(cells)
    weights = {c["id"]: c["weight"] for c in cells}
    clim = {cid: bc.monthly_climatology(df["PRECTOTCORR"]) for cid, df in daily.items()}
    out = {
        "hazards": bc.build_hazards(cells, daily, weights, clim),
        "soil": bc.build_soil(daily, weights),
        "geo": bc.build_geo(cells),
        "model": bc.build_model(),
    }
    return {k: json.loads(json.dumps(v, ensure_ascii=False)) for k, v in out.items()}


@pytest.mark.parametrize("name", NAMES)
def test_rebuilt_files_equal_the_web_files(rebuilt, name):
    web = _strip(json.loads((WEB / f"{name}.json").read_text(encoding="utf-8")))
    assert rebuilt[name] == web


@pytest.mark.parametrize("name", NAMES)
def test_canonical_files_equal_the_web_files(name):
    canon = CANON / f"{name}.json"
    if not canon.exists():
        pytest.skip(f"build first: {bc.ROOT}")
    web = _strip(json.loads((WEB / f"{name}.json").read_text(encoding="utf-8")))
    assert _strip(json.loads(canon.read_text(encoding="utf-8"))) == web


def test_team_dates_match_the_builder_dates():
    bc.check_team_dates()  # raises when the P-02 dates of the rulebook and the builder differ


def _frame(year: int, rain: float = 2.0) -> pd.DataFrame:
    idx = pd.date_range("1990-01-01", f"{max(year, 2020)}-12-31", freq="D")
    return pd.DataFrame({"PRECTOTCORR": rain, "T2M_MAX": 30.0, "T2M": 20.0}, index=idx)


def test_month_with_a_missing_day_is_null_and_not_zero():
    df = _frame(2010)
    normal = bc.monthly_climatology(df["PRECTOTCORR"])
    df.loc["2010-03-15", "PRECTOTCORR"] = np.nan
    row = bc.cell_year(df, 2010, normal)
    assert row["monthly_rain_mm"][2] is None  # March
    assert row["monthly_rain_mm"][1] == pytest.approx(56.0)  # February 2010: 28 days x 2 mm
    assert row["annual_rain_mm"] is None  # a year with an empty month has no total
    assert row["longest_dry_spell_days"] is None
    assert row["missing_days"]["PRECTOTCORR"] == 1
    assert 3 not in row["drought_rain_months"]  # an empty month gets no drought reading


def test_leap_year_february_has_29_days():
    df = _frame(2024)
    normal = bc.monthly_climatology(df["PRECTOTCORR"])
    assert bc.cell_year(df, 2024, normal)["monthly_rain_mm"][1] == pytest.approx(58.0)
    assert bc.cell_year(df, 2023, normal)["monthly_rain_mm"][1] == pytest.approx(56.0)
    assert bc.days_in_month(1992, 2) == 29
    assert bc.days_in_month(1900, 2) == 28
    assert bc.days_in_month(2000, 2) == 29


def test_missing_leap_day_is_reported_by_the_calendar_check():
    idx = pd.date_range("1996-01-01", "1996-12-31", freq="D").drop(pd.Timestamp("1996-02-29"))
    problems = bc.check_calendar(idx, 1996, 1996)
    assert any("29 February" in p for p in problems)
    assert any("365 days, expected 366" in p for p in problems)


def test_hot_cold_and_dry_spell_counts():
    df = _frame(2010, rain=0.0)
    df.loc["2010-06-01":"2010-06-05", "T2M_MAX"] = 35.0  # 35 included (Art. 47.1 a lower bound)
    df.loc["2010-01-10":"2010-01-12", "T2M"] = 13.0  # 13 included (Art. 53.1 a upper bound)
    df.loc["2010-07-01", "PRECTOTCORR"] = 1.0  # 1 mm is a wet day for CDD (dry is below 1 mm)
    normal = bc.monthly_climatology(_frame(2010)["PRECTOTCORR"])
    row = bc.cell_year(df, 2010, normal)
    assert row["hot_days"] == 5
    assert row["cold_days"] == 3
    assert row["longest_dry_spell_days"] == 183  # 2 July .. 31 December (1 January .. 30 June is 181 days)
    assert row["drought_rain_months"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


def test_weighted_value_is_null_when_any_cell_is_null():
    assert bc.weighted([1.0, None], [0.5, 0.5]) is None
    assert bc.weighted([1.0, 3.0], [0.25, 0.75]) == pytest.approx(2.5)


def test_canonical_climate_covers_every_year_and_leap_year():
    path = CANON / "climate.json"
    if not path.exists():
        pytest.skip("build first")
    climate = json.loads(path.read_text(encoding="utf-8"))
    assert climate["years"] == list(range(1991, 2025))
    assert climate["leap_years_checked"] == [1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024]
    assert climate["is_forecast"] is False
    assert climate["is_field_measurement"] is False
    row = climate["series"]["farmland_weighted"]["2024"]
    assert sum(row["monthly_rain_mm"]) == pytest.approx(row["annual_rain_mm"], abs=0.6)
