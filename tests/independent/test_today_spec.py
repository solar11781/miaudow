"""Independent spec tests for code written on 2026-11-12.

Written only from the specifications (docs/03-ML-SPEC.md, docs/05-DATA-CONTRACTS.md, docs/DECISION-LOG.md,
research/evidence-audit-findings.md, docs/REVIEWS.md evidence audit) and the cited source text. No file under src/ or the
other test files was read. Every expected value is computed by hand in the comments. Synthetic data only.
"""

import math

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon, box

from fieldshift.data import series as series_mod
from fieldshift.features import climate as climate_mod
from fieldshift.features import farmland_weights as farmland_mod
from fieldshift.features import hazards as hazards_mod
from fieldshift.ml import evaluation as eval_mod
from fieldshift.ml import normal as normal_mod

# ----------------------------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------------------------


def _series_frame(province, crop, season, years, areas, yields=None):
    years = list(years)
    if np.isscalar(areas):
        areas = [areas] * len(years)
    if yields is None:
        yields = [5.0] * len(years)
    return pd.DataFrame(
        {
            "province_nso": province,
            "crop": crop,
            "season": season,
            "year": years,
            "planted_area_ha": [float(a) for a in areas],
            "yield_t_ha": [float(y) for y in yields],
        }
    )


def _sid(out, province, crop, season, year):
    row = out[
        (out["province_nso"] == province) & (out["crop"] == crop) & (out["season"] == season) & (out["year"] == year)
    ]
    assert len(row) == 1, (province, crop, season, year, len(row))
    return row["series_id"].iloc[0]


def _positions(part, n):
    a = np.asarray(part)
    if a.dtype == bool:
        assert len(a) == n
        return sorted(np.flatnonzero(a).tolist())
    return sorted(a.astype(int).tolist())


def _norm_keys(d):
    return {(round(float(k[0]), 4), round(float(k[1]), 4)): float(v) for k, v in d.items() if float(v) > 0}


# ----------------------------------------------------------------------------------------------------------------
# 1. series: 2004 named breaks (03-ML-SPEC §3, D-56 d, evidence audit EV-01)
# ----------------------------------------------------------------------------------------------------------------
# 03-ML-SPEC §3: "the 2004 province splits (Nghị quyết 22/2003/QH11: Cần Thơ, Đắk Lắk, Lai Châu; Than Uyên from Lào
# Cai; NSO footnote on 1995-2003 merged values) start new series in 2004 as named rules (like Hà Tây 2008); the > 50%
# area-change rule (D-28) stays for other units."
# evidence audit EV-01: "start a new series in 2004 for these 4 units by a named rule (as Hà Tây 2008)".
# NSO English names checked against the parsed NSO table: "Can Tho", "Dak Lak", "Lai Chau", "Lao Cai".

YEARS = list(range(1995, 2011))


@pytest.mark.parametrize(
    ("province", "season", "before", "after"),
    [
        # [DATA] values from research/evidence-audit-findings.md "NSO method": drops below 50%, missed by D-28
        ("Can Tho", "spring", 177600, 93900),  # -47%
        ("Lai Chau", "winter", 47500, 24200),  # -49%
        ("Dak Lak", "winter", 49300, 41900),  # -15%
        ("Lao Cai", "winter", 26900, 19600),  # -27%
    ],
)
def test_named_2004_break_for_split_units(province, season, before, after):
    areas = [before if y < 2004 else after for y in YEARS]
    df = _series_frame(province, "rice", season, YEARS, areas)
    out, _removed = series_mod.prepare_series(df)
    # a new series starts in 2004
    assert _sid(out, province, "rice", season, 2003) != _sid(out, province, "rice", season, 2004)
    # one series 1995-2003 and one series 2004-2010 (no other break)
    assert len({_sid(out, province, "rice", season, y) for y in range(1995, 2004)}) == 1
    assert len({_sid(out, province, "rice", season, y) for y in range(2004, 2011)}) == 1


def test_named_2004_break_applies_even_without_area_change():
    # "named rules (like Hà Tây 2008)": the rule is set by the law, not by the data; constant area still splits
    df = _series_frame("Can Tho", "rice", "spring", YEARS, 100000)
    out, _ = series_mod.prepare_series(df)
    assert _sid(out, "Can Tho", "rice", "spring", 2003) != _sid(out, "Can Tho", "rice", "spring", 2004)


def test_named_2004_break_applies_to_every_crop_of_the_unit():
    # the unit itself changed on 1/1/2004 (Nghị quyết 22/2003/QH11), so every series of that unit is affected
    df = _series_frame("Lao Cai", "maize", "annual", YEARS, 30000)
    out, _ = series_mod.prepare_series(df)
    assert _sid(out, "Lao Cai", "maize", "annual", 2003) != _sid(out, "Lao Cai", "maize", "annual", 2004)


def test_no_2004_break_for_other_units_below_50_percent():
    # "the > 50% area-change rule (D-28) stays for other units": Nghệ An with a 47% drop in 2004 keeps one series
    # (D-28: "|new - old| / old > 0.5"; (177600 - 93900) / 177600 = 0.471 <= 0.5)
    areas = [177600 if y < 2004 else 93900 for y in YEARS]
    df = _series_frame("Nghe An", "rice", "spring", YEARS, areas)
    out, _ = series_mod.prepare_series(df)
    assert len(set(out["series_id"])) == 1


def test_2004_split_then_small_series_rule_uses_the_split_series():
    # D-32: "drop every cleaned series (series_id, after D-28/D-31 splitting) whose median planted area is under
    # 2,000 ha". Lai Châu spring: 2,600 ha 1995-2003 (9 years), 1,900 ha 2004-2024 (21 years), -27%: no D-28 break.
    # After the named split: 1995-2003 median 2,600 (kept), 2004-2024 median 1,900 (< 2,000, removed).
    # Without the split the single series median would be 1,900 and everything would be removed.
    years = list(range(1995, 2025))
    areas = [2600 if y < 2004 else 1900 for y in years]
    df = _series_frame("Lai Chau", "rice", "spring", years, areas)
    out, removed = series_mod.prepare_series(df)
    assert sorted(out["year"].tolist()) == list(range(1995, 2004))
    assert sorted(removed["year"].tolist()) == list(range(2004, 2025))


# ----------------------------------------------------------------------------------------------------------------
# 2. series: FAO +-30% flag (D-56 d, D-70)
# ----------------------------------------------------------------------------------------------------------------
# D-70: "prev_avg = right-aligned 3-year rolling mean lagged one year; flag when yield < prev_avg - 0.3 prev_avg or
# > prev_avg + 0.3 prev_avg (both directions); no check when fewer than 3 previous years exist (the rolling mean is
# missing). Flagged rows are kept and listed".
# 03-ML-SPEC §3: "Low-yield flag = yield outside +-30% of the previous 3-year mean".


def _fao(series_yields, start=2000, shuffle=False):
    rows = []
    for sid, ys in series_yields.items():
        for i, y in enumerate(ys):
            rows.append({"series_id": sid, "year": start + i, "yield_t_ha": float(y)})
    df = pd.DataFrame(rows)
    if shuffle:
        df = df.sample(frac=1.0, random_state=3).reset_index(drop=True)
    out = series_mod.flag_fao_outliers(df)
    if out is None:
        out = df
    return out


def _flags(out, sid):
    sub = out[out["series_id"] == sid].sort_values("year")
    return [bool(v) for v in sub["fao_flagged"]]


def test_fao_flag_boundaries_are_strict():
    out = _fao(
        {
            # prev_avg = 10; lower bound 10 - 3 = 7.0; upper bound 13.0; strict "<" and ">"
            "a": [10, 10, 10, 7.0],
            "b": [10, 10, 10, 6.99],
            "c": [10, 10, 10, 13.0],
            "d": [10, 10, 10, 13.01],
        }
    )
    assert _flags(out, "a") == [False, False, False, False]
    assert _flags(out, "b") == [False, False, False, True]
    assert _flags(out, "c") == [False, False, False, False]
    assert _flags(out, "d") == [False, False, False, True]


def test_fao_flag_no_check_in_first_three_years():
    # "no check when fewer than 3 previous years exist": huge jumps in years 1-3 are never flagged
    out = _fao({"e": [1, 50, 100]})
    assert _flags(out, "e") == [False, False, False]


def test_fao_flag_rows_kept():
    # "Flagged rows are kept": no row is dropped by the flag
    df_in = {"b": [10, 10, 10, 6.99, 10]}
    out = _fao(df_in)
    assert len(out) == 5


def test_fao_flag_rolling_mean_includes_flagged_years():
    # prev_avg is the plain rolling mean of the previous 3 yields (D-70 defines no exclusion of flagged years).
    # year4 = 20 > 13 -> flagged; year5: prev_avg = (10 + 10 + 20) / 3 = 13.333; lower bound 9.333; 9.0 -> flagged
    out = _fao({"f": [10, 10, 10, 20, 9.0]})
    assert _flags(out, "f") == [False, False, False, True, True]


def test_fao_flag_uses_only_three_previous_years():
    # 3-year window, not all past years: year4 prev = (100+10+10)/3 = 40 -> 10 < 28 flagged;
    # year5 prev = (10+10+10)/3 = 10 -> 10 not flagged (an expanding mean 32.5 would flag it)
    out = _fao({"g": [100, 10, 10, 10, 10]})
    assert _flags(out, "g") == [False, False, False, True, False]


def test_fao_flag_restarts_in_each_series():
    # a new series has no previous years of its own (rolling mean inside the series)
    rows = [{"series_id": "h1", "year": y, "yield_t_ha": 10.0} for y in (2000, 2001, 2002)]
    rows += [{"series_id": "h2", "year": y, "yield_t_ha": 5.0} for y in (2003, 2004, 2005, 2006)]
    df = pd.DataFrame(rows)
    out = series_mod.flag_fao_outliers(df)
    if out is None:
        out = df
    assert _flags(out, "h2") == [False, False, False, False]


def test_fao_flag_independent_of_row_order():
    out = _fao({"f": [10, 10, 10, 20, 9.0], "g": [100, 10, 10, 10, 10]}, shuffle=True)
    assert _flags(out, "f") == [False, False, False, True, True]
    assert _flags(out, "g") == [False, False, False, True, False]


# ----------------------------------------------------------------------------------------------------------------
# 3. normal yield and percent anomaly (03-ML-SPEC §3, D-66, D-72)
# ----------------------------------------------------------------------------------------------------------------
# 03-ML-SPEC §3: "anom[p,c,t] = yield[p,c,t] / normal[p,c](t) - 1"; "3-year past mean (Iizumi and Ramankutty 2016:
# 'three-year RM yield (year t-3 to t-1)'); 5-year linear trend (Paudel et al. 2021); a normal exists only when that
# many past years exist." findings: Paudel 2021 "baseline = linear trend from a 5-year window".
# "Years without a normal ... have no anomaly: the value is null".


def _yield_frame(series):
    rows = []
    for sid, (start, ys) in series.items():
        for i, y in enumerate(ys):
            rows.append({"series_id": sid, "year": start + i, "yield_t_ha": float(y)})
    return pd.DataFrame(rows)


def _by_year(df, values, sid):
    s = pd.Series(np.asarray(values, dtype=float), index=df.index)
    sub = df[df["series_id"] == sid]
    return dict(zip(sub["year"], s.loc[sub.index], strict=True))


def test_mean3_normal_values():
    df = _yield_frame({"A": (2000, [4, 5, 6, 8, 9, 10])})
    nrm = _by_year(df, normal_mod.past_normal(df, "mean3"), "A")
    # 2000-2002: fewer than 3 past years -> no normal
    assert all(math.isnan(nrm[y]) for y in (2000, 2001, 2002))
    assert nrm[2003] == pytest.approx(5.0)  # (4+5+6)/3
    assert nrm[2004] == pytest.approx(19 / 3)  # (5+6+8)/3
    assert nrm[2005] == pytest.approx(23 / 3)  # (6+8+9)/3


def test_trend5_normal_values():
    # 2000-2004 yields 10, 12, 11, 13, 14: x = -2..2, mean 12, slope = (4+0+0+1+4)/10 = 0.9 -> at 2005: 12 + 3*0.9
    # = 14.7. 2001-2005 yields 12, 11, 13, 14, 15: mean 13, slope = (2+2+0+1+4)/10 = 0.9 -> at 2006: 15.7
    df = _yield_frame({"A": (2000, [10, 12, 11, 13, 14, 15, 99])})
    nrm = _by_year(df, normal_mod.past_normal(df, "trend5"), "A")
    assert all(math.isnan(nrm[y]) for y in range(2000, 2005))
    assert nrm[2005] == pytest.approx(14.7)
    assert nrm[2006] == pytest.approx(15.7)


@pytest.mark.parametrize("method", ["mean3", "trend5"])
def test_normal_is_past_only(method):
    # "normal is fitted only on years before the test year" (Paudel et al. 2021): the year's own yield and later
    # yields never change it
    base = [10, 12, 11, 13, 14, 15, 16, 17]
    df1 = _yield_frame({"A": (2000, base)})
    changed = [*base[:6], 500, -3]  # change 2006 and 2007
    df2 = _yield_frame({"A": (2000, changed)})
    n1 = _by_year(df1, normal_mod.past_normal(df1, method), "A")
    n2 = _by_year(df2, normal_mod.past_normal(df2, method), "A")
    assert n1[2006] == pytest.approx(n2[2006])
    for y in range(2000, 2007):
        if math.isnan(n1[y]):
            assert math.isnan(n2[y])
        else:
            assert n1[y] == pytest.approx(n2[y])


@pytest.mark.parametrize(("method", "first"), [("mean3", 3), ("trend5", 5)])
def test_normal_restarts_in_each_series(method, first):
    # "per province x rice season" and series split at breaks: the second series has no past years of its own
    df = _yield_frame({"A": (2000, [10] * 8), "B": (2008, [3] * 8)})
    nrm = _by_year(df, normal_mod.past_normal(df, method), "B")
    for y in range(2008, 2008 + first):
        assert math.isnan(nrm[y])
    assert nrm[2008 + first] == pytest.approx(3.0)


def test_add_anomaly_percent_form_and_null_without_normal():
    df = _yield_frame({"A": (2000, [4, 5, 6, 8, 9, 10])})
    df = df.sample(frac=1.0, random_state=1)  # row order must not matter
    out = normal_mod.add_anomaly(df, "mean3")
    if out is None:
        out = df
    assert len(out) == 6  # rows without a normal are kept with a null value
    o = out.set_index("year")
    assert o.loc[2003, "normal_t_ha"] == pytest.approx(5.0)
    assert o.loc[2003, "anom"] == pytest.approx(8 / 5 - 1)  # 0.6
    assert o.loc[2004, "anom"] == pytest.approx(9 / (19 / 3) - 1)  # 0.42105
    assert o.loc[2005, "anom"] == pytest.approx(10 / (23 / 3) - 1)
    for y in (2000, 2001, 2002):
        assert pd.isna(o.loc[y, "anom"])
        assert pd.isna(o.loc[y, "normal_t_ha"])


def test_unknown_normal_method_rejected():
    # D-72: "Only these two candidates are used"
    df = _yield_frame({"A": (2000, [4, 5, 6, 8, 9, 10])})
    with pytest.raises(ValueError, match=r"unknown normal method"):
        normal_mod.past_normal(df, "mm")


# ----------------------------------------------------------------------------------------------------------------
# 4. farmland mask and cell weights (03-ML-SPEC §4, 05 §3, D-36, D-106, D-107, D-146)
# ----------------------------------------------------------------------------------------------------------------
# 03-ML-SPEC §4: "each 0.05 deg pixel's farmland share is its minimum MODIS cropland percent over 2001-2015, with IGBP
# class 12 (croplands, 'At least 60%' cultivated) counted at 80%, the middle of 60-100% (D-146), and class 14
# (cropland/natural vegetation mosaics, 'small-scale cultivation 40-60%', R-K10) counted at 50%". MCD12C1 Land_Cover_Type_1_Percent: 17 layers, one per IGBP class
# 0-16 (0 = water), so layer 12 = croplands and layer 14 = mosaics.


def _percent(rows, cols, p12=0, p14=0, other=None):
    a = np.zeros((rows, cols, 17), dtype=np.uint8)
    a[:, :, 12] = p12
    a[:, :, 14] = p14
    rest = 100 - a[:, :, 12].astype(int) - a[:, :, 14].astype(int)
    a[:, :, 10] = rest.astype(np.uint8)  # remainder grassland so each pixel sums to 100
    return a


def test_farmland_fraction_class_weights():
    a = np.zeros((1, 5, 17), dtype=np.uint8)
    a[0, 0, 12] = 100  # all cropland -> 0.8 (D-146)
    a[0, 1, 14] = 100  # all mosaic -> 0.5
    a[0, 2, 12] = 60
    a[0, 2, 14] = 40  # 0.48 + 0.2 = 0.68
    a[0, 3, 10] = 100  # grassland -> 0
    a[0, 4, 13] = 50
    a[0, 4, 0] = 50  # urban + water -> 0
    f = np.asarray(farmland_mod.farmland_fraction(a), dtype=float)
    assert f.shape == (1, 5)
    np.testing.assert_allclose(f[0], [0.8, 0.5, 0.68, 0.0, 0.0], atol=1e-9)


def _years_grid(per_year, lat_max=19.5, lon_min=105.0, cell=0.05):
    return {y: {"percent": p, "lat_max": lat_max, "lon_min": lon_min, "cell": cell} for y, p in per_year.items()}


def test_fixed_mask_minimum_of_combined_share():
    # pixel (0,0), class 12 at 0.8 (D-146): 2001 -> 0.48 (p12 60); 2002 -> 0.16 + 0.4 = 0.56 (p12 20, p14 80); other
    # years 0.56 (p12 70) -> min 0.48. (taking the minimum of p12 and p14 separately would give 0.16 + 0 = 0.16)
    # pixel (0,1): p14 100 (0.5) every year except 2010 p14 50 (0.25) -> 0.25
    per_year = {}
    for y in range(2001, 2016):
        a = np.zeros((1, 2, 17), dtype=np.uint8)
        a[0, 0, 12] = 70
        a[0, 1, 14] = 100
        if y == 2001:
            a[0, 0, 12] = 60
        if y == 2002:
            a[0, 0, 12] = 20
            a[0, 0, 14] = 80
        if y == 2010:
            a[0, 1, 14] = 50
        per_year[y] = a
    m = farmland_mod.fixed_farmland_mask(_years_grid(per_year))
    np.testing.assert_allclose(np.asarray(m["farmland"], dtype=float), [[0.48, 0.25]], atol=1e-9)
    assert m["lat_max"] == 19.5
    assert m["lon_min"] == 105.0
    assert m["cell"] == 0.05


def test_fixed_mask_does_not_use_test_years():
    # "built from years before the first test year 2016"; "a map from a test year would use later information":
    # a 2016 map is either refused or ignored
    per_year = {y: _percent(1, 1, p12=50) for y in range(2001, 2016)}
    per_year[2016] = _percent(1, 1, p12=0)
    try:
        m = farmland_mod.fixed_farmland_mask(_years_grid(per_year))
    except Exception:
        return
    np.testing.assert_allclose(np.asarray(m["farmland"], dtype=float), [[0.5]], atol=1e-9)


def _grid(farmland):
    return {"farmland": np.asarray(farmland, dtype=float), "lat_max": 19.5, "lon_min": 105.0, "cell": 0.05}


# 20 rows (19.5 -> 18.5 N), 25 columns (105.0 -> 106.25 E). Pixel (i, j) centre: lat 19.5 - (i + 0.5) * 0.05,
# lon 105.0 + (j + 0.5) * 0.05. POWER cells centred on multiples of 0.5 lat / 0.625 lon: cell 19.0 covers
# 18.75-19.25, cell 19.5 covers 19.25-19.75; lon cell 105.0 covers 104.6875-105.3125, cell 105.625 covers
# 105.3125-105.9375.


def test_cell_weights_single_cell():
    geom = box(105.4, 18.8, 105.6, 19.2)
    w = farmland_mod.province_cell_weights(geom, _grid(np.full((20, 25), 0.5)))
    assert _norm_keys(w) == pytest.approx({(19.0, 105.625): 1.0})


def test_cell_weights_follow_farmland_share():
    # box 105.2-105.4: columns j = 4, 5 (centres 105.225, 105.275 -> cell 105.0) and j = 6, 7 (105.325, 105.375 ->
    # cell 105.625). Farmland 0.3 in j = 4, 5 and 0.1 in j = 6, 7; same rows -> weights 0.6/0.8 = 0.75 and 0.25
    f = np.zeros((20, 25))
    f[:, 4:6] = 0.3
    f[:, 6:8] = 0.1
    w = _norm_keys(farmland_mod.province_cell_weights(box(105.2, 18.8, 105.4, 19.2), _grid(f)))
    assert set(w) == {(19.0, 105.0), (19.0, 105.625)}
    assert w[(19.0, 105.0)] == pytest.approx(0.75, abs=1e-9)
    assert w[(19.0, 105.625)] == pytest.approx(0.25, abs=1e-9)
    assert sum(w.values()) == pytest.approx(1.0)


def test_cell_weights_use_ground_area_cos_latitude():
    # D-36: "pixels are weighted by ground area (cos latitude ...)". box lat 19.15-19.35: row centres 19.175, 19.225
    # (cell 19.0) and 19.275, 19.325 (cell 19.5), 4 columns each, farmland 1 everywhere.
    w = _norm_keys(farmland_mod.province_cell_weights(box(105.4, 19.15, 105.6, 19.35), _grid(np.ones((20, 25)))))
    c = lambda d: math.cos(math.radians(d))  # noqa: E731
    s_low = c(19.175) + c(19.225)
    s_high = c(19.275) + c(19.325)
    assert w[(19.0, 105.625)] == pytest.approx(s_low / (s_low + s_high), abs=1e-7)
    assert w[(19.5, 105.625)] == pytest.approx(s_high / (s_low + s_high), abs=1e-7)


def test_cell_weights_pixel_belongs_by_centre():
    # D-36: "A MODIS pixel belongs to the province and POWER cell containing its centre". box 105.29-105.40 overlaps
    # pixel j = 5 (105.25-105.30, centre 105.275, cell 105.0) but does not contain its centre -> only cell 105.625
    w = _norm_keys(farmland_mod.province_cell_weights(box(105.29, 18.8, 105.40, 19.2), _grid(np.ones((20, 25)))))
    assert w == pytest.approx({(19.0, 105.625): 1.0})


def test_cell_weights_sum_to_one_for_any_shape():
    # 05 §3: "the weights of a unit sum to 1"
    rng = np.random.default_rng(0)
    f = rng.uniform(0, 1, size=(20, 25))
    geom = Polygon([(105.05, 18.55), (106.2, 18.6), (105.7, 19.45)])
    w = farmland_mod.province_cell_weights(geom, _grid(f))
    assert sum(float(v) for v in w.values()) == pytest.approx(1.0)
    assert all(float(v) >= 0 for v in w.values())


def test_cell_weights_no_farmland_raises():
    # D-36: "a province without farmland raises an error instead of being filled"
    with pytest.raises(ValueError, match=r"no farmland pixels"):
        farmland_mod.province_cell_weights(box(105.4, 18.8, 105.6, 19.2), _grid(np.zeros((20, 25))))


# ----------------------------------------------------------------------------------------------------------------
# 5. risk-level hazard rules (03-ML-SPEC §5a, 05 §4b, D-58, D-96, D-97, D-104, D-108; QĐ 18/2021 text)
# ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        # Art. 44.1 level 1: "lượng mưa từ 100 mm đến 200 mm trong 24 giờ"; "từ 100" includes 100; higher amounts
        # give higher levels and "level 1 or higher" counts (D-97)
        ([10, 99.9, 50], False),
        ([10, 100.0, 50], True),
        ([250.0], True),
        ([], False),
    ],
)
def test_heavy_rain_rule(values, expected):
    assert bool(hazards_mod.heavy_rain(pd.Series(values, dtype=float))) is expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        # Art. 47.1 a "từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên"; 35.0 included (D-96); consecutive (D-96);
        # hotter or longer spells are level 1-4 (D-104)
        ([35.0, 35.0, 35.0], True),
        ([30, 34.99, 35.0, 35.0, 35.0, 30], True),
        ([35.0, 35.0, 34.99, 35.0, 35.0], False),
        ([36, 36], False),
        ([34, 42, 42, 42, 34], True),
        ([36] * 30, True),
        ([34.99] * 10, False),
        # D-146: word for word, a spell counts only inside one band of Art. 47.1 (35-37; >37-39; >39-41; >41)
        ([36, 36, 38], False),
        ([37.0, 37.0, 37.0], True),
        ([36, 38, 38, 38], True),
    ],
)
def test_heat_rule(values, expected):
    assert bool(hazards_mod.heat(pd.Series(values, dtype=float))) is expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        # Art. 53.1 a: daily mean "từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày" -> >= 6 consecutive days <= 13.0
        ([13.0] * 6, True),
        ([13.0] * 5, False),
        ([13.0] * 5 + [13.1] + [13.0] * 5, False),
        ([20, 12, 12, 12, 12, 12, 12, 20], True),
        ([12.0] * 15, True),  # longer spells are level 2 (53.2 a "trên 10 ngày"), still met
        # D-120 (supersedes D-108): word for word; a spell with days in both bands is not counted
        ([13, 12, 7, 7, 12, 13], False),
        # Art. 53.1 d: "từ 8°c trở xuống, kéo dài từ 3 ngày đến 5 ngày" -> >= 3 consecutive days <= 8.0
        ([8.0, 8.0, 8.0], True),
        ([8.0, 8.0], False),
        ([8.1, 8.0, 8.0], False),
        ([9, 9, 7, 7, 9], False),  # 5 days <= 13 and only 2 days <= 8
        ([-1.0, 0.5, 3.0], True),
    ],
)
def test_cold_rule(values, expected):
    assert bool(hazards_mod.cold(pd.Series(values, dtype=float))) is expected


def test_monthly_climatology_mean_of_monthly_totals():
    # "the same month's 1991-2020 mean": mean over years of each month's total rain
    idx = pd.date_range("1991-01-01", "2020-12-31", freq="D")
    rain = pd.Series(0.0, index=idx)
    for y in range(1991, 2021):
        rain.loc[pd.Timestamp(y, 1, 1)] = float(y - 1990)  # Jan totals 1..30 -> mean 15.5
        rain.loc[pd.Timestamp(y, 7, 15)] = 10.0  # Jul totals 10 -> mean 10
    clim = hazards_mod.monthly_climatology(rain)
    assert clim[1] == pytest.approx(15.5)
    assert clim[7] == pytest.approx(10.0)
    assert clim[2] == pytest.approx(0.0)
    assert sorted(int(m) for m in clim.index) == list(range(1, 13))


def test_drought_months_strictly_more_than_half_below():
    # Art. 48.1: "thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm": deficit > 50%, i.e.
    # rain < 0.5 * mean. Exactly 50% below is not "trên 50%".
    rain = pd.Series([50.0, 49.9, 0.0, 100.0], index=[1, 2, 3, 4])
    clim = pd.Series([100.0] * 12, index=range(1, 13))
    out = hazards_mod.drought_months(rain, clim)
    assert [bool(v) for v in pd.Series(out).loc[[1, 2, 3, 4]]] == [False, True, True, False]


def test_drought_months_align_by_month():
    rain = pd.Series([10.0, 100.0], index=[3, 4])
    clim = pd.Series([1000.0] * 12, index=range(1, 13))
    clim[3] = 100.0
    clim[4] = 300.0
    out = pd.Series(hazards_mod.drought_months(rain, clim))
    assert bool(out.loc[3]) is True  # 10 < 50
    assert bool(out.loc[4]) is True  # 100 < 150


@pytest.mark.parametrize(
    ("flags", "consecutive", "any2"),
    [
        # D-58: "at least 2 consecutive months; any 2 months in the season"; longer runs are higher levels
        # (48.2-48.4 "trên 3 tháng", "trên 5 tháng"), still met (D-97)
        ([True, False, True], False, True),
        ([True, True], True, True),
        ([False, True, True, False], True, True),
        ([True], False, False),
        ([False, False, False], False, False),
        ([], False, False),
        ([True] * 6, True, True),
    ],
)
def test_drought_readings(flags, consecutive, any2):
    assert bool(hazards_mod.drought_consecutive(flags)) is consecutive
    assert bool(hazards_mod.drought_any2(flags)) is any2


def _daily(years=(2009, 2010)):
    idx = pd.date_range(f"{years[0]}-01-01", f"{years[-1]}-12-31", freq="D")
    return pd.DataFrame({"PRECTOTCORR": 2.0, "T2M_MAX": 30.0, "T2M": 20.0}, index=idx)


CLIM60 = pd.Series([60.0] * 12, index=range(1, 13))  # 2 mm/day gives 56-62 mm per month: never > 50% below 60
RULES = {"heavy_rain", "heat", "cold", "drought_rain_consecutive", "drought_rain_any2"}


def _rules(daily, field_dates, months, year=2010):
    out = hazards_mod.cell_rules(daily, year, field_dates=field_dates, months=months, clim=CLIM60)
    assert set(out) >= RULES
    return {k: bool(out[k]) for k in RULES}


def test_cell_rules_quiet_year_meets_nothing():
    r = _rules(_daily(), [("06-10", "08-30")], [6, 7, 8])
    assert r == dict.fromkeys(RULES, False)


def test_cell_rules_heavy_rain_only_inside_field_days_of_the_year():
    # D-97: "daily rules ... the exact days from the P-02 sowing date to the first reported harvest date"
    d = _daily()
    d.loc["2010-07-01", "PRECTOTCORR"] = 120.0
    assert _rules(d, [("06-10", "08-30")], [6, 7, 8])["heavy_rain"] is True
    d = _daily()
    d.loc["2010-09-05", "PRECTOTCORR"] = 120.0  # after the first harvest date
    assert _rules(d, [("06-10", "08-30")], [6, 7, 8])["heavy_rain"] is False
    d = _daily()
    d.loc["2009-07-01", "PRECTOTCORR"] = 120.0  # another year
    assert _rules(d, [("06-10", "08-30")], [6, 7, 8])["heavy_rain"] is False
    d = _daily()
    d.loc["2010-06-09", "PRECTOTCORR"] = 120.0  # the day before sowing
    d.loc["2010-08-31", "PRECTOTCORR"] = 120.0  # the day after the first harvest date
    assert _rules(d, [("06-10", "08-30")], [6, 7, 8])["heavy_rain"] is False


@pytest.mark.parametrize("day", ["2010-06-10", "2010-08-30"])
def test_cell_rules_field_days_include_sowing_and_first_harvest_date(day):
    # "from the P-02 sowing date to the first reported harvest date" read as both dates included
    d = _daily()
    d.loc[day, "PRECTOTCORR"] = 120.0
    assert _rules(d, [("06-10", "08-30")], [6, 7, 8])["heavy_rain"] is True


def test_cell_rules_heat_spell_must_be_consecutive_calendar_days():
    # spells ("đợt") are consecutive days (D-96). Year level: union of the field days of two crops (05 §4b). Hot days
    # 05-16, 05-17 (end of crop 1) and 06-10 (start of crop 2) are not 3 consecutive days.
    fd = [("01-17", "05-17"), ("06-10", "08-30")]
    d = _daily()
    d.loc[["2010-05-16", "2010-05-17", "2010-06-10"], "T2M_MAX"] = 36.0
    assert _rules(d, fd, [1, 2, 3, 4, 5, 6, 7, 8])["heat"] is False
    d = _daily()
    d.loc[["2010-05-15", "2010-05-16", "2010-05-17"], "T2M_MAX"] = 36.0
    assert _rules(d, fd, [1, 2, 3, 4, 5, 6, 7, 8])["heat"] is True


def test_cell_rules_heat_spell_cut_at_field_time():
    # only field days count: 05-16, 05-17 inside, 05-18 after the first harvest date 05-17 -> 2 field days only
    d = _daily()
    d.loc[["2010-05-16", "2010-05-17", "2010-05-18"], "T2M_MAX"] = 36.0
    assert _rules(d, [("01-17", "05-17")], [1, 2, 3, 4, 5])["heat"] is False


def test_cell_rules_cold_spell():
    d = _daily()
    d.loc["2010-01-20":"2010-01-25", "T2M"] = 12.0  # 6 days <= 13.0
    assert _rules(d, [("01-17", "05-17")], [1, 2, 3, 4, 5])["cold"] is True
    d = _daily()
    d.loc["2010-01-20":"2010-01-24", "T2M"] = 12.0  # 5 days
    assert _rules(d, [("01-17", "05-17")], [1, 2, 3, 4, 5])["cold"] is False


def test_cell_rules_drought_both_readings():
    # months 1-5, mean 60 each; Feb and Apr with no rain -> two drought months, not consecutive
    d = _daily()
    d.loc["2010-02-01":"2010-02-28", "PRECTOTCORR"] = 0.0
    d.loc["2010-04-01":"2010-04-30", "PRECTOTCORR"] = 0.0
    r = _rules(d, [("01-17", "05-17")], [1, 2, 3, 4, 5])
    assert r["drought_rain_consecutive"] is False
    assert r["drought_rain_any2"] is True
    d = _daily()
    d.loc["2010-02-01":"2010-03-31", "PRECTOTCORR"] = 0.0
    r = _rules(d, [("01-17", "05-17")], [1, 2, 3, 4, 5])
    assert r["drought_rain_consecutive"] is True
    assert r["drought_rain_any2"] is True


def test_cell_rules_drought_uses_whole_calendar_months():
    # 03-ML-SPEC §5a: "the calendar months from the sowing month to the harvest month, partial months included";
    # Art. 48 compares the month's total ("tổng lượng mưa tháng") with that month's mean. Sowing 01-17: January's
    # total includes the 100 mm of 5 January -> not a drought month; February dry -> one drought month only.
    d = _daily()
    d.loc["2010-01-01":"2010-01-31", "PRECTOTCORR"] = 0.0
    d.loc["2010-01-05", "PRECTOTCORR"] = 100.0
    d.loc["2010-02-01":"2010-02-28", "PRECTOTCORR"] = 0.0
    r = _rules(d, [("01-17", "03-31")], [1, 2, 3])
    assert r["drought_rain_consecutive"] is False
    assert r["drought_rain_any2"] is False


def test_cell_rules_drought_only_in_given_months():
    d = _daily()
    d.loc["2010-01-01":"2010-02-28", "PRECTOTCORR"] = 0.0
    r = _rules(d, [("06-10", "08-30")], [6, 7, 8])
    assert r["drought_rain_consecutive"] is False
    assert r["drought_rain_any2"] is False


def test_farmland_share_sums_weights_of_cells_meeting_rule():
    # 03-ML-SPEC §5a: "share of Nghệ An farmland where the rule was met = sum of the farmland weights ... of the
    # cells where it was met"
    w = {(19.0, 105.625): 0.5, (19.0, 105.0): 0.3, (18.5, 105.625): 0.2}
    met = {(19.0, 105.625): True, (19.0, 105.0): False, (18.5, 105.625): True}
    assert hazards_mod.farmland_share(met, w) == pytest.approx(0.7)
    assert hazards_mod.farmland_share(dict.fromkeys(w, False), w) == pytest.approx(0.0)
    assert hazards_mod.farmland_share(dict.fromkeys(w, True), w) == pytest.approx(1.0)


# ----------------------------------------------------------------------------------------------------------------
# 6. season climate features (03-ML-SPEC §4, 05 §4, §4a, D-39, D-72)
# ----------------------------------------------------------------------------------------------------------------

# Window 2010-01-10 .. 2010-01-31 (22 days, both ends included: "first day of the first sowing month to last day of
# the last harvest month", D-38). Rain inside the window, day by day:
RAIN_IN = [0.5, 0.9, 0.0, 1.0, 20.0, 19.9, 30.0, 5.0, 0, 0, 0, 0, 0, 0, 0.2, 2.0, 0, 0, 0, 0, 0, 0]


def _season_frame():
    idx = pd.date_range("2010-01-01", "2010-02-28", freq="D")
    d = pd.DataFrame(
        {
            "PRECTOTCORR": 0.0,
            "T2M_MAX": 45.0,
            "T2M_MIN": -5.0,
            "T2M": 20.0,
            "GWETROOT": 0.05,
            "ALLSKY_SFC_SW_DWN": 0.0,
        },
        index=idx,
    )
    win = pd.date_range("2010-01-10", "2010-01-31", freq="D")
    assert len(win) == 22
    d.loc["2010-01-08", "PRECTOTCORR"] = 100.0  # outside the window
    d.loc["2010-01-09", "PRECTOTCORR"] = 100.0  # outside the window
    d.loc[win, "PRECTOTCORR"] = RAIN_IN
    d.loc[win, "T2M_MAX"] = 30.0
    d.loc["2010-01-14", "T2M_MAX"] = 35.0
    d.loc["2010-01-15", "T2M_MAX"] = 35.1
    d.loc["2010-01-16", "T2M_MAX"] = 38.0
    d.loc[win, "T2M_MIN"] = 20.0
    d.loc["2010-01-20", "T2M_MIN"] = 10.0
    d.loc[win, "GWETROOT"] = 0.5
    d.loc["2010-01-25", "GWETROOT"] = 0.2
    d.loc["2010-01-26", "GWETROOT"] = 0.8
    d.loc["2010-01-31", "GWETROOT"] = 0.1
    d.loc[win, "ALLSKY_SFC_SW_DWN"] = 15.0
    d.loc["2010-01-10", "ALLSKY_SFC_SW_DWN"] = 21.0
    return d


@pytest.fixture(scope="module")
def season_feats():
    return climate_mod.season_features(_season_frame(), pd.Timestamp("2010-01-10"), pd.Timestamp("2010-01-31"))


def test_season_precip_sum(season_feats):
    # 05 §4 "POWER PRECTOTCORR summed": 0.5+0.9+1+20+19.9+30+5+0.2+2 = 79.5 (Jan 8-9 outside)
    assert season_feats["precip_sum_mm"] == pytest.approx(79.5)


def test_season_dry_spell(season_feats):
    # ETCCDI CDD: longest run of days < 1 mm. Runs: Jan 10-12 (3), Jan 18-24 (7, 0.2 < 1), Jan 26-31 (6; February
    # is outside the window). 1.0 mm on Jan 13 is a wet day.
    assert season_feats["dry_spell_max_d"] == 7


def test_season_heavy_rain_r20(season_feats):
    # ETCCDI R20mm: days >= 20 mm: 20.0 and 30.0 (19.9 not; Jan 8-9 outside)
    assert season_feats["heavy_rain_d"] == 2


def test_season_rx5day(season_feats):
    # ETCCDI Rx5day inside the window: Jan 13-17 = 1 + 20 + 19.9 + 30 + 5 = 75.9 (Jan 8-12 would be 201.4 if the
    # days before the window were used)
    assert season_feats["rx5day_mm"] == pytest.approx(75.9)


def test_season_temperature_features(season_feats):
    # tmax mean = (19 * 30 + 35 + 35.1 + 38) / 22 = 678.1 / 22
    assert season_feats["tmax_mean_c"] == pytest.approx(678.1 / 22)
    # tmin mean = (21 * 20 + 10) / 22 = 430 / 22
    assert season_feats["tmin_mean_c"] == pytest.approx(430 / 22)
    # TXx = 38.0 (45 outside the window)
    assert season_feats["txx_c"] == pytest.approx(38.0)
    # hot_days_d is counted per cell then weighted since the 2026-11-12 spec change (05 §4, §4a, D-72): tested
    # with official_counts below, not here


def test_season_soil_and_radiation(season_feats):
    # GWETROOT mean = (19 * 0.5 + 0.2 + 0.8 + 0.1) / 22 = 10.6 / 22; min = 0.1 (last window day included)
    assert season_feats["gwetroot_mean"] == pytest.approx(10.6 / 22)
    assert season_feats["gwetroot_min"] == pytest.approx(0.1)
    # ALLSKY_SFC_SW_DWN is returned by POWER in MJ/m^2/day (findings, POWER v2.10.3): mean = (21 * 15 + 21) / 22
    assert season_feats["srad_mean_mj_m2_d"] == pytest.approx(336 / 22)


def _cell(rain_days=None, temp_days=None, tmax_days=None):
    idx = pd.date_range("2010-01-01", "2010-02-28", freq="D")
    d = pd.DataFrame({"PRECTOTCORR": 0.0, "T2M": 20.0, "T2M_MAX": 30.0}, index=idx)
    for day, v in (rain_days or {}).items():
        d.loc[day, "PRECTOTCORR"] = v
    for day, v in (temp_days or {}).items():
        d.loc[day, "T2M"] = v
    for day, v in (tmax_days or {}).items():
        d.loc[day, "T2M_MAX"] = v
    return d


def test_official_counts_per_cell_then_weighted():
    # 05 §4a: heavy rain "rain > 50 mm in 24 h (Art. 5.17)"; ret_hai "strictly below 13 C"; ret_dam "strictly below
    # 15 C"; "counted per POWER cell and then weighted with the farmland weights (D-72; not on the weighted province
    # series)".
    a = _cell(
        rain_days={"2010-01-03": 60.0, "2010-01-04": 50.0, "2010-01-05": 51.0, "2010-02-02": 80.0},
        temp_days={
            "2010-01-10": 12.9,
            "2010-01-11": 12.9,
            "2010-01-12": 12.9,
            "2010-01-13": 13.0,
            "2010-01-14": 14.9,
            "2010-01-15": 15.0,
        },
    )
    b = _cell(
        temp_days={
            **{f"2010-01-{d:02d}": 10.0 for d in range(20, 30)},
            **{f"2010-02-{d:02d}": 5.0 for d in range(1, 11)},
        }
    )
    cells = {(19.0, 105.625): a, (19.0, 105.0): b}
    weights = {(19.0, 105.625): 0.75, (19.0, 105.0): 0.25}
    out = climate_mod.official_counts(cells, weights, pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-31"))
    # cell A: heavy 2 (60, 51; 50.0 not, Feb outside), ret_hai 3, ret_dam 5; cell B: heavy 0, ret_hai 10, ret_dam 10
    # weighted: heavy 0.75 * 2 = 1.5 (averaging rain first: (60 * 0.75) = 45 < 50 -> 0)
    assert out["official_heavy_rain_d"] == pytest.approx(1.5)
    assert out["ret_hai_d"] == pytest.approx(0.75 * 3 + 0.25 * 10)  # 4.75
    assert out["ret_dam_d"] == pytest.approx(0.75 * 5 + 0.25 * 10)  # 6.25


def test_official_counts_hot_days_per_cell_then_weighted():
    # 05 §4: hot_days_d "counted per cell, then weighted (§4a, D-72): Tmax strictly above 35 C (QĐ 18/2021 Art. 5.21
    # 'vượt quá 35°c', R-A01; 35.0 C is not counted), over the whole season window".
    # cell A (weight 0.75): 36.0 on Jan 3-6 (4 days), 35.0 on Jan 7 (not counted), 40.0 on Feb 3 (outside) -> 4
    # cell B (weight 0.25): never above 30 -> 0. Weighted: 0.75 * 4 = 3.0 (averaging Tmax first gives
    # 0.75 * 36 + 0.25 * 30 = 34.5 -> 0 days)
    a = _cell(
        tmax_days={
            "2010-01-03": 36.0,
            "2010-01-04": 36.0,
            "2010-01-05": 36.0,
            "2010-01-06": 36.0,
            "2010-01-07": 35.0,
            "2010-02-03": 40.0,
        }
    )
    b = _cell()
    cells = {(19.0, 105.625): a, (19.0, 105.0): b}
    weights = {(19.0, 105.625): 0.75, (19.0, 105.0): 0.25}
    out = climate_mod.official_counts(cells, weights, pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-31"))
    assert out["hot_days_d"] == pytest.approx(3.0)


# ----------------------------------------------------------------------------------------------------------------
# 7. evaluation harness (03-ML-SPEC §6, §7, D-69, D-83, D-107, D-109)
# ----------------------------------------------------------------------------------------------------------------


def test_test_years_2016_to_2024():
    # D-69: "Rolling-origin testing starts in 2016 ... 9 test years"; 03 §7 "rolling origin 2016-2024"
    assert list(eval_mod.TEST_YEARS) == list(range(2016, 2025))


@pytest.mark.parametrize(
    ("n", "k"),
    [
        # 03 §7: "the last 30% of its anomaly years (rounded to the nearest whole year, at least 1)"
        (18, 5),  # 5.4 -> 5 (first outer fold with the 3-year mean normal: 1998-2015)
        (16, 5),  # 4.8 -> 5
        (17, 5),  # 5.1 -> 5
        (19, 6),  # 5.7 -> 6
        (10, 3),
        (6, 2),  # 1.8 -> 2
        (4, 1),  # 1.2 -> 1
        (3, 1),  # 0.9 -> 1
        (2, 1),  # 0.6 -> 1
        (1, 1),  # 0.3 -> 0 -> at least 1
    ],
)
def test_inner_test_years_last_30_percent(n, k):
    years = list(range(2015 - n + 1, 2016))
    assert [int(y) for y in eval_mod.inner_test_years(years)] == years[-k:]


def test_inner_test_years_order_independent():
    years = list(range(1998, 2016))
    shuffled = list(np.random.default_rng(5).permutation(years))
    assert [int(y) for y in eval_mod.inner_test_years(shuffled)] == list(range(2011, 2016))


def test_inner_test_years_counts_years_not_rows():
    # "the last 30% of its anomaly years": with 2 rows per year the count is still 18 years -> 5 inner test years
    years = np.repeat(np.arange(1998, 2016), 2)
    assert [int(y) for y in eval_mod.inner_test_years(years)] == list(range(2011, 2016))


def _check_splits(splits, years, expected_test_years):
    years = np.asarray(years)
    n = len(years)
    got = {}
    for tr, te in splits:
        tr_p = _positions(tr, n)
        te_p = _positions(te, n)
        ys = set(years[te_p].tolist())
        assert len(ys) == 1
        got[ys.pop()] = (tr_p, te_p)
    assert sorted(got) == list(expected_test_years)
    for t, (tr_p, te_p) in got.items():
        # train on all years < t from the first available year; test = all rows of year t
        assert tr_p == sorted(np.flatnonzero(years < t).tolist())
        assert te_p == sorted(np.flatnonzero(years == t).tolist())


def test_rolling_origin_splits():
    # 03 §7: "for each test year t, train on years < t ..., predict year t for all provinces"
    years = np.repeat(np.arange(1998, 2025), 3)
    years = np.random.default_rng(2).permutation(years)
    _check_splits(list(eval_mod.rolling_origin_splits(years, eval_mod.TEST_YEARS)), years, range(2016, 2025))


def test_inner_splits():
    # D-107: inner test years "each predicted from all years before it, training always from the first available
    # year"; 18 years 1998-2015 -> inner test years 2011-2015
    years = np.repeat(np.arange(1998, 2016), 2)
    years = np.random.default_rng(4).permutation(years)
    _check_splits(list(eval_mod.inner_splits(years)), years, range(2011, 2016))


def _ref_frame():
    # series A 2010-2013 anomalies 0.1, 0.3, -0.1, 0.5; series B -0.2, 0.0, 0.2, 9.0; series C only 2013
    rows = []
    for sid, vals in {"A": [0.1, 0.3, -0.1, 0.5], "B": [-0.2, 0.0, 0.2, 9.0]}.items():
        for i, v in enumerate(vals):
            rows.append({"series_id": sid, "year": 2010 + i, "anom": v})
    rows.append({"series_id": "C", "year": 2013, "anom": 0.7})
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=7).reset_index(drop=True)
    return df


def test_predict_b0_training_mean_only():
    # B0 = "Mean anomaly of the training years, refit in each fold" (03 §6, D-83). The spec does not say whether the
    # mean is per series or pooled; both readings are accepted. Test-year anomalies (0.5, 9.0) must not enter.
    df = _ref_frame()
    train = np.flatnonzero((df["year"] < 2013).to_numpy())
    test = np.flatnonzero(((df["year"] == 2013) & df["series_id"].isin(["A", "B"])).to_numpy())
    pred = np.asarray(eval_mod.predict_b0(df, train, test), dtype=float)
    sids = df["series_id"].to_numpy()[test]
    per_series = np.array([{"A": 0.1, "B": 0.0}[s] for s in sids])  # A (0.1+0.3-0.1)/3; B (-0.2+0+0.2)/3
    pooled = np.full(len(test), 0.05)  # (0.3 + 0.0) / 6
    assert np.allclose(pred, per_series) or np.allclose(pred, pooled)


def test_predict_b2_previous_year_same_series():
    # B2 = "Previous-year anomaly" (persistence); a row without the previous year cannot be predicted (03 §6:
    # "including B2, which needs the previous year")
    df = _ref_frame()
    test = np.flatnonzero((df["year"] == 2013).to_numpy())
    pred = np.asarray(eval_mod.predict_b2(df, test), dtype=float)
    sids = df["series_id"].to_numpy()[test]
    for s, p in zip(sids, pred, strict=True):
        if s == "A":
            assert p == pytest.approx(-0.1)
        elif s == "B":
            assert p == pytest.approx(0.2)
        else:
            assert math.isnan(p)


def test_same_rows():
    # 03 §6: "a province-year enters the comparison only if every model and reference ... can predict it"
    preds = {
        "b0": pd.Series([0.1, np.nan, 0.3, 0.4]),
        "b2": pd.Series([0.1, 0.2, np.nan, 0.4]),
        "m1_ridge": pd.Series([0.0, 0.0, 0.0, 0.0]),
    }
    assert [bool(v) for v in eval_mod.same_rows(preds)] == [True, False, False, True]


Y = np.array([1.0, 2.0, 3.0, 4.0])
P = np.array([1.0, 2.0, 3.0, 5.0])
BASE = np.array([2.0, 2.0, 2.0, 2.0])


def test_rmse_mae():
    assert eval_mod.rmse(Y, P) == pytest.approx(0.5)  # sqrt(1/4)
    assert eval_mod.mae(Y, P) == pytest.approx(0.25)


def test_skill_scores():
    # 03 §7: "skill score ... (1 - MSE_model / MSE_reference; WMO/WWRP)": MSE_p 0.25, MSE_base (1+0+1+4)/4 = 1.5
    assert eval_mod.skill_score(Y, P, BASE) == pytest.approx(1 - 0.25 / 1.5)
    # sensitivity (b): "1 - MAE_model / MAE_reference": MAE_p 0.25, MAE_base (1+0+1+2)/4 = 1.0
    assert eval_mod.mae_skill(Y, P, BASE) == pytest.approx(0.75)


# Out-of-sample R2 is not tested: dropped from the spec by D-111 ("Our R2 formula therefore had no source; it is
# removed").


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        # D-109: alpha'/2 = Phi(-sqrt(n/(n-1)) t_{alpha/2,n-1}); level 0.9 -> alpha/2 = 0.05.
        # n = 9: t(0.95, 8) = 1.859548, x sqrt(9/8) = 1.972346, Phi(-1.972346) = 0.024285
        (9, 0.024285),
        # n = 30: t(0.95, 29) = 1.699127, x sqrt(30/29) = 1.728196, Phi(-1.728196) = 0.041979
        (30, 0.041979),
    ],
)
def test_expanded_alpha_half(n, expected):
    assert eval_mod.expanded_alpha_half(n, 0.9) == pytest.approx(expected, abs=2e-6)


def test_expanded_alpha_half_tends_to_plain_alpha():
    assert eval_mod.expanded_alpha_half(100000, 0.9) == pytest.approx(0.05, abs=1e-3)


def _two_year_frame():
    # year A: y 0, pred 0, base 1 (10 rows); year B: y 0, pred 1, base 2 (10 rows).
    # whole-year resamples: AA skill 1 - 0/20 = 1; AB 1 - 10/50 = 0.8; BB 1 - 20/80 = 0.75
    rows = [{"year": 2016, "y": 0.0, "pred": 0.0, "base": 1.0} for _ in range(10)]
    rows += [{"year": 2017, "y": 0.0, "pred": 1.0, "base": 2.0} for _ in range(10)]
    return pd.DataFrame(rows)


def test_year_bootstrap_resamples_whole_years():
    # 03 §7: "bootstrap over whole years (not rows)". With 2 years, BB has probability 1/4 and AA 1/4, so the
    # interval ends are 0.75 and 1.0 (n = 2 gives alpha'/2 near 0). Row resampling would almost never reach 0.75.
    lo, hi = eval_mod.year_bootstrap_ci(_two_year_frame(), stat="skill", n_boot=2000, seed=1, level=0.9)
    assert lo == pytest.approx(0.75, abs=1e-9)
    assert hi == pytest.approx(1.0, abs=1e-9)


def test_year_bootstrap_mae_skill():
    # MAE skill: AA 1 - 0/1 = 1; AB 1 - 0.5/1.5 = 0.6667; BB 1 - 1/2 = 0.5
    lo, hi = eval_mod.year_bootstrap_ci(_two_year_frame(), stat="mae_skill", n_boot=2000, seed=1, level=0.9)
    assert lo == pytest.approx(0.5, abs=1e-9)
    assert hi == pytest.approx(1.0, abs=1e-9)


def test_year_bootstrap_reproducible_with_seed():
    df = _two_year_frame()
    a = eval_mod.year_bootstrap_ci(df, stat="skill", n_boot=500, seed=11, level=0.9)
    b = eval_mod.year_bootstrap_ci(df, stat="skill", n_boot=500, seed=11, level=0.9)
    assert tuple(a) == tuple(b)


def test_year_bootstrap_uses_expanded_percentile():
    # 9 years, one row each: y 0, base 1, pred = sqrt(d) with d = 0..8, so skill = 1 - mean(resampled d).
    # Expected ends: quantiles at alpha'/2 = 0.024285 and 1 - alpha'/2 (Hesterberg 2015, D-109), here estimated by a
    # large independent reference resampling. The plain 5% / 95% quantiles differ from them by about 0.28.
    d = np.arange(9, dtype=float)
    df = pd.DataFrame({"year": np.arange(2016, 2025), "y": 0.0, "pred": np.sqrt(d), "base": 1.0})
    rng = np.random.default_rng(12345)
    ref = 1 - d[rng.integers(0, 9, size=(400000, 9))].mean(axis=1)
    a2 = 0.024285
    ref_lo, ref_hi = np.quantile(ref, [a2, 1 - a2])
    plain_lo, plain_hi = np.quantile(ref, [0.05, 0.95])
    assert ref_lo < plain_lo - 0.2
    assert ref_hi > plain_hi + 0.2
    lo, hi = eval_mod.year_bootstrap_ci(df, stat="skill", n_boot=10000, seed=3, level=0.9)
    assert lo == pytest.approx(ref_lo, abs=0.12)
    assert hi == pytest.approx(ref_hi, abs=0.12)


@pytest.mark.parametrize(
    ("alpha", "expected"),
    [
        # D-109: "the ceil((n+1)(1-alpha))-th smallest absolute inner-fold residual; infinite when that rank exceeds n"
        (0.2, 9.0),  # n = 10: ceil(11 * 0.8) = ceil(8.8) = 9
        (0.1, 10.0),  # ceil(9.9) = 10
        (0.05, math.inf),  # ceil(10.45) = 11 > 10
    ],
)
def test_conformal_halfwidth(alpha, expected):
    res = np.random.default_rng(0).permutation(np.arange(1.0, 11.0))
    assert eval_mod.conformal_halfwidth(res, alpha) == expected


def test_coverage():
    # share of held-out outcomes inside their interval (G4): 1 in [0,1.5], 2 not in [0,1.5], 3 in [0,5], 4 not in [0,3]
    y = np.array([1.0, 2.0, 3.0, 4.0])
    lo = np.zeros(4)
    hi = np.array([1.5, 1.5, 5.0, 3.0])
    assert eval_mod.coverage(y, lo, hi) == pytest.approx(0.5)
