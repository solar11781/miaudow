"""Tests for the primary test's metrics, gates and weather claim (03-ML-SPEC sections 6-8; 05-DATA-CONTRACTS 5b).

Expected values come from the gate table of 03-ML-SPEC section 8 (thresholds are team choices D-48, D-66) and from
hand-computed toy predictions:
- G1: >= 20 usable years and >= 40 provinces for spring and winter rice, >= 25 provinces for summer-autumn (D-71);
- G2: the model beats B0 and BNW, each skill > 0 with a year-bootstrap 90% CI that excludes 0 (D-83, D-99);
- G3: on the Nghe An / Ha Tinh / Thanh Hoa subset, fails only when the CI of the skill vs B2 lies entirely below 0;
- G4: the 80% interval covers 70-90% of the held-out outcomes;
- weather claim: made only if the model beats BNW on the test years (D-93), read as G2's BNW part.
"""

import pandas as pd
import pytest

from fieldshift.ml.primary_test import (
    app_season,
    g1_rows,
    gate_detail,
    metric_records,
    metric_row,
    penalty_report,
    season_gates,
    weather_claim,
)


def _pred() -> pd.DataFrame:
    # 2 test years x 2 rows; y = 1, -1, 1, -1 (mean 0, sum of squares 4); m1 misses by 0.1, b0/b2/bnw by 0.2:
    # skill = 1 - 0.01 / 0.04 = 0.75; r2_oos = 1 - 0.04 / 4 = 0.99; rows 1 and 3 inside their 80% interval: 0.5
    return pd.DataFrame(
        {
            "year": [2016, 2016, 2017, 2017],
            "y": [1.0, -1.0, 1.0, -1.0],
            "m1": [1.1, -1.1, 1.1, -1.1],
            "lo80": [1.0, -1.3, 0.95, -0.95],
            "hi80": [1.2, -1.2, 1.05, -0.9],
            "bnw": [1.2, -1.2, 1.2, -1.2],
            "b0": [1.2, -1.2, 1.2, -1.2],
            "b2": [1.2, -1.2, 1.2, -1.2],
        }
    )


def test_metric_row_scores_the_model_against_each_reference():
    row = metric_row(_pred(), "m1", seed=0, n_boot=200)
    assert row["rmse"] == pytest.approx(0.1)
    assert row["mae"] == pytest.approx(0.1)
    assert row["r2_oos"] == pytest.approx(0.99)
    assert row["skill_vs_b0"]["value"] == pytest.approx(0.75)
    assert row["skill_vs_bnw"]["value"] == pytest.approx(0.75)
    assert row["skill_vs_b0"]["ci90_low"] - 1e-9 <= 0.75 <= row["skill_vs_b0"]["ci90_high"] + 1e-9  # float sums
    assert row["coverage_80"] == pytest.approx(0.5)
    assert row["n_rows"] == 4
    assert row["n_test_years"] == 2


def test_a_reference_is_not_scored_against_itself_and_has_no_interval():
    row = metric_row(_pred(), "b0", seed=0, n_boot=200)
    assert row["skill_vs_b0"] is None
    assert row["coverage_80"] is None


def _skill(value: float, low: float, high: float) -> dict:
    return {"value": value, "ci90_low": low, "ci90_high": high}


def _m1(vs_b0: dict, vs_bnw: dict, coverage: float) -> dict:
    return {"skill_vs_b0": vs_b0, "skill_vs_bnw": vs_bnw, "coverage_80": coverage}


def test_g2_needs_both_references_beaten_with_a_ci_above_0():
    good, weak = _skill(0.1, 0.02, 0.2), _skill(0.1, -0.01, 0.2)
    pilot = {"skill_vs_b2": _skill(0.0, -0.1, 0.1)}
    assert season_gates(_m1(good, good, 0.8), pilot)["G2"] is True
    assert season_gates(_m1(good, weak, 0.8), pilot)["G2"] is False
    assert season_gates(_m1(_skill(-0.1, -0.2, -0.01), good, 0.8), pilot)["G2"] is False


def test_g3_fails_only_when_the_ci_vs_persistence_lies_below_0():
    m1 = _m1(_skill(0.1, 0.02, 0.2), _skill(0.1, 0.02, 0.2), 0.8)
    assert season_gates(m1, {"skill_vs_b2": _skill(-0.05, -0.2, 0.01)})["G3"] is True  # CI includes 0: a match
    assert season_gates(m1, {"skill_vs_b2": _skill(-0.1, -0.2, -0.01)})["G3"] is False


def test_g4_coverage_from_70_to_90_percent():
    good = _skill(0.1, 0.02, 0.2)
    pilot = {"skill_vs_b2": _skill(0.0, -0.1, 0.1)}
    assert [season_gates(_m1(good, good, c), pilot)["G4"] for c in (0.69, 0.70, 0.90, 0.91)] == [
        False,
        True,
        True,
        False,
    ]


def test_weather_claim_follows_the_bnw_part_of_g2():
    assert weather_claim(_m1(_skill(-0.5, -0.6, -0.4), _skill(0.1, 0.02, 0.2), 0.8)) is True
    assert weather_claim(_m1(_skill(0.1, 0.02, 0.2), _skill(0.1, -0.01, 0.2), 0.8)) is False


def test_g1_counts_usable_years_and_provinces_per_season():
    rows = pd.DataFrame(
        {
            "season": ["spring"] * 40 * 20 + ["autumn"] * 24 * 30,
            "province_nso": [f"p{i}" for i in range(40) for _ in range(20)]
            + [f"p{i}" for i in range(24) for _ in range(30)],
            "year": [1995 + y for _ in range(40) for y in range(20)] + [1995 + y for _ in range(24) for y in range(30)],
        }
    )
    out = {r["season"]: r["passed"] for r in g1_rows(rows)}
    assert out == {"spring": True, "autumn": False}  # 24 summer-autumn provinces < 25


def _labelled() -> pd.DataFrame:
    pred = pd.concat([_pred().assign(season=s) for s in ("spring", "winter")], ignore_index=True)
    return pred.assign(province_nso="Nghe An", region="North Central and Central coastal areas")


METRIC_KEYS = {  # UI-UX-SPEC section 11 MetricRow, 05-DATA-CONTRACTS section 5b
    "model_id", "season", "role", "scheme", "sensitivity", "detail", "subset", "rmse", "mae", "r2_oos",
    "skill_vs_b0", "skill_vs_b2", "skill_vs_bnw", "coverage_80", "n_rows", "n_test_years", "source_ids",
}  # fmt: skip


def test_metric_records_follow_the_contract_and_have_one_primary_row():
    # Source: D-83 and 03-ML-SPEC section 7: the one primary test is M1 on spring rice, rolling origin, national
    rows = metric_records(_labelled(), _labelled(), pilot=("Nghe An",), seed=0, n_boot=50)
    assert all(set(r) == METRIC_KEYS for r in rows)
    primary = [r for r in rows if r["role"] == "primary"]
    assert [(r["model_id"], r["season"], r["scheme"], r["subset"]) for r in primary] == [
        ("m1_ridge", "spring", "rolling_origin", "national")
    ]
    assert {r["role"] for r in rows if r["model_id"] in ("b0", "b2", "bnw")} == {"reference"}
    assert {r["scheme"] for r in rows} == {"rolling_origin", "spatial_holdout"}
    assert "region:north_central_and_central_coastal_areas" in {r["subset"] for r in rows}


def test_season_codes_are_the_app_codes():
    # Source: UI-UX-SPEC section 11 SeasonCode: spring | summer_autumn | winter | autumn_winter (NSO "autumn" rice is
    # the summer-autumn crop, 05-DATA-CONTRACTS section 2)
    assert app_season("autumn") == "summer_autumn"
    assert app_season("spring") == "spring"
    with pytest.raises(ValueError, match="unknown"):
        app_season("dry")


def test_gate_text_shows_three_decimals_and_vietnamese_decimal_commas():
    # Source: review 2026-11-14: a CI low of 0.0011 must not read as 0.00 next to a pass; Vietnamese writes 0,001
    skill = {"value": 0.0681, "ci90_low": 0.0011, "ci90_high": 0.1372}
    text = gate_detail("G2", {"skill_vs_b0": skill, "skill_vs_bnw": skill, "coverage_80": 0.76}, {})
    assert "0.001" in text["en"]
    assert "0,001" in text["vi"]
    assert "0.001" not in text["vi"]


def test_penalty_report_gives_the_share_of_test_years_at_a_grid_end():
    # Source: D-110: the chosen penalty is reported in grid units with the share of test years at an end of the grid
    item = penalty_report({"m1": 1 / 9, "bnw": 7 / 9})
    assert "11%" in item["text"]["en"]
    assert "78%" in item["text"]["en"]
    assert item["id"] == "E-012"
