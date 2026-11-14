"""Tests for the method-page reports (05-DATA-CONTRACTS section 5b ReportItem; EXPERIMENTS E-012, E-014, E-016, E-018).

Expected values are counted by hand from the toy inputs below; the wording requirements come from the register:
E-012 and E-018 (the winter weather claim is to be worded as narrow and fragile), E-012, E-013 and E-017 (setup
choices disclosed on the method page), E-014 (count of seasons where the two drought readings differ, D-58) and
E-016 (heavy-rain years against DesInventar rice flood damage, agreement only, D-54).
"""

import pandas as pd
import pytest

from fieldshift.ml.reports import (
    drought_readings_report,
    heavy_rain_check_report,
    setup_report,
    winter_claim_report,
)


def _row(sensitivity: str | None, low: float, value: float = 0.068, high: float = 0.134) -> dict:
    return {
        "model_id": "m1_ridge",
        "season": "winter",
        "scheme": "rolling_origin",
        "subset": "national",
        "sensitivity": sensitivity,
        "skill_vs_bnw": {"value": value, "ci90_low": low, "ci90_high": high},
    }


def test_winter_claim_report_counts_the_runs_whose_interval_reaches_zero():
    # 4 sensitivity rows: lower ends -0.05 and -0.001 (below 0), 0.0001 (0.000 at 3 decimals), 0.011 (above 0)
    rows = [
        _row(None, 0.0029),
        _row("mae_skill", -0.05),
        _row("window", -0.001),
        _row("centroid_points", 0.0001),
        _row("no_fao_flagged", 0.011),
        {**_row("window", -0.5), "season": "spring"},  # another season: not counted
        {**_row("window", -0.5), "subset": "na_ht_th"},  # another subset: not counted
    ]
    item = winter_claim_report(rows)
    en, vi = item["text"]["en"], item["text"]["vi"]
    assert "0.068 (90% CI 0.003 to 0.134)" in en
    assert "0,068" in vi
    assert "0,003" in vi
    assert "2 of the 4 checking runs" in en
    assert "in 1 more it is 0.000" in en
    assert "2 trong 4" in vi
    assert item["id"] == "E-018"
    assert item["source_ids"] == ["E-012", "E-018", "E-008"]


def test_winter_claim_report_needs_sensitivity_rows():
    with pytest.raises(ValueError, match="no sensitivity rows"):
        winter_claim_report([_row(None, 0.0029)])


def test_setup_report_names_the_choices_and_their_sources():
    item = setup_report()
    assert item["id"] == "E-012"
    assert item["source_ids"] == ["E-012", "E-013", "E-017", "R-M25", "R-M26", "R-M12", "R-M27"]
    assert "after the features were frozen" in item["text"]["en"]
    assert item["text"]["vi"]


def test_drought_readings_report_counts_the_seasons_where_the_readings_differ():
    # 5 rows; they differ (any 2 months yes, 2 in a row no) in 2: Nghe An spring 2001 and Ha Tinh winter 2001
    readings = pd.DataFrame(
        {
            "province_nso": ["Nghe An", "Nghe An", "Nghe An", "Ha Tinh", "Ha Tinh"],
            "season": ["spring", "spring", "autumn", "winter", "winter"],
            "year": [2000, 2001, 2001, 2000, 2001],
            "consecutive": [True, False, False, False, False],
            "any2": [True, True, False, False, True],
        }
    )
    item = drought_readings_report(readings)
    en, vi = item["text"]["en"], item["text"]["vi"]
    assert "differ in 2 of 5 province seasons 2000-2001" in en
    assert "spring 1 of 2; summer-autumn 0 of 1; winter 1 of 2" in en
    assert "1 of 3 Nghệ An seasons" in en
    assert "2 trong 5" in vi
    assert item["id"] == "E-014"
    assert item["source_ids"] == ["E-014"]


def test_drought_readings_report_writes_thousands_with_the_language_separator():
    n = 1200
    readings = pd.DataFrame(
        {
            "province_nso": ["Nghe An"] * n,
            "season": ["spring"] * n,
            "year": [2000] * n,
            "consecutive": [False] * n,
            "any2": [False] * n,
        }
    )
    item = drought_readings_report(readings)
    assert "0 of 1,200" in item["text"]["en"]
    assert "0 trong 1.200" in item["text"]["vi"]


def test_heavy_rain_check_report_gives_agreement_counts_only():
    # years 2000-2004: heavy rain in 2000, 2001, 2002; recorded damage in 2001, 2002, 2003 -> both 2, heavy rain only 1
    # (2000), damage only 1 (2003), neither 1 (2004); agree in 3 of 5
    item = heavy_rain_check_report({2000, 2001, 2002}, {2001, 2002, 2003}, range(2000, 2005))
    en = item["text"]["en"]
    assert "both in 2 years" in en
    assert "heavy rain only in 1" in en
    assert "recorded damage only in 1" in en
    assert "neither in 1" in en
    assert "agree in 3 of 5 years" in en
    assert "2003" not in en  # no DesInventar year is shown (D-54: never republish its data)
    assert item["id"] == "E-016"
    assert item["source_ids"] == ["E-016", "R-A19", "E-019"]


def test_heavy_rain_check_report_refuses_years_outside_the_period():
    with pytest.raises(ValueError, match="outside"):
        heavy_rain_check_report({1990}, set(), range(2000, 2005))
