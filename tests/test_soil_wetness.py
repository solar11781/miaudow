"""Soil wetness rows per P-02 plan crop and past year (written before the module).

Spec: 05-DATA-CONTRACTS §4d (field-day mean of daily GWETROOT per cell, farmland-weighted; 1991-2020 normal of the same
mean; a missing day gives null, never filled; a normal needs all 30 years; fields and sources), D-97, D-135. Expected
values are hand-computed from the series below, never taken from the module.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.features.hazard_labels import plan_crops
from fieldshift.features.soil_wetness import soil_wetness_rows

CC1 = {
    "id": "cc1",
    "seasons": [
        {
            "crop_key": "cc1_summer_autumn_mung_bean",
            "season": "summer_autumn",
            "sow_from": "06-10",
            "sow_to": "06-10",
            "harvest_from": "08-30",  # P-02 harvest range "30/8 - 3/9": the first reported date (D-97)
            "harvest_to": "09-03",
        }
    ],
}
A, B = (19.0, 105.0), (19.5, 105.0)


def _cell(level: float) -> pd.DataFrame:
    index = pd.date_range("1991-01-01", "2024-12-31", freq="D")
    return pd.DataFrame({"GWETROOT": level}, index=index)


def _cells() -> dict:
    a, b = _cell(0.4), _cell(0.2)
    a.loc["2000-06-10":"2000-08-30", "GWETROOT"] = 0.6  # wetter field days in 2000
    a.loc["2000-08-31":"2000-09-03", "GWETROOT"] = 1.0  # after the first reported harvest date: not counted
    return {A: a, B: b}


WEIGHTS = {A: 0.75, B: 0.25}


def _row(rows: list[dict], year: int) -> dict:
    (row,) = [r for r in rows if r["year"] == year]
    return row


def test_value_is_the_weighted_field_day_mean_and_normal_the_1991_2020_mean():
    rows = soil_wetness_rows(plan_crops([CC1]), _cells(), WEIGHTS, [2000, 2001])
    assert _row(rows, 2000)["value"] == pytest.approx(0.75 * 0.6 + 0.25 * 0.2)
    assert _row(rows, 2001)["value"] == pytest.approx(0.75 * 0.4 + 0.25 * 0.2)
    normal = 0.75 * (29 * 0.4 + 0.6) / 30 + 0.25 * 0.2  # cell A: 29 years at 0.4 and 2000 at 0.6
    assert _row(rows, 2000)["normal"] == pytest.approx(normal)
    assert _row(rows, 2001)["normal"] == pytest.approx(normal)


def test_rows_carry_the_crop_keys_counts_and_sources():
    rows = soil_wetness_rows(plan_crops([CC1]), _cells(), WEIGHTS, [2000, 2001])
    assert len(rows) == 2  # one row per plan crop x year
    row = rows[0]
    assert (row["plan_id"], row["crop_key"], row["season"]) == ("cc1", "cc1_summer_autumn_mung_bean", "summer_autumn")
    assert row["field_dates"] == [["06-10", "08-30"]]
    assert row["n_cells"] == 2
    assert row["source_ids"] == ["R-N01", "R-W12", "R-N02", "R-A15"]  # §4d
    assert row["computed_by"] == "E-020"  # EXPERIMENTS: computed_by of soil_wetness.json


def test_a_missing_day_gives_no_value_for_that_year_and_no_normal_without_all_30_years():
    cells = _cells()
    cells[B].loc["2005-07-01", "GWETROOT"] = np.nan
    rows = soil_wetness_rows(plan_crops([CC1]), cells, WEIGHTS, [2005, 2006])
    assert _row(rows, 2005)["value"] is None  # never filled from the other cell
    assert _row(rows, 2006)["value"] == pytest.approx(0.75 * 0.4 + 0.25 * 0.2)
    assert _row(rows, 2006)["normal"] is None  # 2005 lies inside 1991-2020, so cell B has 29 years only


def test_a_day_absent_from_the_data_counts_as_missing():
    cells = _cells()
    cells[A] = cells[A].drop(pd.Timestamp("2010-07-01"))
    rows = soil_wetness_rows(plan_crops([CC1]), cells, WEIGHTS, [2010])
    assert rows[0]["value"] is None


REPO = Path(__file__).resolve().parents[1]


def test_the_exported_artifact_has_every_p02_crop_and_year():
    doc = json.loads((REPO / "artifacts" / "soil_wetness.json").read_text(encoding="utf-8"))
    assert set(doc) == {"schema_version", "generated_at", "freeze_commit", "rows"}  # §4d
    rows = doc["rows"]
    assert len({r["crop_key"] for r in rows}) == 15  # P-02: plans usual and cc1..cc4, three crops each
    assert {r["year"] for r in rows} == set(range(1995, 2025))  # §4d: 1995..2024
    assert len(rows) == 15 * 30
    keys = {"plan_id", "crop_key", "season", "field_dates", "year", "value", "normal", "n_cells", "source_ids"}
    for row in rows:
        assert set(row) == keys | {"computed_by"}
        for field in ("value", "normal"):
            assert row[field] is None or 0.0 <= row[field] <= 1.0  # GWETROOT: 0 dry to 1 saturated (R-W12)


def test_a_cell_without_soil_wetness_names_the_crop_and_cell() -> None:
    # Python rules: errors name the input
    cells = _cells()
    cells[B] = cells[B].drop(columns="GWETROOT")
    with pytest.raises(ValueError, match=r"cc1_summer_autumn_mung_bean cell \(19\.5, 105\.0\)"):
        soil_wetness_rows(plan_crops([CC1]), cells, WEIGHTS, [2000])


def test_years_may_be_any_iterable() -> None:
    rows = soil_wetness_rows(plan_crops([CC1]), _cells(), WEIGHTS, (y for y in (2000, 2001)))
    assert [r["year"] for r in rows] == [2000, 2001]
