"""Independent specification tests for fieldshift.data.nso (NSO PX-Web CSV exports -> crop_stats).

Written without reading the implementation (D-30). Every expectation cites its source.
Real-data expectations were read by hand from data/raw/nso/*.csv (retrieved 2026-11-10, sha256 in data/MANIFEST.csv).
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.data.nso import build_crop_stats, canonical_province, consistency_ratio, parse_export

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "nso"
ADMIN = ROOT / "data" / "reference" / "admin_units.csv"
ALL_TABLES = [f"E06.{n}" for n in range(13, 28)] + ["E06.34", "E06.35"]
HAVE_RAW = all((RAW / f"{t}.csv").exists() for t in ALL_TABLES)
needs_raw = pytest.mark.skipif(not HAVE_RAW, reason="NSO raw exports not present (gitignored)")
needs_admin = pytest.mark.skipif(not ADMIN.exists(), reason="admin_units.csv missing")

REGIONS = {
    "WHOLE COUNTRY",
    "Red River Delta",
    "Northern midlands and mountain areas",
    "North Central and Central coastal areas",
    "Central Highlands",
    "South East",
    "Mekong River Delta",
}
CONTRACT_COLUMNS = {
    "province_nso",
    "year",
    "crop",
    "season",
    "is_preliminary",
    "planted_area_ha",
    "yield_t_ha",
    "production_t",
    "yield_derived",
    "source_table",
    "retrieved_on",
}
# table ids -> (crop, season, quantity); from the task interface list and 05-DATA-CONTRACTS §2 season names
TABLES = {
    "E06.13": ("rice", "annual", "area"),
    "E06.14": ("rice", "annual", "yield"),
    "E06.15": ("rice", "annual", "prod"),
    "E06.16": ("rice", "spring", "area"),
    "E06.17": ("rice", "spring", "yield"),
    "E06.18": ("rice", "spring", "prod"),
    "E06.19": ("rice", "autumn", "area"),
    "E06.20": ("rice", "autumn", "yield"),
    "E06.21": ("rice", "autumn", "prod"),
    "E06.22": ("rice", "winter", "area"),
    "E06.23": ("rice", "winter", "yield"),
    "E06.24": ("rice", "winter", "prod"),
    "E06.25": ("maize", "annual", "area"),
    "E06.26": ("maize", "annual", "yield"),
    "E06.27": ("maize", "annual", "prod"),
    "E06.34": ("peanut", "annual", "area"),
    "E06.35": ("peanut", "annual", "prod"),
}


def _admin_names() -> set[str]:
    with ADMIN.open(encoding="utf-8") as f:
        return {row["province_nso"] for row in csv.DictReader(f)}


# ---------------------------------------------------------------- synthetic export builder
# Format (external fact, and matches the real files byte for byte in structure): line 1 quoted title, blank line,
# header "Cities, provincies" + year labels, one row per region/province, CRLF line ends, ".." = missing,
# and the real exports end with a single NUL byte after the last CRLF (seen in all 17 raw files).

LABELS = ["2023", "2024", "Prel. 2025"]


def _export(title: str, rows: list[tuple[str, list[str]]], labels=LABELS, trailing_nul=True) -> bytes:
    lines = [f'"{title}"', ""]
    lines.append(",".join(['"Cities, provincies"'] + [f'"{lab}"' for lab in labels]))
    for name, vals in rows:
        lines.append(",".join([f'"{name}"', *vals]))
    data = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    return data + (b"\x00" if trailing_nul else b"")


def _simple_export(**kw) -> bytes:
    rows = [
        (" WHOLE COUNTRY", ["44.3", "48.0", "49.6"]),
        ("Red River Delta", ["44.5", "53.5", "53.6"]),
        ("Ha Noi", ["30.6", "41.3", "39.5"]),
        ("Ha Tay", ["39.0", "..", ".."]),
        ("North Central and Central coastal areas", ["40.0", "41.0", "42.0"]),
        ("Nghe An", ["60.0", "69.1", "65.9"]),
    ]
    return _export("Yield of spring rice by province by Cities, provincies and Year", rows, **kw)


def _cell(df: pd.DataFrame, prov: str, label: str):
    sel = df[(df["province_nso"].map(canonical_province) == prov) & (df["year_label"].astype(str) == label)]
    return sel["value"]


# ---------------------------------------------------------------- tests of parse_export on synthetic exports


def test_parse_export_columns():
    # Source: interface spec: columns province_nso, year_label, value
    df = parse_export(_simple_export())
    assert {"province_nso", "year_label", "value"} <= set(df.columns)


def test_parse_export_drops_aggregate_rows():
    # Source: external fact (NSO format): " WHOLE COUNTRY" and the six region names are not provinces
    df = parse_export(_simple_export())
    names = {" ".join(str(p).split()) for p in df["province_nso"]}
    assert names == {"Ha Noi", "Ha Tay", "Nghe An"}
    assert not names & REGIONS


def test_parse_export_year_labels_include_preliminary():
    # Source: external fact (NSO format): header year labels "1995".."2024","Prel. 2025"
    df = parse_export(_simple_export())
    assert set(df["year_label"].astype(str)) == set(LABELS)


def test_parse_export_cells_aligned_with_header():
    # Source: synthetic export above: Nghe An 2023=60.0, 2024=69.1, Prel. 2025=65.9 (ratios independent of units)
    df = parse_export(_simple_export())
    v23 = float(_cell(df, "Nghe An", "2023").iloc[0])
    v24 = float(_cell(df, "Nghe An", "2024").iloc[0])
    v25 = float(_cell(df, "Nghe An", "Prel. 2025").iloc[0])
    assert v24 / v23 == pytest.approx(69.1 / 60.0)
    assert v25 / v23 == pytest.approx(65.9 / 60.0)
    h23 = float(_cell(df, "Ha Noi", "2023").iloc[0])
    assert h23 / v23 == pytest.approx(30.6 / 60.0)


def test_parse_export_missing_is_null_not_zero():
    # Source: external fact (".." = missing) + 05-DATA-CONTRACTS conventions: missing = null (never 0 or -999)
    df = parse_export(_simple_export())
    vals = _cell(df, "Ha Tay", "2024")
    assert vals.isna().all()  # either absent (empty) or NaN
    assert not (df["value"] == 0).any()
    assert not (df["value"] == -999).any()


def test_parse_export_one_row_per_province_and_label():
    # Source: interface spec: long format, one value per (province, year label)
    df = parse_export(_simple_export())
    assert not df.duplicated(["province_nso", "year_label"]).any()
    # Corrected 2026-11-11 (arithmetic): 3 provinces x 3 labels = 9 cells, minus 2 ".." cells of Ha Tay = 7
    assert df["value"].notna().sum() == 7


def test_parse_export_handles_trailing_nul_byte():
    # Source: real data: every file in data/raw/nso ends with b"\r\n\x00" (inspected 2026-11-11)
    a = parse_export(_simple_export(trailing_nul=True))
    b = parse_export(_simple_export(trailing_nul=False))
    assert len(a) == len(b)
    assert {" ".join(str(p).split()) for p in a["province_nso"]} == {"Ha Noi", "Ha Tay", "Nghe An"}


def test_parse_export_region_without_leading_space():
    # Source: real data: E06.19 spells the aggregate row "WHOLE COUNTRY" without the leading space
    rows = [("WHOLE COUNTRY", ["1", "2", "3"]), ("Mekong River Delta", ["1", "2", "3"]), ("Can Tho", ["4", "5", "6"])]
    df = parse_export(_export("Planted area of autumn rice by province by Cities, provincies and Year", rows))
    assert {" ".join(str(p).split()) for p in df["province_nso"]} == {"Can Tho"}


# ---------------------------------------------------------------- canonical_province


@pytest.mark.parametrize(
    ("variant", "reference"),
    [
        ("Thai  Nguyen", "Thai Nguyen"),  # real data: double space in E06.13 etc.
        ("Quang  Nam", "Quang Nam"),
        ("Quang  Ngai", "Quang Ngai"),
        ("Khanh  Hoa", "Khanh Hoa"),
        ("Ninh  Thuan", "Ninh Thuan"),
        ("Binh  Duong", "Binh Duong"),
        ("Kien  Giang", "Kien Giang"),
        ("TP. Ho Chi Minh", "Ho Chi Minh city"),  # real data: E06.19-21 vs E06.13 spelling
        ("Thua Thien Hue", "Thua Thien-Hue"),  # real data: E06.19-21 vs E06.13 spelling
    ],
)
def test_canonical_province_merges_real_spelling_variants(variant, reference):
    # Source: real data spellings (data/raw/nso) + docs/STATUS.md (variants must merge: 72 names -> 64 provinces)
    assert canonical_province(variant) == canonical_province(reference)


@pytest.mark.parametrize("name", ["Nghe An", "Ha Tinh", "Thanh Hoa", "Ha Tay", "Thai  Nguyen", "TP. Ho Chi Minh"])
def test_canonical_province_is_idempotent(name):
    # Source: interface spec: one canonical spelling per province (canonical of canonical is itself)
    c = canonical_province(name)
    assert canonical_province(c) == c


def test_canonical_province_keeps_nghe_an():
    # Source: 05-DATA-CONTRACTS §2: province_nso holds the NSO English name, e.g. "Nghe An"
    assert canonical_province("Nghe An") == "Nghe An"


@needs_admin
@pytest.mark.parametrize(
    "name",
    ["Thai  Nguyen", "TP. Ho Chi Minh", "Thua Thien Hue", "Kien  Giang", "Ha Tay", "Nghe An", "Ho Chi Minh city"],
)
def test_canonical_province_is_a_reference_unit(name):
    # Source: data/reference/admin_units.csv (historical NSO units "as named in the NSO English exports", SOURCES.md)
    assert canonical_province(name) in _admin_names()


@needs_raw
@needs_admin
def test_canonical_names_of_all_raw_rows_are_the_64_reference_units():
    # Source: docs/STATUS.md (64 provinces after merging variants) + admin_units.csv (63 provinces + Ha Tay)
    names = set()
    for t in ALL_TABLES:
        names |= {canonical_province(p) for p in parse_export((RAW / f"{t}.csv").read_bytes())["province_nso"]}
    assert names == _admin_names()
    assert len(names) == 64


# ---------------------------------------------------------------- consistency_ratio


def test_consistency_ratio_definition():
    # Source: documented contract (05-DATA-CONTRACTS section 2, 2026-11-11): production / (area * yield) for rows with
    # all three values, area and yield > 0, and a published (not derived) yield; derived-yield rows are excluded
    # because they equal 1 by construction.
    df = pd.DataFrame(
        {
            "planted_area_ha": [100.0, 2000.0, 50.0, 10.0, 0.0],
            "yield_t_ha": [5.0, 4.0, 2.0, 3.0, 1.0],
            "production_t": [500.0, 4000.0, 110.0, 30.0, 0.0],
            "yield_derived": [False, False, False, True, False],
        }
    )
    r = consistency_ratio(df)
    assert isinstance(r, pd.Series)
    assert list(r.round(10)) == [1.0, 0.5, 1.1]


# ---------------------------------------------------------------- build_crop_stats (synthetic raw dir)
# Units [DATA-SOURCES nso_e06 + A-11]: rice/maize area thousand ha, yield quintal/ha, production thousand tonnes;
# peanut area ha, production tonnes. Contract §2: area in ha, yield t/ha (q/ha / 10), production t.

SEASON_F = {
    ("rice", "annual"): 6.0,
    ("rice", "spring"): 1.0,
    ("rice", "autumn"): 2.0,
    ("rice", "winter"): 3.0,
    ("maize", "annual"): 4.0,
}
YEAR_F = {"2023": 1.0, "2024": 1.2, "Prel. 2025": 1.1}


def _syn_area_th_ha(cs, lab):
    return 2.5 * SEASON_F[cs] * YEAR_F[lab]


def _syn_yield_q_ha(cs, lab):
    return 40.0 + SEASON_F[cs] + (2.0 if lab == "2024" else 0.0)


def _syn_prod_th_t(cs, lab):
    return _syn_area_th_ha(cs, lab) * _syn_yield_q_ha(cs, lab) / 10.0


PEANUT_AREA_HA = {"2023": 1000.0, "2024": 1200.0, "Prel. 2025": 1100.0}
PEANUT_PROD_T = {"2023": 2500.0, "2024": 3300.0, "Prel. 2025": 2860.0}


@pytest.fixture(scope="module")
def syn_raw_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("nso_raw")
    for t, (crop, season, qty) in TABLES.items():
        rows = [(" WHOLE COUNTRY", ["1.0", "1.0", "1.0"]), ("Red River Delta", ["1.0", "1.0", "1.0"])]
        rows.append(("Ha Noi", ["..", "..", ".."]))
        rows.append(("North Central and Central coastal areas", ["1.0", "1.0", "1.0"]))
        if crop == "peanut":
            src = PEANUT_AREA_HA if qty == "area" else PEANUT_PROD_T
            vals = [f"{src[lab]:.1f}" for lab in LABELS]
        else:
            f = {"area": _syn_area_th_ha, "yield": _syn_yield_q_ha, "prod": _syn_prod_th_t}[qty]
            vals = [f"{f((crop, season), lab):.4f}" for lab in LABELS]
        rows.append(("Nghe An", vals))
        rows.append(("Thai  Nguyen", vals))
        (d / f"{t}.csv").write_bytes(_export(f"Synthetic {t} by Cities, provincies and Year", rows))
    return d


@pytest.fixture(scope="module")
def syn_stats(syn_raw_dir) -> pd.DataFrame:
    return build_crop_stats(syn_raw_dir, retrieved_on="2026-11-10")


def _row(df, prov, crop, season, year) -> pd.Series:
    sel = df[(df["province_nso"] == prov) & (df["crop"] == crop) & (df["season"] == season) & (df["year"] == year)]
    assert len(sel) == 1, f"expected one row for {prov} {crop} {season} {year}, got {len(sel)}"
    return sel.iloc[0]


def test_build_has_contract_columns(syn_stats):
    # Source: 05-DATA-CONTRACTS §2 column list
    assert set(syn_stats.columns) >= CONTRACT_COLUMNS


def test_build_crop_and_season_values(syn_stats):
    # Source: 05-DATA-CONTRACTS §2: crop in {rice, maize, peanut}; season in {spring, autumn, winter, annual}
    assert set(syn_stats["crop"]) == {"rice", "maize", "peanut"}
    assert set(syn_stats["season"]) <= {"spring", "autumn", "winter", "annual"}
    combos = set(map(tuple, syn_stats[["crop", "season"]].drop_duplicates().to_numpy()))
    assert combos == {
        ("rice", "annual"),
        ("rice", "spring"),
        ("rice", "autumn"),
        ("rice", "winter"),
        ("maize", "annual"),
        ("peanut", "annual"),
    }


def test_build_excludes_aggregate_rows(syn_stats):
    # Source: external fact (NSO format): WHOLE COUNTRY and regions are not provinces
    assert not {" ".join(str(p).split()) for p in syn_stats["province_nso"]} & REGIONS


def test_build_canonicalises_province_names(syn_stats):
    # Source: interface spec (canonical spelling) + real double-space variant "Thai  Nguyen"
    assert "Thai  Nguyen" not in set(syn_stats["province_nso"])
    assert canonical_province("Thai  Nguyen") in set(syn_stats["province_nso"])


@pytest.mark.parametrize("cs", list(SEASON_F))
@pytest.mark.parametrize(("lab", "year"), [("2023", 2023), ("2024", 2024)])
def test_build_rice_maize_unit_conversion(syn_stats, cs, lab, year):
    # Source: DATA-SOURCES units (thousand ha, q/ha, thousand t) + contract §2 (ha, t/ha = q/ha / 10, t)
    r = _row(syn_stats, "Nghe An", cs[0], cs[1], year)
    assert r["planted_area_ha"] == pytest.approx(_syn_area_th_ha(cs, lab) * 1000.0, rel=1e-6)
    assert r["yield_t_ha"] == pytest.approx(_syn_yield_q_ha(cs, lab) / 10.0, rel=1e-6)
    assert r["production_t"] == pytest.approx(_syn_prod_th_t(cs, lab) * 1000.0, rel=1e-6)
    assert not bool(r["yield_derived"])


@pytest.mark.parametrize(("lab", "year"), [("2023", 2023), ("2024", 2024)])
def test_build_peanut_units_and_derived_yield(syn_stats, lab, year):
    # Source: DATA-SOURCES (peanut area ha, production t) + contract §2 (peanut yield derived = production/area, flag)
    r = _row(syn_stats, "Nghe An", "peanut", "annual", year)
    assert r["planted_area_ha"] == pytest.approx(PEANUT_AREA_HA[lab])
    assert r["production_t"] == pytest.approx(PEANUT_PROD_T[lab])
    assert r["yield_t_ha"] == pytest.approx(PEANUT_PROD_T[lab] / PEANUT_AREA_HA[lab])
    assert bool(r["yield_derived"])


def test_build_preliminary_year(syn_stats):
    # Source: contract §2: year 1995..2025, is_preliminary true for "Prel. 2025"
    assert set(syn_stats["year"].astype(int)) == {2023, 2024, 2025}
    prel = syn_stats["year"].astype(int) == 2025
    assert syn_stats.loc[prel, "is_preliminary"].astype(bool).all()
    assert not syn_stats.loc[~prel, "is_preliminary"].astype(bool).any()
    r = _row(syn_stats, "Nghe An", "rice", "spring", 2025)
    assert r["planted_area_ha"] == pytest.approx(_syn_area_th_ha(("rice", "spring"), "Prel. 2025") * 1000.0)


def test_build_year_is_integer(syn_stats):
    # Source: contract §2: year int
    assert pd.api.types.is_integer_dtype(syn_stats["year"])


def test_build_missing_values_are_null(syn_stats):
    # Source: contract conventions: missing = null (never 0 or -999); Ha Noi is ".." everywhere in the fixture
    hn = syn_stats[syn_stats["province_nso"] == "Ha Noi"]
    for col in ["planted_area_ha", "yield_t_ha", "production_t"]:
        assert hn[col].isna().all()
    for col in ["planted_area_ha", "yield_t_ha", "production_t"]:
        assert not (syn_stats[col] == -999).any()


def test_build_retrieved_on_and_source_table(syn_stats):
    # Source: contract §2: source_table e.g. "E06.17"; retrieved_on = retrieval date passed in
    assert {str(pd.Timestamp(v).date()) for v in syn_stats["retrieved_on"]} == {"2026-11-10"}
    for (crop, season), grp in syn_stats.groupby(["crop", "season"]):
        ids = [t for t, (c, s, _) in TABLES.items() if (c, s) == (crop, season)]
        assert all(any(i in str(v) for i in ids) for v in grp["source_table"]), (crop, season)


def test_build_unique_key(syn_stats):
    # Source: contract §2 (one row holds area, yield and production for a province, year, crop, season)
    assert not syn_stats.duplicated(["province_nso", "year", "crop", "season"]).any()


def test_build_consistency_ratio_is_one_for_consistent_input(syn_stats):
    # Source: physical identity area x yield = production; fixture production = area x yield exactly
    full = syn_stats.dropna(subset=["planted_area_ha", "yield_t_ha", "production_t"])
    assert len(full) > 0
    assert np.allclose(consistency_ratio(full).to_numpy(dtype=float), 1.0, rtol=1e-4)


# ---------------------------------------------------------------- real data


@pytest.fixture(scope="module")
def real_stats() -> pd.DataFrame:
    if not HAVE_RAW:
        pytest.skip("NSO raw exports not present")
    return build_crop_stats(RAW, retrieved_on="2026-11-10")


@needs_raw
@pytest.mark.parametrize(("table", "n"), [("E06.17", 64), ("E06.20", 32), ("E06.34", 60), ("E06.35", 60)])
def test_real_parse_export_province_counts(table, n):
    # Source: real data: E06.17 has 64 province rows, E06.20 32, E06.34/35 60 (rows counted by hand)
    df = parse_export((RAW / f"{table}.csv").read_bytes())
    names = {canonical_province(p) for p in df["province_nso"]}
    assert len(names) == n
    assert not {" ".join(str(p).split()) for p in df["province_nso"]} & REGIONS


@needs_raw
def test_real_parse_export_values_aligned():
    # Source: real data E06.17 Nghe An: 2020 = 66.5, 2024 = 69.1, Prel. 2025 = 65.9; Ha Noi 2008 = 59.8
    df = parse_export((RAW / "E06.17.csv").read_bytes())
    v20 = float(_cell(df, "Nghe An", "2020").iloc[0])
    assert float(_cell(df, "Nghe An", "2024").iloc[0]) / v20 == pytest.approx(69.1 / 66.5)
    assert float(_cell(df, "Nghe An", "Prel. 2025").iloc[0]) / v20 == pytest.approx(65.9 / 66.5)
    assert float(_cell(df, "Ha Noi", "2008").iloc[0]) / v20 == pytest.approx(59.8 / 66.5)


@needs_raw
def test_real_parse_export_ha_tay_missing_after_2007():
    # Source: real data E06.17 Ha Tay: 54.5 in 2007, ".." from 2008 (D-28)
    df = parse_export((RAW / "E06.17.csv").read_bytes())
    assert _cell(df, "Ha Tay", "2008").isna().all()
    assert _cell(df, "Ha Tay", "2007").notna().all()


@needs_raw
def test_real_nghe_an_spring_rice_2024(real_stats):
    # Source: real data: E06.16 = 91.0 thousand ha, E06.17 = 69.1 q/ha, E06.18 = 628.6 thousand t (Nghe An 2024)
    r = _row(real_stats, "Nghe An", "rice", "spring", 2024)
    assert r["planted_area_ha"] == pytest.approx(91_000.0)
    assert r["yield_t_ha"] == pytest.approx(6.91)
    assert r["production_t"] == pytest.approx(628_600.0)
    assert not bool(r["is_preliminary"])
    assert not bool(r["yield_derived"])


@needs_raw
def test_real_nghe_an_spring_rice_prel_2025(real_stats):
    # Source: real data: E06.16 Nghe An "Prel. 2025" = 90.6 thousand ha, E06.17 = 65.9 q/ha
    r = _row(real_stats, "Nghe An", "rice", "spring", 2025)
    assert bool(r["is_preliminary"])
    assert r["planted_area_ha"] == pytest.approx(90_600.0)
    assert r["yield_t_ha"] == pytest.approx(6.59)


@needs_raw
def test_real_nghe_an_whole_year_rice_2024(real_stats):
    # Source: real data: E06.13 = 168.1 thousand ha, E06.14 = 60.37 q/ha, E06.15 = 1014.94 thousand t (Nghe An 2024)
    r = _row(real_stats, "Nghe An", "rice", "annual", 2024)
    assert r["planted_area_ha"] == pytest.approx(168_100.0)
    assert r["yield_t_ha"] == pytest.approx(6.037)
    assert r["production_t"] == pytest.approx(1_014_940.0)


@needs_raw
def test_real_nghe_an_maize_2024(real_stats):
    # Source: real data: E06.25 = 46.2 thousand ha, E06.26 = 47.4 q/ha, E06.27 = 219.30 thousand t (Nghe An 2024)
    r = _row(real_stats, "Nghe An", "maize", "annual", 2024)
    assert r["planted_area_ha"] == pytest.approx(46_200.0)
    assert r["yield_t_ha"] == pytest.approx(4.74)
    assert r["production_t"] == pytest.approx(219_300.0)


@needs_raw
def test_real_nghe_an_peanut_2020(real_stats):
    # Source: real data: E06.34 = 12902 ha, E06.35 = 34284.8 t (Nghe An 2020); contract: yield derived = prod/area
    r = _row(real_stats, "Nghe An", "peanut", "annual", 2020)
    assert r["planted_area_ha"] == pytest.approx(12_902.0)
    assert r["production_t"] == pytest.approx(34_284.8)
    assert r["yield_t_ha"] == pytest.approx(34_284.8 / 12_902.0)
    assert bool(r["yield_derived"])


@needs_raw
@pytest.mark.parametrize(("season", "n"), [("spring", 1863), ("autumn", 908), ("winter", 1758)])
def test_real_rice_season_yield_counts(real_stats, season, n):
    # Source: real data: non-".." province yield cells 1995-2024 counted by hand in E06.17 / E06.20 / E06.23
    # (no cell in these seasons has area and production but no yield, so no derivation can change the count)
    d = real_stats[
        (real_stats["crop"] == "rice") & (real_stats["season"] == season) & ~real_stats["is_preliminary"].astype(bool)
    ]
    assert d["yield_t_ha"].notna().sum() == n


@needs_raw
def test_real_peanut_rows(real_stats):
    # Source: real data E06.34/35: 420 province-year cells 2018-2024 with both area and production, 60 provinces
    d = real_stats[(real_stats["crop"] == "peanut") & ~real_stats["is_preliminary"].astype(bool)]
    d = d[d["yield_t_ha"].notna()]
    assert len(d) == 420
    assert d["province_nso"].nunique() == 60
    assert set(d["year"].astype(int)) == set(range(2018, 2025))
    assert d["yield_derived"].astype(bool).all()


@needs_raw
def test_real_autumn_rice_has_32_provinces(real_stats):
    # Source: real data E06.19-21 (32 province rows); 03-ML-SPEC §2 "32 provinces only"
    d = real_stats[(real_stats["crop"] == "rice") & (real_stats["season"] == "autumn")]
    d = d.dropna(subset=["planted_area_ha", "yield_t_ha", "production_t"], how="all")
    assert d["province_nso"].nunique() == 32
    assert "Nghe An" in set(d["province_nso"])


@needs_raw
def test_real_years_range(real_stats):
    # Source: contract §2 (year 1995..2025) + real data header ("1995".."2024","Prel. 2025")
    years = real_stats["year"].astype(int)
    assert years.min() == 1995
    assert years.max() == 2025
    assert real_stats.loc[years == 2025, "is_preliminary"].astype(bool).all()
    assert not real_stats.loc[years < 2025, "is_preliminary"].astype(bool).any()


@needs_raw
def test_real_ha_tay_has_no_values_from_2008(real_stats):
    # Source: real data: Ha Tay ".." from 2008 in every table (D-28); missing must stay null
    d = real_stats[(real_stats["province_nso"] == "Ha Tay") & (real_stats["year"].astype(int) >= 2008)]
    for col in ["planted_area_ha", "yield_t_ha", "production_t"]:
        assert d[col].isna().all()
    early = real_stats[(real_stats["province_nso"] == "Ha Tay") & (real_stats["year"].astype(int) == 2007)]
    assert early["planted_area_ha"].notna().any()


@needs_raw
def test_real_unique_key_and_retrieved_on(real_stats):
    # Source: contract §2 key columns and retrieved_on
    assert not real_stats.duplicated(["province_nso", "year", "crop", "season"]).any()
    assert {str(pd.Timestamp(v).date()) for v in real_stats["retrieved_on"]} == {"2026-11-10"}


@needs_raw
@pytest.mark.parametrize(
    ("crop", "season"),
    [("rice", "annual"), ("rice", "spring"), ("rice", "autumn"), ("rice", "winter"), ("maize", "annual")],
)
def test_real_area_times_yield_matches_production(real_stats, crop, season):
    # Source: physical identity + own count from raw CSVs: >= 98.5% of cells per table agree within 5%
    # (lowest table, maize, 98.6% when computed by hand with the documented unit factors)
    d = real_stats[(real_stats["crop"] == crop) & (real_stats["season"] == season)]
    d = d.dropna(subset=["planted_area_ha", "yield_t_ha", "production_t"])
    d = d[d["planted_area_ha"] * d["yield_t_ha"] > 0]
    r = consistency_ratio(d).astype(float)
    assert r.median() == pytest.approx(1.0, abs=0.01)
    assert ((r - 1.0).abs() <= 0.05).mean() >= 0.985


@needs_raw
def test_real_yields_have_plausible_magnitude(real_stats):
    # Source: external agronomic fact: typical provincial rice and maize yields are a few t/ha (median 3-8 t/ha);
    # a wrong unit factor (q/ha not divided by 10, or divided by 100) would move the median by 10x.
    # Not every value is checked: the raw data holds a few implausible cells (e.g. E06.17 Ben Tre 2020 = 0.4 q/ha).
    for crop in ["rice", "maize"]:
        y = real_stats.loc[real_stats["crop"] == crop, "yield_t_ha"].dropna()
        assert 3.0 <= y.median() <= 8.0, crop
    area = real_stats["planted_area_ha"].dropna()
    assert (area >= 0).all()
    # real data E06.13: Nghe An whole-year rice 2018 = 186.4 thousand ha, so 186,400 ha (ha, not thousand ha)
    na = real_stats[
        (real_stats["province_nso"] == "Nghe An")
        & (real_stats["crop"] == "rice")
        & (real_stats["season"] == "annual")
        & (real_stats["year"].astype(int) == 2018)
    ]
    assert na["planted_area_ha"].iloc[0] == pytest.approx(186_400.0)
