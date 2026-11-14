"""Tests for matching map boundaries to NSO province names (written before the code, D-29).

Spec: D-26 needs one boundary per NSO province; data/reference/admin_units.csv holds the canonical NSO names with
Vietnamese names; the geoBoundaries VNM ADM1 file has 64 units including "Côn Đảo" and a name "Hà Nội\\t" with a tab
(observed 2026-11-11). Côn Đảo was a district of Bà Rịa - Vũng Tàu before 1 July 2025 (D-35, research 2026-11-11),
so its shape belongs to "Ba Ria - Vung Tau" for 1995-2024 data. Hà Tây has no boundary (D-28).
"""

from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box

from fieldshift.data.boundaries import match_boundary_name, province_geometries

GEOJSON = Path("data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson")
ADMIN = Path("data/reference/admin_units.csv")


@pytest.mark.parametrize(
    ("shape_name", "expected"),
    [
        ("Nghệ An", "Nghe An"),  # admin_units.csv row
        ("Hà Tĩnh", "Ha Tinh"),
        ("Hà Nội\t", "Ha Noi"),  # stray tab observed in the real file
        ("Ho Chi Minh", "Ho Chi Minh city"),  # geoBoundaries spelling vs NSO canonical
        ("Bà Rịa\u2013Vũng Tàu", "Ba Ria - Vung Tau"),  # en dash in geoBoundaries, hyphen with spaces in NSO
        ("Thừa Thiên Huế", "Thua Thien-Hue"),
        ("Đắk Lắk", "Dak Lak"),
        ("Côn Đảo", "Ba Ria - Vung Tau"),  # D-35
    ],
)
def test_known_name_pairs(shape_name, expected):
    assert match_boundary_name(shape_name, ADMIN) == expected


def test_unknown_name_raises():
    # Spec (no assumptions): a name that cannot be matched must fail loudly, never be guessed.
    with pytest.raises(KeyError):
        match_boundary_name("Atlantis", ADMIN)


@pytest.mark.skipif(not GEOJSON.exists(), reason="boundary file not downloaded")
def test_real_file_gives_one_geometry_per_province_except_ha_tay():
    geoms = province_geometries(GEOJSON, ADMIN)

    admin = pd.read_csv(ADMIN)
    expected = set(admin.province_nso) - {"Ha Tay"}
    assert set(geoms) == expected
    assert len(geoms) == 63


@pytest.mark.skipif(not GEOJSON.exists(), reason="boundary file not downloaded")
def test_ba_ria_vung_tau_includes_con_dao():
    geoms = province_geometries(GEOJSON, ADMIN)
    # Côn Đảo islands lie around 8.7 N, 106.6 E (well south-east of mainland Bà Rịa - Vũng Tàu).
    assert geoms["Ba Ria - Vung Tau"].intersects(box(106.4, 8.5, 106.8, 8.9))


@pytest.mark.skipif(not GEOJSON.exists(), reason="boundary file not downloaded")
def test_nghe_an_geometry_matches_the_map_used_in_e000b():
    geoms = province_geometries(GEOJSON, ADMIN)
    minx, miny, maxx, maxy = geoms["Nghe An"].bounds
    # Bounds observed 2026-11-11 from the same file (docs/figures/nghe_an_power_grid.png).
    assert (round(minx, 2), round(miny, 2), round(maxx, 2), round(maxy, 2)) == (103.88, 18.56, 105.81, 20.04)
