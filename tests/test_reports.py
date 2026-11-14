"""Tests for the method-page reports (05-DATA-CONTRACTS section 5b ReportItem; EXPERIMENTS E-012, E-014, E-016, E-018).

Expected values are counted by hand from the toy inputs below; the wording requirements come from the register:
E-012 and E-018 (the winter weather claim is to be worded as narrow and fragile), E-012, E-013 and E-017 (setup
choices disclosed on the method page), E-014 (count of seasons where the two drought readings differ, D-58, read per
cell then weighted, D-72) and E-016 (heavy-rain years against DesInventar rice flood damage, agreement only, D-54).
Labels come from rules/method.yaml (season_labels) and rules/conditions.yaml (the two drought readings).
"""

import pandas as pd
import pytest

from fieldshift.ml.reports import (
    drought_readings_report,
    heavy_rain_check_report,
    merge_reports,
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
    # a sensitivity row comes first: the main test is the row without a sensitivity label, not the first row.
    # 4 checking rows: lower ends -0.05 and -0.001 (below 0), 0.0001 (0.000 at 3 decimals), 0.011 (above 0);
    # largest drop of the lower end: 0.0029 - (-0.05) = 0.0529
    rows = [
        _row("mae_skill", -0.05, value=0.008),
        _row(None, 0.0029),
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
    assert "smaller than the largest drop of the lower end in one checking run (0.053)" in en
    assert "2 of the 4 checking runs" in en
    assert "in 1 more it is 0.000" in en
    assert "2 trong 4" in vi
    assert item["id"] == "E-018"
    assert item["source_ids"] == ["E-012", "E-018", "E-008"]


def test_winter_claim_report_needs_sensitivity_rows_and_one_main_row():
    with pytest.raises(ValueError, match="no sensitivity rows"):
        winter_claim_report([_row(None, 0.0029)])
    with pytest.raises(ValueError, match="main test"):
        winter_claim_report([_row("window", -0.01)])


def test_winter_claim_report_refuses_fragile_when_no_checking_run_reaches_zero():
    with pytest.raises(ValueError, match="not fragile"):
        winter_claim_report([_row(None, 0.0029), _row("window", 0.001)])


def test_winter_claim_report_refuses_narrow_when_the_lower_end_is_not_close_to_zero():
    # the only checking run drops the lower end by 0.0028, less than its distance 0.0029 from 0
    with pytest.raises(ValueError, match="not narrow"):
        winter_claim_report([_row(None, 0.0029), _row("window", 0.0001)])
    with pytest.raises(ValueError, match="not narrow"):
        winter_claim_report([_row(None, -0.01), _row("window", -0.02)])


def test_setup_report_puts_each_citation_next_to_its_choice():
    item = setup_report()
    en = item["text"]["en"]
    assert item["id"] == "E-012"
    assert item["source_ids"] == ["E-012", "E-013", "E-017", "R-M25", "R-M26", "R-M12", "R-M27"]
    assert "after the features were frozen" in en
    assert "the spring indicator times every weather feature (Lobell and Burke 2010)" in en
    assert "over the years before the test year (Ortiz-Bobea 2021, who warns" in en
    assert "unmeasured differences between places" in en
    assert "Lobell và Burke 2010" in item["text"]["vi"]


def _readings(consecutive: list[float], any2: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "province_nso": ["Nghe An", "Nghe An", "Nghe An", "Ha Tinh", "Ha Tinh"],
            "season": ["spring", "spring", "autumn", "winter", "winter"],
            "year": [2000, 2001, 2001, 2000, 2001],
            "consecutive": consecutive,
            "any2": any2,
        }
    )


def test_drought_readings_report_counts_the_seasons_whose_shares_differ():
    # farmland shares per row; they differ in 2 of 5: Nghe An spring 2001 (0.2 vs 0.5) and Ha Tinh winter 2001 (0 vs 1)
    item = drought_readings_report(_readings([1.0, 0.2, 0.0, 0.0, 0.0], [1.0, 0.5, 0.0, 0.0, 1.0]))
    en, vi = item["text"]["en"], item["text"]["vi"]
    assert "differ in 2 of 5 province seasons" in en
    assert "(spring season 1 of 2; summer-autumn season 0 of 1; winter season 1 of 2)" in en  # method.yaml labels
    assert "(vụ Đông Xuân: 1 trong 2" in vi
    assert "1 of 3 Nghệ An seasons" in en
    assert "2 trong 5" in vi
    assert '"Drought (rain part), 2 months in a row"' in en  # conditions.yaml labels of the two readings
    assert '"Hạn hán (phần lượng mưa), 2 tháng bất kỳ"' in vi
    assert "more than 50% below the 1991-2020 normal" in en
    assert "per NASA POWER cell" in en
    assert "with NSO rice yield data" in en
    assert item["id"] == "E-014"
    assert item["source_ids"] == ["E-014", "R-A01"]


def test_drought_readings_report_writes_thousands_with_the_language_separator():
    n = 1200
    readings = pd.DataFrame(
        {"province_nso": ["Nghe An"] * n, "season": ["spring"] * n, "year": [2000] * n, "consecutive": [0.0] * n}
    ).assign(any2=0.0)
    item = drought_readings_report(readings)
    assert "0 of 1,200" in item["text"]["en"]
    assert "0 trong 1.200" in item["text"]["vi"]


def test_heavy_rain_check_report_gives_agreement_counts_and_the_chance_agreement():
    # years 2000-2004: heavy rain in 2000, 2001, 2002; recorded damage in 2001, 2002, 2003 -> both 2, heavy rain only 1
    # (2000), damage only 1 (2003), neither 1 (2004); agree in 3 of 5. Chance agreement from the same margins:
    # 5 x (3/5 x 3/5 + 2/5 x 2/5) = 2.6
    item = heavy_rain_check_report({2000, 2001, 2002}, {2001, 2002, 2003}, range(2000, 2005))
    en, vi = item["text"]["en"], item["text"]["vi"]
    assert "Both in 2 years" in en
    assert "heavy rain only in 1" in en
    assert "recorded damage only in 1" in en
    assert "neither in 1" in en
    assert "agree in 3 of 5 years" in en
    assert "about 2.6 of 5" in en
    assert "2,6" in vi
    assert "only the DesInventar flood, flash flood and inundation records with rice area damaged count" in en
    assert "cyclone, hailstorm and storm, are left out" in en
    assert "lốc tố, lốc kèm mưa đá và bão" in vi
    assert "above 0 (our reading)" in en
    assert "2003" not in en  # no DesInventar year is shown (D-54: never republish its data)
    assert item["id"] == "E-016"
    assert item["source_ids"] == ["E-016", "R-A19", "E-019"]


def test_heavy_rain_check_report_refuses_years_outside_the_period():
    with pytest.raises(ValueError, match="outside"):
        heavy_rain_check_report({1990}, set(), range(2000, 2005))


def _report(rid: str, title: str) -> dict:
    return {"id": rid, "title": {"vi": title, "en": title}, "text": {"vi": "t", "en": "t"}, "source_ids": [rid]}


def test_merge_reports_replaces_by_slot_so_a_changed_title_never_duplicates():
    # run_primary_test.py writes E-010, E-012 (zero-weight cells) and E-012 (penalty); this script adds four reports
    primary = [_report("E-010", "normal"), _report("E-012", "zero"), _report("E-012", "penalty")]
    new = {
        "winter_claim": _report("E-018", "winter"),
        "setup": _report("E-012", "setup"),
        "drought_readings": _report("E-014", "drought"),
        "heavy_rain_check": _report("E-016", "check"),
    }
    first = merge_reports(primary, new)
    assert [r["title"]["en"] for r in first] == ["normal", "zero", "penalty", "winter", "setup", "drought", "check"]
    again = merge_reports(first, {**new, "setup": _report("E-012", "setup renamed")})
    assert [r["title"]["en"] for r in again] == [
        "normal",
        "zero",
        "penalty",
        "winter",
        "setup renamed",
        "drought",
        "check",
    ]


def test_merge_reports_refuses_a_slot_that_would_land_elsewhere():
    # the setup slot is the third E-012 report; with only one E-012 report present it would become the second
    with pytest.raises(ValueError, match="slot"):
        merge_reports([_report("E-012", "zero")], {"setup": _report("E-012", "setup")})
