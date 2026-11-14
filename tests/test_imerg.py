"""Tests for the GPM IMERG monthly box download (D-135).

Expected values come from docs/DATA-SOURCES.md (row gpm_imerg_gesdisc: index = (deg + 179.95) / 0.1 for longitude,
(deg + 89.95) / 0.1 for latitude, verified 2026-11-10), the DAS of a monthly file read 2026-11-13 (dimension order
time, lon, lat), the GES DISC listing read 2026-11-13 (file names), and the cell rule of D-135 (POWER cell centre
+-0.25 deg latitude, +-0.3125 deg longitude, lower edge included, upper edge excluded).
"""

import pytest

from fieldshift.data import imerg

LISTING_2020 = """<a href="3B-MO.MS.MRG.3IMERG.20200101-S000000-E235959.01.V07B.HDF5.html">x</a>
<a href="3B-MO.MS.MRG.3IMERG.20200101-S000000-E235959.01.V07B.HDF5.dds">dds</a>
<a href="3B-MO.MS.MRG.3IMERG.20200201-S000000-E235959.02.V07B.HDF5.das">das</a>"""


def test_pixel_index_follows_the_verified_formula():
    assert imerg.pixel_index(-89.95, -179.95) == (0, 0)
    assert imerg.pixel_index(89.95, 179.95) == (1799, 3599)
    assert imerg.pixel_index(19.05, 105.05) == (1090, 2850)


def test_cell_pixels_lat_edges_lower_in_upper_out():
    # cell centre 19.0: latitude band [18.75, 19.25); pixel centres 18.75 .. 19.15 inside, 19.25 outside
    lat_idx, _ = imerg.cell_pixel_ranges(19.0, 105.0)
    assert lat_idx == (imerg.pixel_index(18.75, 0)[0], imerg.pixel_index(19.15, 0)[0])


def test_cell_pixels_lon_band():
    # cell centre 105.0: longitude band [104.6875, 105.3125); pixel centres 104.75 .. 105.25
    _, lon_idx = imerg.cell_pixel_ranges(19.0, 105.0)
    assert lon_idx == (imerg.pixel_index(0, 104.75)[1], imerg.pixel_index(0, 105.25)[1])


def test_box_covers_every_cell():
    cells = [(19.0, 105.0), (18.5, 105.625)]
    lat0, lat1, lon0, lon1 = imerg.box_for_cells(cells)
    for lat, lon in cells:
        (a, b), (c, d) = imerg.cell_pixel_ranges(lat, lon)
        assert lat0 <= a
        assert b <= lat1
        assert lon0 <= c
        assert d <= lon1
    assert (lat0, lon0) == (imerg.cell_pixel_ranges(18.5, 105.625)[0][0], imerg.cell_pixel_ranges(19.0, 105.0)[1][0])


def test_month_file_from_listing():
    assert imerg.month_file(LISTING_2020, 2020, 1) == "3B-MO.MS.MRG.3IMERG.20200101-S000000-E235959.01.V07B.HDF5"
    assert imerg.month_file(LISTING_2020, 2020, 2) == "3B-MO.MS.MRG.3IMERG.20200201-S000000-E235959.02.V07B.HDF5"


def test_month_file_missing_raises():
    with pytest.raises(ValueError, match=r"expected one file for 2020-03"):
        imerg.month_file(LISTING_2020, 2020, 3)


def test_subset_url_uses_time_lon_lat_order():
    url = imerg.subset_url(2020, "F.HDF5", (1081, 1098, 2845, 2860))
    assert url.endswith("/2020/F.HDF5.ascii?precipitation[0:0][2845:2860][1081:1098]")


# Reply layout seen 2026-11-13: one line per longitude index, one value per latitude index.
GOOD = "Dataset: F.HDF5\nprecipitation[0][0], 0.044, 0.051, 0.051\nprecipitation[0][1], 0.051, 0.055, 0.058\n"
BOX = (1082, 1084, 2847, 2848)  # 3 latitudes x 2 longitudes


def test_check_response_accepts_the_seen_layout():
    imerg.check_response(GOOD, BOX)


def test_check_response_rejects_html_empty_and_wrong_count():
    for bad in (
        "<html>login</html>",
        "",
        GOOD.replace(", 0.058", ""),
        GOOD.replace("precipitation[0][1], 0.051, 0.055, 0.058\n", ""),
    ):
        with pytest.raises(ValueError, match=r"not the expected 2 x 3 reply"):
            imerg.check_response(bad, BOX)
