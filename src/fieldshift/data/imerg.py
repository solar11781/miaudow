"""Download a box of NASA GPM IMERG Final monthly V07 (GPM_3IMERGM) around POWER cells, as raw OPeNDAP ASCII (D-135).

Grid facts: docs/DATA-SOURCES.md row gpm_imerg_gesdisc (0.1 deg pixels centred at -179.95 + 0.1 i and -89.95 + 0.1 j);
dimension order time, lon, lat (file DAS, 2026-11-13). Cell rule (D-135): IMERG pixels whose centres lie inside the
POWER cell, centre +-0.25 deg latitude and +-0.3125 deg longitude, lower edge included, upper edge excluded.
The responses are stored unchanged; parsing and the monthly totals belong to the rain check (05-DATA-CONTRACTS §5c).
"""

from __future__ import annotations

import re

BASE_URL = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07"
HALF_DLAT = 0.25  # POWER cell half height (farmland_weights.POWER_DLAT / 2)
HALF_DLON = 0.3125  # POWER cell half width (farmland_weights.POWER_DLON / 2)
_SCALE = 10_000  # work in 1e-4 degree integers so the edge rule is exact


def pixel_index(lat: float, lon: float) -> tuple[int, int]:
    """(lat index, lon index) of the pixel centred at (lat, lon)."""
    return round((lat + 89.95) / 0.1), round((lon + 179.95) / 0.1)


def _centres_in(lo: float, hi: float, first_centre: float) -> tuple[int, int]:
    """First and last index of pixel centres c = first_centre + 0.1 k with lo <= c < hi."""
    lo_u, hi_u, c0, step = (round(v * _SCALE) for v in (lo, hi, first_centre, 0.1))
    first = -((c0 - lo_u) // step)  # ceil((lo - c0) / step)
    last = -((c0 - hi_u) // step) - 1  # ceil((hi - c0) / step) - 1
    if last < first:
        raise ValueError(f"no pixel centre in [{lo}, {hi})")
    return first, last


def cell_pixel_ranges(lat: float, lon: float) -> tuple[tuple[int, int], tuple[int, int]]:
    """Inclusive (lat index range, lon index range) of the pixels inside the POWER cell centred at (lat, lon)."""
    return (
        _centres_in(lat - HALF_DLAT, lat + HALF_DLAT, -89.95),
        _centres_in(lon - HALF_DLON, lon + HALF_DLON, -179.95),
    )


def box_for_cells(cells) -> tuple[int, int, int, int]:
    """(lat0, lat1, lon0, lon1) inclusive index box covering every cell."""
    ranges = [cell_pixel_ranges(lat, lon) for lat, lon in cells]
    if not ranges:
        raise ValueError("no cells")
    return (
        min(r[0][0] for r in ranges),
        max(r[0][1] for r in ranges),
        min(r[1][0] for r in ranges),
        max(r[1][1] for r in ranges),
    )


def month_file(listing_html: str, year: int, month: int) -> str:
    """The one monthly HDF5 file name of (year, month) in a GES DISC directory listing."""
    pattern = rf"3B-MO\.MS\.MRG\.3IMERG\.{year:04d}{month:02d}01-S000000-E235959\.{month:02d}\.V07[A-Z]?\.HDF5"
    names = set(re.findall(pattern, listing_html))  # the listing repeats a name with .html, .dds, .das suffixes
    if len(names) != 1:
        raise ValueError(f"expected one file for {year}-{month:02d}, found {sorted(names)}")
    return names.pop()


def subset_url(year: int, file_name: str, box: tuple[int, int, int, int]) -> str:
    lat0, lat1, lon0, lon1 = box
    return f"{BASE_URL}/{year:04d}/{file_name}.ascii?precipitation[0:0][{lon0}:{lon1}][{lat0}:{lat1}]"


def check_response(text: str, box: tuple[int, int, int, int]) -> None:
    """Reject a reply that is not one line per longitude with one number per latitude of the box (for example an
    HTML login page) before it is cached. Fill values stay as they are; the rain check handles them."""
    lat0, lat1, lon0, lon1 = box
    rows = [line.split(",")[1:] for line in text.splitlines() if line.startswith("precipitation[0][")]
    if len(rows) != lon1 - lon0 + 1 or any(len(r) != lat1 - lat0 + 1 for r in rows):
        raise ValueError(f"not the expected {lon1 - lon0 + 1} x {lat1 - lat0 + 1} reply: {text.lstrip()[:80]!r}")
    for r in rows:
        [float(v) for v in r]
