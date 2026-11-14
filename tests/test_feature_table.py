"""Tests for the training feature table builder (written before the code, D-29).

Spec: one row per cleaned rice label (province, season, year) with its D-38 window and D-39 features; province weather
uses the one fixed farmland mask for all years (D-106; 05-DATA-CONTRACTS §3 cell_weights.csv); no rain normal is
stored (its normal comes from each fold's training years, D-66); the §4a counts are per cell then weighted (D-72);
rows that cannot be built (e.g. Mekong summer-autumn,
D-37) are returned in a skipped list with a reason, never silently dropped; missing inputs raise.
"""

import pandas as pd
import pytest

from fieldshift.features.feature_table import build_cell_month_rain, build_feature_table, build_risk_level_features

CELL_A, CELL_B = (19.0, 105.0), (19.0, 105.625)


def _cells():
    idx = pd.date_range("1990-01-01", "2020-12-31", freq="D", name="date")  # spec: normal needs 1991-2020

    def frame(rain):
        return pd.DataFrame(
            {
                "PRECTOTCORR": rain,
                "T2M_MAX": 30.0,
                "T2M_MIN": 20.0,
                "T2M": 25.0,
                "RH2M": 80.0,
                "WS2M": 2.0,
                "ALLSKY_SFC_SW_DWN": 18.0,
                "GWETROOT": 0.6,
            },
            index=idx,
        )

    return {CELL_A: frame(1.0), CELL_B: frame(3.0)}


def _weights(provinces=("P", "M")):
    rows = [(p, f"{c[0]}_{c[1]}", *c, 0.5, "farmland_weighted") for p in provinces for c in (CELL_A, CELL_B)]
    return pd.DataFrame(rows, columns=["province_nso", "cell_id", "lat", "lon", "farmland_weight", "method"])


def _labels():
    return pd.DataFrame(
        {
            "province_nso": ["P", "P", "M"],
            "crop": ["rice"] * 3,
            "season": ["spring", "spring", "autumn"],
            "year": [2010, 2011, 2010],
            "yield_t_ha": [5.0, 5.2, 4.0],
            "planted_area_ha": [9e4, 9e4, 5e4],
            "series_id": ["P|rice|spring|0", "P|rice|spring|0", "M|rice|autumn|0"],
            "fao_flagged": [False] * 3,
            "flag_2008_transfer": [False] * 3,
        }
    )


REGIONS = {"P": "north_central", "M": "mekong"}


def test_rows_windows_and_features():
    table, _ = build_feature_table(_labels(), _weights(), _cells(), REGIONS)
    assert len(table) == 2
    row = table[table.year == 2010].iloc[0]
    assert str(row.window_start)[:10] == "2010-02-01"
    assert str(row.window_end)[:10] == "2010-06-30"
    assert "landcover_year" not in table.columns  # D-106: no year-matched map
    assert row.precip_sum_mm == pytest.approx(2.0 * 150)  # province rain 2 mm/day x 150 days
    assert "rain_vs_normal_pct" not in table.columns  # D-66: per fold, not stored
    assert row.official_heavy_rain_d == 0
    assert row.ret_hai_d == 0
    assert row.ret_dam_d == 0
    assert row.n_points == 2  # 05 §4: cells aggregated (two weighted cells)
    assert row.yield_t_ha == 5.0
    assert row.calendar_region == "north_central"


def test_mekong_autumn_is_skipped_with_reason():
    _, skipped = build_feature_table(_labels(), _weights(), _cells(), REGIONS)
    assert len(skipped) == 1
    assert skipped.iloc[0].province_nso == "M"
    assert "D-37" in skipped.iloc[0].reason


def test_missing_weights_for_a_province_raises():
    with pytest.raises(KeyError):
        build_feature_table(_labels(), _weights(provinces=("M",)), _cells(), REGIONS)


def test_cell_month_rain_holds_each_cells_monthly_total_over_the_window():
    # Source: 05-DATA-CONTRACTS section 4a drought_rain_months: months with rain more than 50% below the same month's
    # mean over the training years, per cell then weighted (D-72), computed per fold, so each row needs its cells'
    # monthly totals. P spring (north_central, 2010): window 1 Feb - 30 Jun 2010 (calendar R-V05) = 5 months;
    # cell A rains 1 mm a day: February 28 mm, March 31 mm; cell B 3 mm a day: February 84 mm.
    m = build_cell_month_rain(_labels(), _weights(), _cells(), REGIONS)
    p10 = m[(m.province_nso == "P") & (m.season == "spring") & (m.year == 2010)]
    assert sorted(p10["month"].unique()) == ["2010-02", "2010-03", "2010-04", "2010-05", "2010-06"]
    a = p10[(p10.lat == 19.0) & (p10.lon == 105.0)].set_index("month")
    assert a.loc["2010-02", "rain_mm"] == pytest.approx(28.0)
    assert a.loc["2010-03", "rain_mm"] == pytest.approx(31.0)
    assert a.loc["2010-02", "farmland_weight"] == pytest.approx(0.5)
    b = p10[(p10.lat == 19.0) & (p10.lon == 105.625)].set_index("month")
    assert b.loc["2010-02", "rain_mm"] == pytest.approx(84.0)
    assert m[(m.province_nso == "M") & (m.season == "autumn")].empty  # Mekong summer-autumn has no window (D-37)


def test_a_shifted_window_moves_its_start_and_end_by_whole_months():
    # Source: E-008 (03-ML-SPEC section 7, team 2026-11-14): windows one month earlier, later, or wider on both ends;
    # P spring (north_central) is 1 Feb - 30 Jun 2010; wider: 1 Jan - 31 Jul; later: 1 Mar - 31 Jul
    wide, _ = build_feature_table(_labels(), _weights(), _cells(), REGIONS, shift=(-1, 1))
    row = wide[(wide.province_nso == "P") & (wide.year == 2010)].iloc[0]
    assert (row.window_start, row.window_end) == (pd.Timestamp("2010-01-01"), pd.Timestamp("2010-07-31"))
    later = build_cell_month_rain(_labels(), _weights(), _cells(), REGIONS, shift=(1, 1))
    months = sorted(later[(later.province_nso == "P") & (later.year == 2010)]["month"].unique())
    assert months == ["2010-03", "2010-04", "2010-05", "2010-06", "2010-07"]


def test_risk_level_features_give_one_row_per_label_with_the_three_shares():
    # Source: 03-ML-SPEC section 7 sensitivity (c) (team 2026-11-14): the farmland shares meeting the heavy-rain, heat
    # and cold rules over each row's season window; the toy weather meets none of them (30 C, 25 C, at most 3 mm)
    risk = build_risk_level_features(_labels(), _weights(), _cells(), REGIONS)
    assert len(risk) == 2  # the Mekong summer-autumn row has no window (D-37)
    assert set(risk.columns) == {"province_nso", "season", "year", "risk_heavy_rain", "risk_heat", "risk_cold"}
    assert (risk[["risk_heavy_rain", "risk_heat", "risk_cold"]] == 0.0).all(axis=None)
