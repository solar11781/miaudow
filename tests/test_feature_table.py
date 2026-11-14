"""Tests for the training feature table builder (written before the code, D-29).

Spec: one row per cleaned rice label (province, season, year) with its D-38 window and D-39 features; province weather
uses the one fixed farmland mask for all years (D-106; 05-DATA-CONTRACTS §3 cell_weights.csv); no rain normal is
stored (its normal comes from each fold's training years, D-66); the §4a counts are per cell then weighted (D-72);
rows that cannot be built (e.g. Mekong summer-autumn,
D-37) are returned in a skipped list with a reason, never silently dropped; missing inputs raise.
"""

import pandas as pd
import pytest

from fieldshift.features.feature_table import build_feature_table

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
