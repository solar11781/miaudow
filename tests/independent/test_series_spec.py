"""Independent specification tests for fieldshift.data.series (consistent series, DECISION-LOG D-28).

Written without reading the implementation (D-30). Every expectation cites its source.
D-28: (1) drop Ha Tay; (2) drop Ha Noi 1995-2007, keep 2008+ as a fresh series; (3) keep Vinh Phuc and Hoa Binh,
flagged (flag_2008_transfer); (4) a one-year planted-area change with |new - old| / old > 0.5 starts a new segment.
Not tested on purpose: behaviour across missing years inside a series (undecided when these tests were commissioned),
and the D-32 small-series filter (not part of the commissioned interface). All synthetic series therefore have
consecutive years and large areas (>= 40,000 ha median).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fieldshift.data.nso import build_crop_stats
from fieldshift.data.series import apply_known_boundary_rules, assign_segments, prepare_series

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "nso"
ALL_TABLES = [f"E06.{n}" for n in range(13, 28)] + ["E06.34", "E06.35"]
HAVE_RAW = all((RAW / f"{t}.csv").exists() for t in ALL_TABLES)
needs_raw = pytest.mark.skipif(not HAVE_RAW, reason="NSO raw exports not present (gitignored)")

KEY = ["province_nso", "crop", "season", "year"]


def _series(province: str, areas: dict[int, float], crop: str = "rice", season: str = "spring") -> list[dict]:
    """Rows following the crop_stats contract (05-DATA-CONTRACTS §2)."""
    rows = []
    for year, area in sorted(areas.items()):
        rows.append(
            {
                "province_nso": province,
                "year": year,
                "crop": crop,
                "season": season,
                "is_preliminary": False,
                "planted_area_ha": float(area),
                "yield_t_ha": 5.0,
                "production_t": float(area) * 5.0,
                "yield_derived": False,
                "source_table": "E06.16",
                "retrieved_on": "2026-11-10",
            }
        )
    return rows


def _df(*row_lists: list[dict]) -> pd.DataFrame:
    rows = [r for rl in row_lists for r in rl]
    df = pd.DataFrame(rows)
    df["year"] = df["year"].astype(int)
    return df


def _steady(start: int, end: int, area: float = 100_000.0) -> dict[int, float]:
    return {y: area * (1 + 0.01 * ((y - start) % 3)) for y in range(start, end + 1)}


def _by_key(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index(KEY).sort_index()


# ---------------------------------------------------------------- apply_known_boundary_rules


@pytest.fixture
def boundary_input() -> pd.DataFrame:
    return _df(
        _series("Ha Tay", _steady(1995, 2007, 77_000)),
        _series("Ha Noi", {**_steady(1995, 2007, 20_600), **_steady(2008, 2012, 101_200)}),
        _series("Vinh Phuc", _steady(1995, 2012, 60_000)),
        _series("Hoa Binh", _steady(1995, 2012, 40_000)),
        _series("Nghe An", _steady(1995, 2012, 91_000)),
        _series("Ha Tinh", _steady(1995, 2012, 59_000), season="winter"),
    )


def test_boundary_rows_are_partitioned(boundary_input):
    # Source: interface spec (kept, removed): every input row ends in exactly one of the two outputs
    kept, removed = apply_known_boundary_rules(boundary_input)
    assert len(kept) + len(removed) == len(boundary_input)
    k = set(map(tuple, kept[KEY].to_numpy()))
    r = set(map(tuple, removed[KEY].to_numpy()))
    assert not k & r
    assert k | r == set(map(tuple, boundary_input[KEY].to_numpy()))


def test_boundary_drops_ha_tay(boundary_input):
    # Source: D-28 rule 1: drop Ha Tay
    kept, removed = apply_known_boundary_rules(boundary_input)
    assert "Ha Tay" not in set(kept["province_nso"])
    assert (removed["province_nso"] == "Ha Tay").sum() == 13


def test_boundary_drops_ha_noi_before_2008_only(boundary_input):
    # Source: D-28 rule 2: drop Ha Noi 1995-2007, keep 2008+
    kept, removed = apply_known_boundary_rules(boundary_input)
    hn_kept = kept[kept["province_nso"] == "Ha Noi"]
    hn_removed = removed[removed["province_nso"] == "Ha Noi"]
    assert set(hn_kept["year"].astype(int)) == set(range(2008, 2013))
    assert set(hn_removed["year"].astype(int)) == set(range(1995, 2008))


def test_boundary_removal_reason_present(boundary_input):
    # Source: interface spec: removed has column removal_reason (one reason per removed row)
    _, removed = apply_known_boundary_rules(boundary_input)
    assert "removal_reason" in removed.columns
    assert removed["removal_reason"].notna().all()
    assert (removed["removal_reason"].astype(str).str.len() > 0).all()


def test_boundary_removal_reasons_distinguish_the_two_rules(boundary_input):
    # Source: D-28 rules 1 and 2 are different reasons (Ha Tay dropped entirely vs Ha Noi pre-2008)
    _, removed = apply_known_boundary_rules(boundary_input)
    ht = set(removed.loc[removed["province_nso"] == "Ha Tay", "removal_reason"])
    hn = set(removed.loc[removed["province_nso"] == "Ha Noi", "removal_reason"])
    assert ht
    assert hn
    assert not ht & hn


def test_boundary_flags_vinh_phuc_and_hoa_binh(boundary_input):
    # Source: D-28 rule 3: keep Vinh Phuc and Hoa Binh, flagged (flag_2008_transfer)
    kept, _ = apply_known_boundary_rules(boundary_input)
    assert pd.api.types.is_bool_dtype(kept["flag_2008_transfer"])
    vp_hb = kept["province_nso"].isin(["Vinh Phuc", "Hoa Binh"])
    assert vp_hb.sum() == 36
    # Corrected 2026-11-11: team decision D-33 A flags only years before 2008
    assert kept.loc[vp_hb & (kept["year"] < 2008), "flag_2008_transfer"].all()
    assert not kept.loc[vp_hb & (kept["year"] >= 2008), "flag_2008_transfer"].any()


def test_boundary_does_not_flag_unaffected_provinces(boundary_input):
    # Source: D-28: only Vinh Phuc and Hoa Binh gave land to Ha Noi in 2008 (admin_units.csv Ha Tay note)
    kept, _ = apply_known_boundary_rules(boundary_input)
    other = kept["province_nso"].isin(["Nghe An", "Ha Tinh"])
    assert not kept.loc[other, "flag_2008_transfer"].any()


def test_boundary_keeps_other_rows_unchanged(boundary_input):
    # Source: D-28: the rules touch only Ha Tay, Ha Noi, Vinh Phuc, Hoa Binh
    kept, _ = apply_known_boundary_rules(boundary_input)
    cols = ["planted_area_ha", "yield_t_ha", "production_t"]
    a = _by_key(kept[kept["province_nso"].isin(["Nghe An", "Ha Tinh", "Vinh Phuc"])])[cols]
    b = _by_key(boundary_input[boundary_input["province_nso"].isin(["Nghe An", "Ha Tinh", "Vinh Phuc"])])[cols]
    pd.testing.assert_frame_equal(a, b)


# ---------------------------------------------------------------- assign_segments


def _seg(df: pd.DataFrame, **kw) -> pd.DataFrame:
    out = assign_segments(df, **kw)
    assert {"segment", "break_here", "series_id"} <= set(out.columns)
    return _by_key(out)


def _breaks(out: pd.DataFrame, province: str, crop: str = "rice", season: str = "spring") -> list[int]:
    s = out.loc[(province, crop, season)]
    return sorted(int(y) for y in s.index[s["break_here"].astype(bool)])


def test_segments_output_columns_and_types():
    # Source: interface spec: segment (int), break_here (bool), series_id (str); one output row per input row
    df = _df(_series("Nghe An", _steady(2000, 2010)))
    out = assign_segments(df)
    assert len(out) == len(df)
    assert pd.api.types.is_integer_dtype(out["segment"])
    assert pd.api.types.is_bool_dtype(out["break_here"])
    assert out["series_id"].map(lambda v: isinstance(v, str)).all()


def test_steady_series_has_one_segment():
    # Source: D-28 rule 4: no one-year change above 50% -> no break
    out = _seg(_df(_series("Nghe An", _steady(1995, 2024))))
    s = out.loc[("Nghe An", "rice", "spring")]
    assert not s["break_here"].any()
    assert s["segment"].nunique() == 1
    assert s["series_id"].nunique() == 1


def test_large_increase_starts_new_segment():
    # Source: D-28 rule 4: |160,000 - 100,000| / 100,000 = 0.6 > 0.5 -> new segment at the new year (2003)
    areas = {2000: 100_000, 2001: 101_000, 2002: 100_000, 2003: 160_000, 2004: 161_000, 2005: 159_000}
    out = _seg(_df(_series("Nghe An", areas)))
    s = out.loc[("Nghe An", "rice", "spring")]
    assert _breaks(out, "Nghe An") == [2003]
    assert s.loc[[2000, 2001, 2002], "segment"].nunique() == 1
    assert s.loc[[2003, 2004, 2005], "segment"].nunique() == 1
    assert s.loc[2002, "segment"] != s.loc[2003, "segment"]
    assert s.loc[2002, "series_id"] != s.loc[2003, "series_id"]


def test_large_decrease_starts_new_segment():
    # Source: D-28 rule 4: |40,000 - 100,000| / 100,000 = 0.6 > 0.5
    areas = {2000: 100_000, 2001: 100_000, 2002: 40_000, 2003: 41_000}
    out = _seg(_df(_series("Nghe An", areas)))
    assert _breaks(out, "Nghe An") == [2002]


@pytest.mark.parametrize("new_area", [150_000, 50_000])
def test_change_of_exactly_half_is_not_a_break(new_area):
    # Source: D-28 rule 4 uses a strict "above 50%" (> 0.5); 0.5 exactly does not break
    areas = {2000: 100_000, 2001: 100_000, 2002: new_area, 2003: new_area}
    out = _seg(_df(_series("Nghe An", areas)))
    assert _breaks(out, "Nghe An") == []


@pytest.mark.parametrize("new_area", [150_001, 49_999])
def test_change_just_above_half_is_a_break(new_area):
    # Source: D-28 rule 4: anything above 0.5 breaks
    areas = {2000: 100_000, 2001: 100_000, 2002: new_area, 2003: new_area}
    out = _seg(_df(_series("Nghe An", areas)))
    assert _breaks(out, "Nghe An") == [2002]


def test_relative_change_uses_old_value_as_denominator_decrease():
    # Source: D-28 formula |new - old| / old: 100,000 -> 60,000 is 0.4 (no break); with /new it would be 0.67
    areas = {2000: 100_000, 2001: 100_000, 2002: 60_000, 2003: 60_000}
    out = _seg(_df(_series("Nghe An", areas)))
    assert _breaks(out, "Nghe An") == []


def test_relative_change_uses_old_value_as_denominator_increase():
    # Source: D-28 formula |new - old| / old: 60,000 -> 100,000 is 0.67 (break); with /new it would be 0.4
    areas = {2000: 60_000, 2001: 60_000, 2002: 100_000, 2003: 100_000}
    out = _seg(_df(_series("Nghe An", areas)))
    assert _breaks(out, "Nghe An") == [2002]


def test_threshold_parameter_is_used():
    # Source: interface spec assign_segments(df, threshold=0.5): 100,000 -> 125,000 is 0.25
    areas = {2000: 100_000, 2001: 100_000, 2002: 125_000, 2003: 125_000}
    df = _df(_series("Nghe An", areas))
    assert _breaks(_seg(df), "Nghe An") == []
    assert _breaks(_seg(df, threshold=0.2), "Nghe An") == [2002]


def test_multiple_breaks_give_multiple_segments():
    # Source: D-28 rule 4 applied at every year: two big changes -> three segments
    areas = {2000: 100_000, 2001: 100_000, 2002: 200_000, 2003: 200_000, 2004: 50_000, 2005: 52_000}
    out = _seg(_df(_series("Nghe An", areas)))
    s = out.loc[("Nghe An", "rice", "spring")]
    assert _breaks(out, "Nghe An") == [2002, 2004]
    assert s["segment"].nunique() == 3
    assert s["series_id"].nunique() == 3
    # segment changes exactly where break_here is True
    changed = s["segment"].ne(s["segment"].shift()).iloc[1:]
    assert list(changed) == list(s["break_here"].iloc[1:])


def test_first_year_is_never_a_break():
    # Source: D-28 rule 4 compares with the previous year; the first year has none
    areas = {2000: 1_000_000, 2001: 1_010_000, 2002: 1_000_000}
    out = _seg(_df(_series("Nghe An", areas)))
    assert not out.loc[("Nghe An", "rice", "spring", 2000), "break_here"]


def test_series_are_independent_across_provinces():
    # Source: D-28 rule 4 is "for every province-crop-season series": one series' jump never affects another
    a = _series("Can Tho", {2002: 275_700, 2003: 275_800, 2004: 136_000, 2005: 138_600}, season="autumn")
    b = _series("Nghe An", {2002: 50_000, 2003: 50_500, 2004: 51_000, 2005: 50_800}, season="autumn")
    out = _seg(_df(a, b))
    assert _breaks(out, "Can Tho", season="autumn") == [2004]
    assert _breaks(out, "Nghe An", season="autumn") == []
    assert not set(out.loc[("Can Tho", "rice", "autumn"), "series_id"]) & set(
        out.loc[("Nghe An", "rice", "autumn"), "series_id"]
    )


def test_series_are_independent_across_seasons_and_crops():
    # Source: D-28 rule 4: series are per province AND crop AND season (spring vs winter vs maize compared separately)
    spring = _series("Nghe An", {2000: 90_000, 2001: 91_000, 2002: 90_500})
    winter = _series("Nghe An", {2000: 20_000, 2001: 20_300, 2002: 20_100}, season="winter")
    maize = _series("Nghe An", {2000: 45_000, 2001: 46_000, 2002: 45_500}, crop="maize", season="annual")
    out = _seg(_df(spring, winter, maize))
    assert not out["break_here"].any()
    assert out["series_id"].nunique() == 3


def test_input_row_order_does_not_matter():
    # Source: D-28 rule 4 is about consecutive years, not about row order in the table
    areas = {2000: 100_000, 2001: 101_000, 2002: 170_000, 2003: 171_000, 2004: 169_000}
    df = _df(_series("Nghe An", areas), _series("Ha Tinh", _steady(2000, 2004, 59_000)))
    shuffled = df.sample(frac=1.0, random_state=7).reset_index(drop=True)
    a = _seg(df)[["break_here"]]
    b = _seg(shuffled)[["break_here"]]
    pd.testing.assert_frame_equal(a, b)
    assert _breaks(_seg(shuffled), "Nghe An") == [2002]


def test_real_value_examples_from_e000c():
    # Source: real data (E06.19 Can Tho autumn 275.8 -> 136.0 thousand ha 2003->2004; E06.22 Tra Vinh winter
    # 89.2 -> 2.6 thousand ha 2014->2015) and E-000c, which lists both as breaks
    can_tho = _series("Can Tho", {2002: 275_700, 2003: 275_800, 2004: 136_000, 2005: 138_600}, season="autumn")
    tra_vinh = _series("Tra Vinh", {2013: 90_400, 2014: 89_200, 2015: 2_600, 2016: 2_400}, season="winter")
    out = _seg(_df(can_tho, tra_vinh))
    assert _breaks(out, "Can Tho", season="autumn") == [2004]
    assert _breaks(out, "Tra Vinh", season="winter") == [2015]


# ---------------------------------------------------------------- prepare_series


@pytest.fixture
def prepare_input() -> pd.DataFrame:
    return _df(
        _series("Ha Tay", _steady(1995, 2007, 77_200)),
        # real data E06.16 Ha Noi spring rice: 20.6 thousand ha (2007) -> 101.2 (2008), then 103.2, 101.8, 102.0
        _series("Ha Noi", {**_steady(1995, 2007, 20_600), 2008: 101_200, 2009: 103_200, 2010: 101_800, 2011: 102_000}),
        _series("Vinh Phuc", _steady(1995, 2011, 60_000)),
        _series("Nghe An", {**_steady(1995, 2003, 100_000), **_steady(2004, 2011, 170_000)}),
    )


def test_prepare_series_returns_series_and_removed(prepare_input):
    # Source: interface spec prepare_series(df, threshold) -> (series, removed); D-28 rules 1-4 combined
    series, removed = prepare_series(prepare_input)
    assert {"segment", "break_here", "series_id", "flag_2008_transfer"} <= set(series.columns)
    assert "removal_reason" in removed.columns


def test_prepare_series_applies_boundary_rules(prepare_input):
    # Source: D-28 rules 1-3
    series, removed = prepare_series(prepare_input)
    assert "Ha Tay" not in set(series["province_nso"])
    assert set(series.loc[series["province_nso"] == "Ha Noi", "year"].astype(int)) == set(range(2008, 2012))
    assert {"Ha Tay", "Ha Noi"} <= set(removed["province_nso"])
    vp = series["province_nso"] == "Vinh Phuc"  # corrected 2026-11-11: D-33 A flags only years before 2008
    assert series.loc[vp & (series["year"] < 2008), "flag_2008_transfer"].all()
    assert not series.loc[vp & (series["year"] >= 2008), "flag_2008_transfer"].any()


def test_prepare_series_ha_noi_2008_is_a_fresh_series_not_a_break(prepare_input):
    # Source: D-28 rule 2 ("keep 2008+ as a fresh series"): with 1995-2007 removed, 2008 has no previous year,
    # so the 2007 -> 2008 border jump (20,600 -> 101,200 ha, real data E06.16) is never measured as a break
    series, _ = prepare_series(prepare_input)
    hn = _by_key(series).loc[("Ha Noi", "rice", "spring")]
    assert not hn["break_here"].any()
    assert hn["series_id"].nunique() == 1


def test_prepare_series_applies_break_rule(prepare_input):
    # Source: D-28 rule 4: Nghe An fixture 2003 -> 2004 goes about 102,000 -> 170,000 ha (> 50%)
    series, _ = prepare_series(prepare_input)
    out = _by_key(series)
    assert _breaks(out, "Nghe An") == [2004]


def test_prepare_series_threshold_is_passed_through(prepare_input):
    # Source: interface spec prepare_series(df, threshold=0.5); a threshold above the 2004 jump (about 0.67)
    series, _ = prepare_series(prepare_input, threshold=0.9)
    assert _breaks(_by_key(series), "Nghe An") == []


# ---------------------------------------------------------------- real data


@pytest.fixture(scope="module")
def real_kept() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not HAVE_RAW:
        pytest.skip("NSO raw exports not present")

    stats = build_crop_stats(RAW, retrieved_on="2026-11-10")
    kept, removed = apply_known_boundary_rules(stats)
    kept = kept[kept["planted_area_ha"].notna()].copy()
    return kept, removed


@needs_raw
def test_real_removed_only_ha_tay_and_old_ha_noi(real_kept):
    # Source: D-28 rules 1-2 on real data; updated 2026-11-11 for D-34 (Quang Tri winter rice dropped entirely)
    _, removed = real_kept
    assert set(removed["province_nso"]) == {"Ha Tay", "Ha Noi", "Quang Tri"}
    assert removed.loc[removed["province_nso"] == "Ha Noi", "year"].astype(int).max() == 2007
    qt = removed[removed["province_nso"] == "Quang Tri"]
    assert set(zip(qt["crop"], qt["season"], strict=True)) == {("rice", "winter")}


@needs_raw
def test_real_removed_rows_with_data(real_kept):
    # Source: own count from raw CSVs: Ha Tay has area values 1995-2007 in E06.13, E06.16, E06.22, E06.25
    # (absent from E06.19 and E06.34) = 52; Ha Noi 1995-2007 the same four tables = 52 (E-000c: 104)
    _, removed = real_kept
    with_area = removed[removed["planted_area_ha"].notna()]
    assert (with_area["province_nso"] == "Ha Tay").sum() == 52
    assert (with_area["province_nso"] == "Ha Noi").sum() == 52


@needs_raw
def test_real_nghe_an_has_no_breaks(real_kept):
    # Source: own computation from raw CSVs: largest one-year area change in any Nghe An series is 33.7%
    # (maize, E06.25), below 50%; E-000c also reports no Nghe An breaks
    kept, _ = real_kept
    out = assign_segments(kept[kept["province_nso"] == "Nghe An"])
    assert not out["break_here"].any()


@needs_raw
@pytest.mark.parametrize(
    ("province", "crop", "season", "year"),
    [
        ("Can Tho", "rice", "autumn", 2004),  # E06.19: 275.8 -> 136.0 thousand ha
        ("Tra Vinh", "rice", "winter", 2015),  # E06.22: 89.2 -> 2.6 thousand ha
        ("Tra Vinh", "rice", "autumn", 2015),  # E06.19: 80.2 -> 164.3 thousand ha
    ],
)
def test_real_known_breaks(real_kept, province, crop, season, year):
    # Source: real data values listed per case (read from data/raw/nso) + E-000c examples
    kept, _ = real_kept
    sub = kept[(kept["province_nso"] == province) & (kept["crop"] == crop) & (kept["season"] == season)]
    out = _by_key(assign_segments(sub))
    assert bool(out.loc[(province, crop, season, year), "break_here"])


@needs_raw
def test_real_tra_vinh_winter_1996_drop_is_not_a_break(real_kept):
    # Source: real data E06.22 Tra Vinh winter 84.3 -> 53.8 thousand ha (1995 -> 1996) = 36% change, below 50%
    kept, _ = real_kept
    sub = kept[(kept["province_nso"] == "Tra Vinh") & (kept["crop"] == "rice") & (kept["season"] == "winter")]
    out = _by_key(assign_segments(sub))
    assert not bool(out.loc[("Tra Vinh", "rice", "winter", 1996), "break_here"])
