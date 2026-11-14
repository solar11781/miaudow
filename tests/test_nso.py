import hashlib
from pathlib import Path

import pandas as pd
import pytest

from fieldshift.data.nso import (
    build_crop_stats,
    canonical_province,
    consistency_ratio,
    parse_export,
    retrieval_dates,
)

RAW = Path("data/raw/nso")


def _export(title, rows):
    lines = [f'"{title}"', "", '"Cities, provincies","2023","2024","Prel. 2025"']
    lines += rows
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_parse_skips_regions_and_masks_missing():
    raw = (
        _export(
            "Yield of spring rice",
            [
                '" WHOLE COUNTRY",68.0,68.5,69.0',
                '"Nghe An",68.8,69.1,65.9',
                '"Ha Tay","..","..",".."',
            ],
        )
        + b"\x00"
    )
    df = parse_export(raw)
    assert set(df["province_nso"]) == {"Nghe An", "Ha Tay"}
    assert df.loc[df.province_nso == "Ha Tay", "value"].isna().all()
    assert df.loc[(df.province_nso == "Nghe An") & (df.year_label == "2024"), "value"].item() == pytest.approx(69.1)


def test_parse_rejects_ragged_rows():
    with pytest.raises(ValueError, match=r"has 3 cells, header has 4"):
        parse_export(_export("t", ['"Nghe An",1.0,2.0']))


def test_build_converts_units_and_flags_preliminary(tmp_path):
    (tmp_path / "E06.16.csv").write_bytes(_export("area", ['"Nghe An",91.3,91.0,90.6']))
    (tmp_path / "E06.17.csv").write_bytes(_export("yield", ['"Nghe An",68.8,69.1,65.9']))
    (tmp_path / "E06.18.csv").write_bytes(_export("prod", ['"Nghe An",628.3,628.6,596.7']))
    df = build_crop_stats(tmp_path, "2026-11-10")
    row = df[(df.year == 2024) & (df.season == "spring")].iloc[0]
    assert row.planted_area_ha == pytest.approx(91_000)
    assert row.yield_t_ha == pytest.approx(6.91)
    assert row.production_t == pytest.approx(628_600)
    assert not row.yield_derived
    assert df.loc[df.year == 2025, "is_preliminary"].all()
    assert not df.loc[df.year < 2025, "is_preliminary"].any()
    assert consistency_ratio(df).between(0.98, 1.02).all()


def test_peanut_yield_is_derived_and_flagged(tmp_path):
    (tmp_path / "E06.34.csv").write_bytes(_export("area", ['"Nghe An",10129,9457,8740']))
    (tmp_path / "E06.35.csv").write_bytes(_export("prod", ['"Nghe An",28033.9,26292.8,24585.5']))
    df = build_crop_stats(tmp_path, "2026-11-10")
    row = df[df.year == 2024].iloc[0]
    assert row.crop == "peanut"
    assert row.yield_derived
    assert row.yield_t_ha == pytest.approx(26292.8 / 9457)


@pytest.mark.skipif(not (RAW / "E06.17.csv").exists(), reason="real NSO exports not downloaded")
def test_real_exports_are_internally_consistent():
    df = build_crop_stats(RAW, "2026-11-10")
    ratio = consistency_ratio(df)
    # Published production should equal area x yield up to rounding for nearly all rows.
    assert (ratio.between(0.95, 1.05)).mean() > 0.97
    assert df.duplicated(["province_nso", "year", "crop", "season"]).sum() == 0
    na = df[(df.province_nso == "Nghe An") & (df.crop == "rice") & (df.season == "autumn") & ~df.is_preliminary]
    assert na.year.min() == 1995
    assert na.year.max() == 2024
    assert len(na) == 30


def test_spelling_variants_map_to_one_province(tmp_path):
    assert canonical_province("Binh  Duong ") == "Binh Duong"
    assert canonical_province("TP. Ho Chi Minh") == "Ho Chi Minh city"
    assert canonical_province("Thua Thien Hue") == "Thua Thien-Hue"
    (tmp_path / "E06.19.csv").write_bytes(_export("area", ['"Binh  Duong",1.0,1.0,1.0']))
    (tmp_path / "E06.20.csv").write_bytes(_export("yield", ['"Binh Duong",40.0,40.0,40.0']))
    df = build_crop_stats(tmp_path, "2026-11-11")
    assert df["province_nso"].nunique() == 1
    assert df[["planted_area_ha", "yield_t_ha"]].notna().all().all()


@pytest.mark.skipif(not (RAW / "E06.17.csv").exists(), reason="real NSO exports not downloaded")
def test_real_exports_have_64_provinces():
    df = build_crop_stats(RAW, "2026-11-11")
    assert df["province_nso"].nunique() == 64


def test_missing_official_rice_yield_is_not_filled(tmp_path):
    # Source: team decision D-33 C (2026-11-11): official blank yields for rice/maize stay blank;
    # only peanut (no official yield table) gets yield = production / area.
    (tmp_path / "E06.16.csv").write_bytes(_export("area", ['"Nghe An",91.3,91.0,90.6']))
    (tmp_path / "E06.17.csv").write_bytes(_export("yield", ['"Nghe An",68.8,"..",65.9']))
    (tmp_path / "E06.18.csv").write_bytes(_export("prod", ['"Nghe An",628.3,628.6,596.7']))
    df = build_crop_stats(tmp_path, "2026-11-11")
    row = df[df.year == 2024].iloc[0]
    assert pd.isna(row.yield_t_ha)
    assert not row.yield_derived


# retrieved_on per table (05-DATA-CONTRACTS §2; audit 2026-11-13 part B row 19): the date comes from the
# data/MANIFEST.csv row whose sha256 matches the file on disk, never from the build date.
MANIFEST_HEADER = "path,source_id,table,title,url,retrieved_on,method,sha256\n"


def _manifest(path, rows):
    path.write_text(MANIFEST_HEADER + "".join(f"{p},nso_e06,{t},title,url,{d},method,{h}\n" for p, t, d, h in rows))
    return path


def test_retrieval_dates_come_from_the_manifest_row_that_matches_the_file(tmp_path):

    raw = tmp_path / "nso"
    raw.mkdir()
    (raw / "E06.16.csv").write_bytes(_export("area", ['"Nghe An",91.3,91.0,90.6']))
    digest = hashlib.sha256((raw / "E06.16.csv").read_bytes()).hexdigest()
    m = _manifest(
        tmp_path / "MANIFEST.csv",
        [
            ("x", "E06.16", "2026-11-01", "0" * 64),  # an older export
            ("x", "E06.16", "2026-11-10", digest),
        ],
    )
    assert retrieval_dates(m, raw) == {"E06.16": "2026-11-10"}


def test_a_file_without_a_matching_manifest_row_is_refused(tmp_path):
    raw = tmp_path / "nso"
    raw.mkdir()
    (raw / "E06.16.csv").write_bytes(_export("area", ['"Nghe An",91.3,91.0,90.6']))
    m = _manifest(tmp_path / "MANIFEST.csv", [("x", "E06.16", "2026-11-10", "0" * 64)])
    with pytest.raises(ValueError, match=r"E06\.16"):
        retrieval_dates(m, raw)


def test_build_writes_each_table_date_and_refuses_mixed_dates_in_one_row(tmp_path):
    (tmp_path / "E06.16.csv").write_bytes(_export("area", ['"Nghe An",91.3,91.0,90.6']))
    (tmp_path / "E06.17.csv").write_bytes(_export("yield", ['"Nghe An",68.8,69.1,65.9']))
    (tmp_path / "E06.35.csv").write_bytes(_export("prod", ['"Nghe An",100.0,110.0,120.0']))
    df = build_crop_stats(tmp_path, {"E06.16": "2026-11-10", "E06.17": "2026-11-10", "E06.35": "2026-11-12"})
    assert set(df.loc[df.crop == "rice", "retrieved_on"]) == {"2026-11-10"}
    assert set(df.loc[df.crop == "peanut", "retrieved_on"]) == {"2026-11-12"}
    with pytest.raises(ValueError, match="different dates"):
        build_crop_stats(tmp_path, {"E06.16": "2026-11-10", "E06.17": "2026-11-11", "E06.35": "2026-11-12"})


@pytest.mark.skipif(not (RAW / "E06.17.csv").exists(), reason="real NSO exports not downloaded")
def test_real_exports_take_their_retrieval_date_from_the_manifest():
    # data/MANIFEST.csv: all 17 NSO exports retrieved 2026-11-10.
    dates = retrieval_dates("data/MANIFEST.csv", RAW)
    assert len(dates) == 17
    assert set(dates.values()) == {"2026-11-10"}
