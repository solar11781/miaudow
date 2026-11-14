"""Tests for the rice stability rows and summary on hand-made risk_table.json rows (placeholder fractions).

Spec: UI-UX-SPEC §11 StabilityYear and Stability (oos_prediction only inside test_years and only if the model is
shown; range_80 only with it and only where G4 passed, D-94; summary over the non-null real values, null from fewer
than 2, D-95; worst_years equal to summary.min, ties give more than one); D-156 (median of an even count = the mean of
the two middle exact values, rounded once half up). Expected values worked out by hand (fraction x 100, half up).
"""

from fieldshift.engine.rules import RiskRow, RiskSeason
from fieldshift.engine.schemas import CropSpan, YearSpan
from fieldshift.engine.stability import RiceHistory, stability, stability_year, summary

TEST_YEARS = YearSpan(first=2016, last=2024)
T = {"vi": "[x]", "en": "[x]"}


def row(year: int, real: float | None, oos: float | None = None) -> RiskRow:
    return RiskRow(
        unit_id="Nghe An",
        crop="rice",
        season="spring",
        year=year,
        anom_history=real,
        anom_history_source_ids=["R-D01", "E-010"],
        anom_oos=oos,
        oos_low_80=None if oos is None else oos - 0.05,
        oos_high_80=None if oos is None else oos + 0.05,
        model_id=None if oos is None else "m1_ridge",
        anom_oos_source_ids=[] if oos is None else ["E-012"],
    )


def test_a_prediction_and_range_only_in_test_years_of_a_shown_season() -> None:
    inside = stability_year(row(2016, 0.01, 0.02), shown=True, g4_passed=True, test_years=TEST_YEARS)
    assert inside.oos_prediction is not None
    assert inside.oos_prediction.value == "2"
    assert inside.range_80 is not None
    assert (inside.range_80.low.value, inside.range_80.high.value) == ("-3", "7")  # 0.02 -/+ 0.05
    before = stability_year(row(2015, 0.01, 0.02), shown=True, g4_passed=True, test_years=TEST_YEARS)
    assert (before.oos_prediction, before.range_80) == (None, None)  # D-82: no model value before 2016
    not_shown = stability_year(row(2016, 0.01, 0.02), shown=False, g4_passed=True, test_years=TEST_YEARS)
    assert (not_shown.oos_prediction, not_shown.range_80) == (None, None)
    no_g4 = stability_year(row(2016, 0.01, 0.02), shown=True, g4_passed=False, test_years=TEST_YEARS)
    assert no_g4.oos_prediction is not None
    assert no_g4.range_80 is None  # D-94


def test_a_null_anomaly_stays_null() -> None:
    assert stability_year(row(1995, None), shown=False, g4_passed=False, test_years=TEST_YEARS).real is None


def test_summary_rounds_the_exact_median_once() -> None:
    found = summary([row(2001, 0.016), row(2002, 0.026), row(2003, None)])
    assert found is not None
    # median (0.016 + 0.026) / 2 = 0.021 -> 2; rounding each first would give (2 + 3) / 2 = 2.5 -> 3
    assert (found.min.value, found.median.value, found.max.value) == ("2", "2", "3")
    assert found.min.source_ids == ["R-D01", "E-010", "E-022"]  # the inputs plus the engine computation (D-158)


def test_no_summary_from_one_real_value() -> None:
    assert summary([row(2001, 0.016), row(2002, None)]) is None


def test_worst_years_are_every_year_equal_to_the_minimum() -> None:
    span = CropSpan(
        crop_key="usual_spring_rice",
        crop_id="rice",
        crop=T,
        variety=None,
        season="spring",
        sow_from=None,
        sow_to=None,
        harvest_from=None,
        harvest_to=None,
        source_ids=["R-P02"],
    )
    rows = {("spring", y): row(y, v) for y, v in [(2001, -0.104), (2002, 0.03), (2003, -0.096)]}
    seasons = {"spring": RiskSeason(season="spring", model_status="not_shown", model_id="m1_ridge")}
    history = RiceHistory(rows, seasons, frozenset(), TEST_YEARS, T)
    block = stability(span, T, [2001, 2002, 2003], history)
    assert block.worst_years == [2001, 2003]  # -10.4 and -9.6 both show "-10"
    assert block.years_count == 3
