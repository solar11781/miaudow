import pandas as pd

from fieldshift.data.series import assign_segments, drop_small_series, flag_fao_outliers, prepare_series


def _rows(province, areas, start=2005, crop="rice", season="spring"):
    return pd.DataFrame(
        {
            "province_nso": province,
            "crop": crop,
            "season": season,
            "year": list(range(start, start + len(areas))),
            "planted_area_ha": areas,
            "yield_t_ha": 5.0,
        }
    )


def test_ha_tay_dropped_and_ha_noi_split_at_2008():
    df = pd.concat(
        [
            _rows("Ha Tay", [160e3, 155e3, 150e3]),
            _rows("Ha Noi", [45e3, 44e3, 51e3, 207e3, 207e3]),
            _rows("Vinh Phuc", [69e3, 68e3, 58e3, 60e3]),
        ],
        ignore_index=True,
    )
    series, removed = prepare_series(df)
    assert "Ha Tay" not in set(series.province_nso)
    assert set(removed.province_nso) == {"Ha Tay", "Ha Noi"}
    assert series[series.province_nso == "Ha Noi"].year.min() == 2008
    assert series[series.province_nso == "Ha Noi"].segment.nunique() == 1  # the 2008 jump is removed, not a break
    vp = series[series.province_nso == "Vinh Phuc"]
    assert vp.loc[vp.year < 2008, "flag_2008_transfer"].all()
    assert not vp.loc[vp.year >= 2008, "flag_2008_transfer"].any()


def test_break_rule_threshold_is_strictly_above_half():
    # 100 -> 150 is exactly +50%: not a break. 150 -> 226 is +50.7%: break. 226 -> 100 is -55.8%: break.
    s = assign_segments(_rows("X", [100.0, 150.0, 226.0, 100.0]))
    assert list(s.segment) == [0, 0, 1, 2]
    assert list(s.break_here) == [False, False, True, True]


def test_missing_year_in_the_middle_starts_a_new_series():
    # Source: team decision D-31 (2026-11-11): any missing year inside a series splits it; no comparison across the gap.
    s = assign_segments(_rows("X", [100.0, None, 105.0, 104.0]))
    assert list(s.segment) == [0, 0, 1, 1]  # the missing-year row stays with the earlier segment
    assert list(s.break_here) == [False, False, True, False]


def test_missing_year_given_as_absent_row_also_splits():
    # Source: D-31. A year can be missing as NaN (above) or as no row at all.
    df = _rows("X", [100.0, 101.0, 102.0])
    df.loc[2, "year"] = 2009  # years 2005, 2006, 2009: 2007-2008 absent
    s = assign_segments(df)
    assert list(s.segment) == [0, 0, 1]


def test_leading_and_trailing_missing_years_do_not_split():
    # Source: D-31 talks about gaps in the middle; missing years before the first or after the last value are not gaps.
    s = assign_segments(_rows("X", [None, 100.0, 101.0, None]))
    assert s.segment.nunique() == 1


def test_small_series_dropped_by_median_area():
    # Source: team decision D-32 (2026-11-11): drop series whose median planted area is under 2,000 ha,
    # threshold chosen from measured yield noise (EXPERIMENTS E-000d).

    df = assign_segments(
        pd.concat(
            [
                _rows("Small", [1500.0, 1900.0, 2500.0]),  # median 1,900 -> dropped
                _rows("Big", [2000.0, 2100.0, 1900.0]),
            ],  # median 2,000 -> kept
            ignore_index=True,
        )
    )
    kept, removed = drop_small_series(df, min_median_area=2000.0)
    assert set(kept.province_nso) == {"Big"}
    assert set(removed.province_nso) == {"Small"}
    assert removed.removal_reason.str.contains("D-32").all()


def test_prepare_series_applies_small_series_rule():
    # Source: D-32 is part of the series preparation pipeline (with D-28 and D-31).
    df = pd.concat([_rows("Small", [300.0, 310.0, 320.0]), _rows("Big", [50e3, 51e3, 52e3])], ignore_index=True)
    series, removed = prepare_series(df)
    assert set(series.province_nso) == {"Big"}
    assert "Small" in set(removed.province_nso)


def test_area_from_zero_to_positive_is_a_break():
    # Source: team decision D-33 B (2026-11-11): 0 ha one year and some land the next starts a new series.
    s = assign_segments(_rows("X", [400.0, 0.0, 5000.0]))
    assert list(s.segment) == [0, 1, 2]  # 400 -> 0 is -100% (D-28 rule); 0 -> 5000 is a break (D-33 B)


def test_zero_to_zero_is_not_a_break():
    # Source: D-33 B concerns zero to some land; no change is not a jump.
    s = assign_segments(_rows("X", [0.0, 0.0]))
    assert s.segment.nunique() == 1


def _fao(yields, areas=None, province="X"):

    df = _rows(province, areas or [50e3] * len(yields), start=2005)
    df["yield_t_ha"] = yields
    df["series_id"] = f"{province}|rice|spring|0"
    return flag_fao_outliers(df)


def test_fao_flag_both_directions_strictly_beyond_30_percent():
    # Source: D-70 (FAO statistics code, R-S29): prev_avg = 3-year rolling mean lagged one year; flag when
    # yield < prev_avg - 0.3 prev_avg or > prev_avg + 0.3 prev_avg. Here prev_avg = 5.0, limits 3.5 and 6.5.
    out = _fao([5.0, 5.0, 5.0, 6.6])
    assert list(out.fao_flagged) == [False, False, False, True]
    assert list(_fao([5.0, 5.0, 5.0, 3.4]).fao_flagged)[-1] is True
    assert list(_fao([5.0, 5.0, 5.0, 6.5]).fao_flagged)[-1] is False  # exactly +30%: not beyond
    assert list(_fao([5.0, 5.0, 5.0, 3.5]).fao_flagged)[-1] is False  # exactly -30%: not beyond


def test_fao_flag_needs_three_previous_years_and_keeps_rows():
    # Source: D-70: "no check when fewer than 3 previous years exist"; flagged rows are kept and listed.
    out = _fao([5.0, 1.0, 9.0, 5.0])
    assert list(out.fao_flagged[:3]) == [False, False, False]
    assert len(out) == 4
    out = _fao([5.0, None, 5.0, 5.0, 1.0])  # a missing yield inside the window: no rolling mean, no check
    assert out.fao_flagged.iloc[3] is False or not out.fao_flagged.iloc[3]
    assert not out.fao_flagged.iloc[4]


def test_fao_flag_restarts_in_each_series_segment():
    # Source: D-70 applied per series (D-28: a new segment is a different series).

    df = _rows("X", [50e3] * 6, start=2000)
    df["yield_t_ha"] = [5.0, 5.0, 5.0, 2.0, 2.0, 2.0]
    df["series_id"] = ["X|rice|spring|0"] * 3 + ["X|rice|spring|1"] * 3
    assert not flag_fao_outliers(df).fao_flagged.any()


def test_prepare_series_has_fao_flag_and_no_one_tonne_flag():
    # Source: D-56 d: the FAO flag supersedes the 1 t/ha flag of D-33 D.
    series, _ = prepare_series(_rows("Nghe An", [40e3] * 5))
    assert "fao_flagged" in series.columns
    assert "extreme_low_yield" not in series.columns


def test_2004_province_splits_start_new_series():
    # Source: D-56 d (Nghi quyet 22/2003/QH11, in force 1/1/2004): Can Tho, Dak Lak, Lai Chau split and Than Uyen moved
    # from Lao Cai, so these units start new series in 2004 as named rules. [DATA] NSO spring rice area, thousand ha
    # converted to ha: Can Tho 2003 177,600 -> 2004 93,900 (-47%) and Lai Chau 8,600 -> 4,400 (-49%) are below the 50%
    # jump rule, so only the named rule catches them.
    df = pd.concat(
        [
            _rows("Can Tho", [181900.0, 180900.0, 177600.0, 93900.0, 93400.0], start=2001),
            _rows("Lai Chau", [7400.0, 8000.0, 8600.0, 4400.0, 4700.0], start=2001),
            _rows("Dak Lak", [21600.0, 23600.0, 24900.0, 22700.0, 17000.0], start=2001),
            _rows("Lao Cai", [9300.0, 9700.0, 10000.0, 8200.0, 8400.0], start=2001),
            _rows("Nghe An", [90e3] * 5, start=2001),
        ],
        ignore_index=True,
    )
    s = assign_segments(df)
    for prov in ["Can Tho", "Lai Chau", "Dak Lak", "Lao Cai"]:
        g = s[s.province_nso == prov].sort_values("year")
        assert g.loc[g.year < 2004, "segment"].nunique() == 1
        assert g.loc[g.year >= 2004, "segment"].nunique() == 1
        assert g.loc[g.year == 2004, "break_here"].item() is True or g.loc[g.year == 2004, "break_here"].item()
        assert g.loc[g.year < 2004, "segment"].iloc[0] != g.loc[g.year >= 2004, "segment"].iloc[0]
    assert s[s.province_nso == "Nghe An"].segment.nunique() == 1


def test_2004_named_break_applies_to_every_crop_and_season():
    # Source: D-56 d names the unit change, not a crop: the territory changed for every series of the unit.
    df = pd.concat(
        [
            _rows("Can Tho", [1000.0, 1000.0], start=2003, crop="maize", season="annual"),
            _rows("Can Tho", [5000.0, 5000.0], start=2003, season="winter"),
        ],
        ignore_index=True,
    )
    s = assign_segments(df)
    for _, g in s.groupby(["crop", "season"]):
        assert g.segment.nunique() == 2


def test_area_jump_rule_still_applies_to_the_2004_units_in_other_years():
    # Source: D-113: "the > 50% area rule applies to every unit, the four 2004 units included in other years" (D-28);
    # 90,000 -> 40,000 ha from 2009 to 2010 is -55.6%, a break in 2010; the 2004 named break is outside these years
    s = assign_segments(_rows("Can Tho", [93400.0, 93000.0, 92000.0, 91000.0, 90000.0, 40000.0, 41000.0], start=2005))
    assert list(s.segment) == [0, 0, 0, 0, 0, 1, 1]
    assert list(s.break_here) == [False, False, False, False, False, True, False]


def test_quang_tri_winter_rice_series_is_dropped():
    # Source: team decision D-34 (2026-11-11): Quang Tri winter rice is about a quarter of normal rice yields in every
    # year, unexplained (EXPERIMENTS E-000e), so the whole series is dropped with a recorded reason.
    df = pd.concat(
        [
            _rows("Quang Tri", [6000.0, 6000.0], season="winter"),
            _rows("Quang Tri", [50e3, 50e3], season="spring"),
            _rows("Nghe An", [40e3, 40e3], season="winter"),
        ],
        ignore_index=True,
    )
    series, removed = prepare_series(df)
    assert not ((series.province_nso == "Quang Tri") & (series.season == "winter")).any()
    assert ((series.province_nso == "Quang Tri") & (series.season == "spring")).sum() == 2
    assert ((series.province_nso == "Nghe An") & (series.season == "winter")).sum() == 2
    qt = removed[(removed.province_nso == "Quang Tri") & (removed.season == "winter")]
    assert len(qt) == 2
    assert qt.removal_reason.str.contains("D-34").all()
