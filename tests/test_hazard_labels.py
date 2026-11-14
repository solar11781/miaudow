"""Official risk-level label rows per P-02 plan crop and per year (written before the module).

Spec: 05-DATA-CONTRACTS §4b (rows, fields, sources, crop and year level, field dates and months), 03-ML-SPEC §5a
(field time from the sowing date to the first reported harvest date; months from the sowing month to the harvest
month; share = sum of the farmland weights of the cells where the rule was met), D-97. Expected values come from those
lines and from hand-made weather series, never from the module.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.engine.rules import hazard_rows
from fieldshift.features.hazard_labels import hazard_label_rows, plan_crops, year_window

RULES = ("heavy_rain", "heat", "drought_rain_consecutive", "drought_rain_any2", "cold")  # §4b rule codes


def _plan(plan_id: str, seasons: list[tuple]) -> dict:
    return {
        "id": plan_id,
        "seasons": [
            {
                "crop_key": key,
                "season": season,
                "sow_from": sow,
                "sow_to": sow,
                "harvest_from": harvest_from,
                "harvest_to": harvest_to,
            }
            for key, season, sow, harvest_from, harvest_to in seasons
        ],
    }


CC1 = _plan(
    "cc1",
    [
        ("cc1_spring_peanut", "spring", "01-18", "05-12", "05-12"),
        ("cc1_summer_autumn_mung_bean", "summer_autumn", "06-10", "08-30", "09-03"),  # P-02 harvest range "30/8 - 3/9"
    ],
)
P03 = _plan("usual_p03", [("usual_p03_spring_rice", "spring", None, None, None)])  # P-03 reports no dates


def test_plan_crops_use_the_sowing_and_first_harvest_dates_of_p02_plans_only() -> None:
    crops = plan_crops([P03, CC1])
    assert crops == [
        {
            "plan_id": "cc1",
            "crop_key": "cc1_spring_peanut",
            "season": "spring",
            "field_dates": [("01-18", "05-12")],
            "months": [1, 2, 3, 4, 5],
        },
        {
            "plan_id": "cc1",
            "crop_key": "cc1_summer_autumn_mung_bean",
            "season": "summer_autumn",
            "field_dates": [("06-10", "08-30")],  # D-97: the first reported harvest date
            "months": [6, 7, 8],  # §4b: sowing month to the month of the first reported harvest date
        },
    ]


def test_year_window_joins_the_field_time_of_every_crop() -> None:
    usual = _plan("usual", [("usual_summer_autumn_black_bean", "summer_autumn", "06-06", "08-25", "08-25")])
    same = _plan("cc2", [("cc2_spring_peanut", "spring", "01-18", "05-12", "05-12")])  # a pair already in cc1
    window = year_window(plan_crops([CC1, usual, same]))
    assert window == {
        "field_dates": [("01-18", "05-12"), ("06-06", "08-25"), ("06-10", "08-30")],
        "months": [1, 2, 3, 4, 5, 6, 7, 8],
    }


def _cell(**days: tuple[str, float]) -> pd.DataFrame:
    """A mild cell 1991-2024 that meets no rule (5 mm rain, 30 C max, 20 C mean each day) with the given days changed."""
    index = pd.date_range("1991-01-01", "2024-12-31", freq="D")
    frame = pd.DataFrame({"PRECTOTCORR": 5.0, "T2M_MAX": 30.0, "T2M": 20.0}, index=index)
    for column, changes in days.items():
        for day, value in changes:
            frame.loc[pd.Timestamp(day), column] = value
    return frame


CELLS = {
    (19.0, 105.0): _cell(PRECTOTCORR=[("2000-07-01", 120.0)]),  # heavy rain inside the mung bean field time
    (19.5, 105.0): _cell(
        T2M_MAX=[("2000-03-01", 36.0), ("2000-03-02", 36.0), ("2000-03-03", 36.0)],  # 3-day spell in one band
        PRECTOTCORR=[("2000-09-15", 150.0)],  # heavy rain after the first reported harvest date: not counted
    ),
}
WEIGHTS = {(19.0, 105.0): 0.75, (19.5, 105.0): 0.25}


def _share(rows: list[dict], level: str, crop_key: str | None, year: int, rule: str) -> float:
    (row,) = [r for r in rows if (r["level"], r["crop_key"], r["year"], r["rule"]) == (level, crop_key, year, rule)]
    return row["share_farmland"]


def test_rows_give_the_farmland_share_meeting_each_rule_per_crop_and_year() -> None:
    rows = hazard_label_rows(plan_crops([CC1]), CELLS, WEIGHTS, [2000, 2001])
    assert len(rows) == (2 + 1) * 2 * len(RULES)  # (2 crops + the year row) x 2 years x 5 rules
    mung = "cc1_summer_autumn_mung_bean"
    assert _share(rows, "crop", mung, 2000, "heavy_rain") == pytest.approx(0.75)
    assert _share(rows, "crop", mung, 2001, "heavy_rain") == 0.0
    assert _share(rows, "crop", "cc1_spring_peanut", 2000, "heat") == pytest.approx(0.25)
    assert _share(rows, "crop", mung, 2000, "heat") == 0.0
    assert _share(rows, "year", None, 2000, "heavy_rain") == pytest.approx(0.75)
    assert _share(rows, "year", None, 2000, "heat") == pytest.approx(0.25)
    for row in rows:
        assert row["n_cells"] == 2
        assert row["threshold_source_id"] == "R-A01"  # §4b
        assert row["values_source_ids"] == ["R-N01", "R-N02"]  # §4b
        assert row["computed_by"] == "E-019"  # EXPERIMENTS: computed_by of hazard_labels.json
        assert row["rule"] in RULES
    year_row = next(r for r in rows if r["level"] == "year")
    assert (year_row["plan_id"], year_row["crop_key"], year_row["season"]) == (None, None, None)
    assert year_row["months"] == [1, 2, 3, 4, 5, 6, 7, 8]
    crop_row = next(r for r in rows if r["crop_key"] == mung)
    assert (crop_row["plan_id"], crop_row["season"], crop_row["months"]) == ("cc1", "summer_autumn", [6, 7, 8])


def test_drought_month_flags_follow_the_1991_2020_monthly_mean() -> None:
    dry = _cell()
    dry.loc["2000-06-01":"2000-07-31", "PRECTOTCORR"] = 0.0  # two calendar-adjacent months with no rain
    rows = hazard_label_rows(plan_crops([CC1]), {(19.0, 105.0): dry}, {(19.0, 105.0): 1.0}, [2000])
    mung = "cc1_summer_autumn_mung_bean"
    assert _share(rows, "crop", mung, 2000, "drought_rain_consecutive") == 1.0
    assert _share(rows, "crop", mung, 2000, "drought_rain_any2") == 1.0
    assert _share(rows, "crop", "cc1_spring_peanut", 2000, "drought_rain_any2") == 0.0


def test_missing_weather_of_a_weighted_cell_fails_loudly() -> None:
    gap = _cell()
    gap.loc["2000-07-01", "T2M"] = np.nan
    with pytest.raises(ValueError, match=r"cc1_summer_autumn_mung_bean 2000 cell \(19\.0, 105\.0\)"):
        hazard_label_rows(plan_crops([CC1]), {(19.0, 105.0): gap}, {(19.0, 105.0): 1.0}, [2000])


def test_rows_pass_the_engine_artifact_check(tmp_path) -> None:
    rows = hazard_label_rows(plan_crops([CC1]), CELLS, WEIGHTS, [2000])
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "hazard_labels.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert len(hazard_rows(tmp_path)) == len(rows)


REPO = Path(__file__).resolve().parents[1]


def test_the_exported_artifact_has_every_p02_crop_year_and_rule() -> None:
    rows = hazard_rows(REPO)  # the engine's artifact check
    crop_rows = [r for r in rows if r.level == "crop"]
    assert len({r.crop_key for r in crop_rows}) == 15  # P-02: plans usual and cc1..cc4, three crops each (§4b)
    assert {r.year for r in rows} == set(range(1995, 2025))  # §4b: 1995..2024
    assert len(rows) == (15 + 1) * 30 * len(RULES)  # (crops + the year row) x years x rules
    assert all(r.share_farmland is not None for r in rows)
    doc = json.loads((REPO / "artifacts" / "hazard_labels.json").read_text(encoding="utf-8"))
    assert set(doc) == {"schema_version", "generated_at", "freeze_commit", "rows"}  # §4b


def test_a_sowing_range_fails_loudly() -> None:
    # 03-ML-SPEC section 5a: P-02 reports one sowing date per crop, so a range in the rules file is an input error
    ranged = _plan("cc1", [("cc1_spring_peanut", "spring", "01-18", "05-12", "05-12")])
    ranged["seasons"][0]["sow_to"] = "01-25"
    with pytest.raises(ValueError, match="cc1_spring_peanut"):
        plan_crops([ranged])


def test_a_rain_gap_in_the_normal_years_names_its_cell() -> None:
    # Python rules: errors name the input; the 1991-2020 rain normal needs every day (03-ML-SPEC section 5a, D-118)
    gap = _cell()
    gap.loc["2000-07-01", "PRECTOTCORR"] = np.nan
    with pytest.raises(ValueError, match=r"cell \(19\.0, 105\.0\)"):
        hazard_label_rows(plan_crops([CC1]), {(19.0, 105.0): gap}, {(19.0, 105.0): 1.0}, [2000])


def test_label_years_may_be_any_iterable() -> None:
    rows = hazard_label_rows(plan_crops([CC1]), CELLS, WEIGHTS, (y for y in (2000, 2001)))
    assert len(rows) == (2 + 1) * 2 * len(RULES)
