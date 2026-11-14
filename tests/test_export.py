"""Tests for the app artifact artifacts/risk_table.json (05-DATA-CONTRACTS section 5; 03-ML-SPEC section 10).

Spec: one row per province x rice season x past year; anom_history = the real anomaly (null without a normal), sources
the NSO table R-D01 and the normal method E-010; anom_oos only for the test years 2016-2024, only for spring and winter
rice, only where that season's own test passed (D-82, D-83); the 80% interval only with anom_oos and only where G4
passed (D-94); model_id and anom_oos_source_ids only with anom_oos. seasons[]: model_status shown / not_shown /
not_modeled from gates.json by 03-ML-SPEC section 8 (shown = G2 and G3 pass; summer-autumn: G1 fails, not modeled).
Unit key: province_nso until the unit_id crosswalk exists (05-DATA-CONTRACTS section 2).
"""

import math

import pandas as pd
import pytest

from fieldshift.ml.export import risk_table


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "province_nso": ["Nghe An"] * 4,
            "season": ["spring", "winter", "winter", "autumn"],
            "year": [2016, 2010, 2016, 2016],
            "anom": [-0.05, math.nan, 0.02, 0.10],
        }
    )


def _pred() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "province_nso": ["Nghe An", "Nghe An"],
            "season": ["spring", "winter"],
            "year": [2016, 2016],
            "m1": [-0.01, 0.03],
            "lo80": [-0.09, -0.04],
            "hi80": [0.07, 0.10],
        }
    )


def _gates(winter_g4: bool = True) -> list[dict]:
    rows = [("G1", "spring", True), ("G2", "spring", False), ("G3", "spring", True), ("G4", "spring", True)]
    rows += [("G1", "winter", True), ("G2", "winter", True), ("G3", "winter", True), ("G4", "winter", winter_g4)]
    rows += [("G1", "summer_autumn", False)]
    return [{"gate": g, "season": s, "passed": p} for g, s, p in rows]


def _row(table: dict, season: str, year: int) -> dict:
    return next(r for r in table["rows"] if r["season"] == season and r["year"] == year)


def test_season_status_follows_the_gates():
    table = risk_table(_history(), _pred(), _gates(), freeze_commit="f", data_versions={})
    status = {s["season"]: (s["model_status"], s["model_id"]) for s in table["seasons"]}
    assert status == {
        "spring": ("not_shown", "m1_ridge"),
        "winter": ("shown", "m1_ridge"),
        "summer_autumn": ("not_modeled", None),
    }


def test_history_is_always_there_and_null_without_a_normal():
    table = risk_table(_history(), _pred(), _gates(), freeze_commit="f", data_versions={})
    assert _row(table, "winter", 2010)["anom_history"] is None
    assert _row(table, "spring", 2016)["anom_history"] == pytest.approx(-0.05)
    assert _row(table, "spring", 2016)["anom_history_source_ids"] == ["R-D01", "E-010"]
    assert _row(table, "summer_autumn", 2016)["anom_history"] == pytest.approx(0.10)


def test_predictions_only_for_a_season_whose_test_passed():
    table = risk_table(_history(), _pred(), _gates(), freeze_commit="f", data_versions={})
    spring = _row(table, "spring", 2016)
    assert (spring["anom_oos"], spring["model_id"], spring["anom_oos_source_ids"]) == (None, None, [])
    winter = _row(table, "winter", 2016)
    assert winter["anom_oos"] == pytest.approx(0.03)
    assert (winter["oos_low_80"], winter["oos_high_80"]) == (pytest.approx(-0.04), pytest.approx(0.10))
    assert (winter["model_id"], winter["anom_oos_source_ids"]) == ("m1_ridge", ["E-012"])
    assert _row(table, "summer_autumn", 2016)["anom_oos"] is None


def test_the_interval_needs_g4():
    table = risk_table(_history(), _pred(), _gates(winter_g4=False), freeze_commit="f", data_versions={})
    winter = _row(table, "winter", 2016)
    assert winter["anom_oos"] == pytest.approx(0.03)
    assert (winter["oos_low_80"], winter["oos_high_80"]) == (None, None)


def test_no_prediction_outside_the_test_years_or_without_g3():
    # Source: 05-DATA-CONTRACTS section 5: anom_oos "filled only for the test years 2016-2024" and only where the
    # season's own test (G2 and G3) passed; a 2011 prediction in the input must never reach the artifact
    history = pd.concat(
        [_history(), pd.DataFrame({"province_nso": ["Nghe An"], "season": ["winter"], "year": [2011], "anom": [0.01]})]
    )
    pred = pd.concat(
        [
            _pred(),
            pd.DataFrame(
                {
                    "province_nso": ["Nghe An"],
                    "season": ["winter"],
                    "year": [2011],
                    "m1": [0.5],
                    "lo80": [0.4],
                    "hi80": [0.6],
                }
            ),
        ]
    )
    table = risk_table(history, pred, _gates(), freeze_commit="f", data_versions={})
    assert _row(table, "winter", 2011)["anom_oos"] is None
    g3_fails = [g if (g["gate"], g["season"]) != ("G3", "winter") else {**g, "passed": False} for g in _gates()]
    table = risk_table(history, pred, g3_fails, freeze_commit="f", data_versions={})
    assert _row(table, "winter", 2016)["anom_oos"] is None


def test_a_modeled_season_without_its_gate_rows_fails_loudly():
    # Source: python rules (unknown data fails loudly): a modeled season needs its G2, G3 and G4 rows
    gates = [g for g in _gates() if (g["gate"], g["season"]) != ("G3", "winter")]
    with pytest.raises(ValueError, match=r"winter.*G3"):
        risk_table(_history(), _pred(), gates, freeze_commit="f", data_versions={})
    no_g1 = [g for g in _gates() if (g["gate"], g["season"]) != ("G1", "spring")]
    with pytest.raises(ValueError, match=r"G1.*spring"):
        risk_table(_history(), _pred(), no_g1, freeze_commit="f", data_versions={})
