"""Tests for season weather windows (written before the code, D-29).

Spec: D-37 (windows from the NSO calendar "Phụ lục 1", source R-V05, verified 2026-11-11; window =
first sowing month to last harvest month; statistical year = agricultural year; Mekong summer-autumn excluded),
D-38 ("central coast" row = the 8 South Central coast provinces; North Central = 6 provinces).
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from fieldshift.features.season_windows import Calendar, calendar_region, load_calendar, season_window

RAW = Path("data/raw/nso/E06.14.csv")


@pytest.mark.parametrize(
    ("season", "region", "year", "start", "end"),
    [
        ("spring", "north_central", 2010, date(2010, 2, 1), date(2010, 6, 30)),  # Feb-Mar sow, May-Jun harvest
        ("autumn", "north_central", 2010, date(2010, 5, 1), date(2010, 9, 30)),  # May-Jun / Aug-Sep
        ("winter", "north_central", 2010, date(2010, 7, 1), date(2010, 11, 30)),  # Jul-Aug / Oct-Nov
        ("spring", "central_coast", 2010, date(2010, 1, 1), date(2010, 5, 31)),  # Jan-Feb / Apr-May
        ("winter", "central_coast", 2012, date(2012, 7, 1), date(2012, 12, 31)),  # Jul-Sep / Nov-Dec
        ("spring", "red_river_delta", 2010, date(2010, 2, 1), date(2010, 6, 30)),  # Feb-Mar / May-Jun
        ("winter", "red_river_delta", 2010, date(2010, 7, 1), date(2010, 11, 30)),  # Jul-Aug / Oct-Nov
        ("spring", "northern_mountains", 2010, date(2010, 3, 1), date(2010, 7, 31)),  # Mar-Apr / Jun-Jul
        ("winter", "northern_mountains", 2010, date(2010, 8, 1), date(2010, 12, 31)),  # Aug-Sep / Nov-Dec
        ("spring", "highlands_southeast", 2010, date(2009, 12, 1), date(2010, 6, 30)),  # Dec(prev)-Mar / Mar-Jun
        ("autumn", "highlands_southeast", 2010, date(2010, 5, 1), date(2010, 9, 30)),
        ("winter", "highlands_southeast", 2010, date(2010, 7, 1), date(2010, 12, 31)),
        ("spring", "mekong", 2010, date(2009, 11, 1), date(2010, 4, 30)),  # Nov-Dec(prev)+Jan / Feb-Apr
        ("winter", "mekong", 2012, date(2011, 8, 1), date(2012, 2, 29)),  # Aug-Oct(prev) / Dec(prev)-Feb, leap year
    ],
)
def test_windows_match_nso_calendar(season, region, year, start, end):
    assert season_window(season, region, year) == (start, end)


def test_mekong_summer_autumn_is_excluded():
    # D-37: the Mekong NSO "autumn" figure adds two crops; no window is defined.
    with pytest.raises(ValueError, match=r"adds hè thu and thu đông"):
        season_window("autumn", "mekong", 2010)


def test_season_without_calendar_entry_raises():
    # NSO calendar has no summer-autumn row for the Red River Delta (no data either); never guess.
    with pytest.raises(ValueError, match=r"no NSO calendar entry for autumn rice"):
        season_window("autumn", "red_river_delta", 2010)


@pytest.mark.skipif(not RAW.exists(), reason="NSO export not present")
@pytest.mark.parametrize(
    ("province", "region"),
    [
        ("Nghe An", "north_central"),
        ("Thua Thien-Hue", "north_central"),
        ("Thanh Hoa", "north_central"),
        ("Da Nang", "central_coast"),
        ("Binh Thuan", "central_coast"),
        ("Lam Dong", "highlands_southeast"),
        ("Binh Duong", "highlands_southeast"),
        ("An Giang", "mekong"),
        ("Ha Noi", "red_river_delta"),
        ("Lao Cai", "northern_mountains"),
    ],
)
def test_province_calendar_regions(province, region):
    # NSO region membership read from the export's region header rows [DATA]; D-38 splits the combined central region.
    assert calendar_region(province, RAW) == region


@pytest.mark.skipif(not RAW.exists(), reason="NSO export not present")
def test_central_split_counts():

    names = pd.read_csv("data/reference/admin_units.csv").province_nso
    regions = [calendar_region(p, RAW) for p in names if p != "Ha Tay"]
    assert regions.count("north_central") == 6
    assert regions.count("central_coast") == 8


def test_windows_are_read_from_the_rules_file(tmp_path):
    # Source: 05-DATA-CONTRACTS §6b: features/season_windows.py reads rules/calendar.yaml; no window is written in code.

    f = tmp_path / "calendar.yaml"
    f.write_text(
        "ml_windows:\n"
        "  - {nso_season: spring, calendar_region: north_central, start: [3, 0], end: [5, 0], source_ids: [R-X]}\n"
        "excluded:\n"
        "  - {nso_season: autumn, calendar_region: mekong, reason: test}\n",
        encoding="utf-8",
    )
    cal = load_calendar(f)
    assert season_window("spring", "north_central", 2010, calendar=cal) == (date(2010, 3, 1), date(2010, 5, 31))
    with pytest.raises(ValueError, match=r"no NSO calendar entry for winter rice"):
        season_window("winter", "north_central", 2010, calendar=cal)


def test_rules_calendar_entries_cite_a_source():

    cal = load_calendar()
    assert cal.windows
    assert all(w["source_ids"] for w in cal.raw["ml_windows"])


def test_calendar_refuses_a_repeated_pair_and_an_unknown_region():
    # Source: 05-DATA-CONTRACTS section 6b: "one entry per NSO rice season and calendar region", and the six region codes
    # red_river_delta, northern_mountains, north_central, central_coast, highlands_southeast, mekong
    w = {"nso_season": "spring", "calendar_region": "mekong", "start": [11, -1], "end": [4, 0], "source_ids": ["R-V05"]}
    with pytest.raises(ValueError, match=r"spring.*mekong"):
        Calendar({"ml_windows": [w, w]})
    with pytest.raises(ValueError, match="mekongg"):
        Calendar({"ml_windows": [{**w, "calendar_region": "mekongg"}]})
    with pytest.raises(ValueError, match="highland"):
        Calendar({"excluded": [{"nso_season": "autumn", "calendar_region": "highland", "reason": "x"}]})
