"""Split crop statistics into consistent series before any trend is fitted (DECISION-LOG D-28).

Plain words: the ML target compares each year with the province's own "normal" yield, computed from earlier years.
That only works if every year in a series describes the same piece of land. When a province's borders change (Hà Tây
merged into Hà Nội in 2008) or its crop area suddenly jumps, the years before and after are different series.

Rules (team decision D-28, 2026-11-11):
1. Drop Hà Tây entirely: no boundary exists on today's map, so no weather region can be assigned.
2. Drop Hà Nội before 2008: NSO did not re-state old Hà Nội to today's borders (rice area 51.3 -> 206.9 thousand ha
   in 2008), and the old city has no boundary on today's map. Hà Nội 2008 onward is a fresh series.
3. Keep Vĩnh Phúc and Hòa Bình (small 2008 transfers), flagged for a sensitivity check.
4. Automatic break rule for every series: a one-year planted-area change above 50% (|new - old| / old > 0.5) starts a
   new series segment.
5. (D-31) A missing year in the middle of a series (no planted-area value, or no row) starts a new segment at the next
   year with a value. Missing years before the first or after the last value are not gaps.
9. (D-34) Drop Quảng Trị winter rice entirely (unexplained, consistently about a quarter of normal yields).
7. (D-33 B) A change from 0 ha to more than 0 ha is a break.
8. (D-56 d, D-70) FAO outlier flag `fao_flagged`: yield outside +-30% of the previous 3-year mean within the series,
   both directions; no check with fewer than 3 previous years. Flagged rows are kept, never dropped.
10. (D-56 d) Named 2004 breaks (Nghị quyết 22/2003/QH11, in force 1/1/2004): Cần Thơ, Đắk Lắk and Lai Châu were split
   and Than Uyên moved from Lào Cai, so every series of these units starts a new segment in 2004.
6. (D-32) Drop series (after splitting) whose median planted area is under 2,000 ha: their yields are much noisier
   (typical year-to-year jump 11-16% vs 6-7.5% for larger series, EXPERIMENTS E-000d).
"""

from __future__ import annotations

import pandas as pd

BREAK_THRESHOLD = 0.5
MIN_MEDIAN_AREA_HA = 2000.0
DROP_PROVINCES = {"Ha Tay"}
MERGE_YEAR = 2008  # Hà Nội border change: Hà Tây merged in (D-28)
DROP_BEFORE = {"Ha Noi": MERGE_YEAR}
FLAG_2008_TRANSFER = {"Vinh Phuc", "Hoa Binh"}
# D-34: whole series dropped because their values are unexplained (EXPERIMENTS E-000e).
DROP_SERIES = {
    ("Quang Tri", "rice", "winter"): "yields about a quarter of normal rice in every year, unexplained (D-34)"
}
SERIES_KEY = ["province_nso", "crop", "season"]
# D-56 d: unit -> first year of the new territory.
NAMED_BREAKS = {"Can Tho": 2004, "Dak Lak": 2004, "Lai Chau": 2004, "Lao Cai": 2004}
FAO_BAND = 0.3  # D-70: +-30% of the previous 3-year mean
FAO_WINDOW = 3


def apply_known_boundary_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (kept, removed) after rules 1-3 and the D-34 series drops; `removed` carries a `removal_reason` column."""
    reason = pd.Series("", index=df.index)
    reason[df["province_nso"].isin(DROP_PROVINCES)] = "province merged 2008, no boundary (D-28 rule 1)"
    for prov, first_year in DROP_BEFORE.items():
        reason[(df["province_nso"] == prov) & (df["year"] < first_year)] = (
            f"pre-{first_year} {prov} is a different territory (D-28 rule 2)"
        )
    for (prov, crop, season), why in DROP_SERIES.items():
        reason[(df["province_nso"] == prov) & (df["crop"] == crop) & (df["season"] == season)] = why
    removed = df[reason != ""].assign(removal_reason=reason[reason != ""])
    kept = df[reason == ""].copy()
    kept["flag_2008_transfer"] = kept["province_nso"].isin(FLAG_2008_TRANSFER) & (kept["year"] < MERGE_YEAR)
    return kept, removed


def assign_segments(df: pd.DataFrame, threshold: float = BREAK_THRESHOLD) -> pd.DataFrame:
    """Add `segment` (0, 1, ...) and `series_id` per province-crop-season, splitting at planted-area jumps.

    A break is placed at year t when |area_t - area_prev| / area_prev > threshold, or when at least one year between
    the previous year with an area value and t has no value (D-31). Rows without area keep the current segment. Also adds `break_here` (True on the first year
    of each new segment after the first).
    """
    out = []
    for key, g in df.sort_values("year").groupby(SERIES_KEY, sort=False):
        seg, prev, prev_year = 0, None, None
        segs, breaks = [], []
        named = NAMED_BREAKS.get(key[0])
        for year, area in zip(g["year"], g["planted_area_ha"], strict=True):
            is_break = False
            if named is not None and year == named and prev is not None:
                seg += 1  # D-56 d: named administrative break
                is_break = True
            elif pd.notna(area) and prev is not None:
                gap = year - prev_year > 1  # D-31: a missing year in the middle splits
                # D-33 B: from 0 ha to some land is a break
                jump = abs(area - prev) / prev > threshold if prev > 0 else area > 0
                if gap or jump:
                    seg += 1
                    is_break = True
            segs.append(seg)
            breaks.append(is_break)
            if pd.notna(area):
                prev, prev_year = area, year
        ids = [f"{key[0]}|{key[1]}|{key[2]}|{s}" for s in segs]
        out.append(g.assign(segment=segs, break_here=breaks, series_id=ids))
    return pd.concat(out).sort_index()


def flag_fao_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Rule 8 (D-56 d, D-70): add `fao_flagged`, computed per `series_id` in year order.

    prev_avg = right-aligned 3-year rolling mean of yield, lagged one year (the FAO code); flagged when
    yield < prev_avg - 0.3 prev_avg or yield > prev_avg + 0.3 prev_avg. No check (False) where prev_avg is missing,
    i.e. fewer than 3 previous years with a yield. Rows are kept.
    """
    out = df.copy()
    flagged = pd.Series(False, index=out.index)
    for _, g in out.sort_values("year").groupby("series_id", sort=False):
        y = g["yield_t_ha"].astype(float)
        prev = y.rolling(FAO_WINDOW).mean().shift(1)
        hit = prev.notna() & ((y < prev - FAO_BAND * prev) | (y > prev + FAO_BAND * prev))
        flagged.loc[g.index] = hit.to_numpy()
    out["fao_flagged"] = flagged.astype(bool)
    return out


def drop_small_series(
    df: pd.DataFrame, min_median_area: float = MIN_MEDIAN_AREA_HA
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rule 6 (D-32): drop every series_id whose median planted area is below min_median_area. Returns (kept, removed)."""
    median = df.groupby("series_id")["planted_area_ha"].transform("median")
    small = median < min_median_area
    removed = df[small].assign(removal_reason=f"median planted area under {min_median_area:,.0f} ha (D-32)")
    return df[~small].copy(), removed


def prepare_series(
    df: pd.DataFrame, threshold: float = BREAK_THRESHOLD, min_median_area: float = MIN_MEDIAN_AREA_HA
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply rules 1-10. Returns (series table, removed rows with removal_reason)."""
    kept, removed = apply_known_boundary_rules(df)
    series = assign_segments(kept, threshold)
    series, removed_small = drop_small_series(series, min_median_area)
    return flag_fao_outliers(series), pd.concat([removed, removed_small])
