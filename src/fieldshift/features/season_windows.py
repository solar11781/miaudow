"""Weather windows per rice season and calendar region (D-37, D-38).

Plain words: a harvest number only depends on the weather while that crop was in the field. The statistics office's
own calendar (NSO "Phụ lục 1", source R-V05) gives sowing and harvest months per season and region;
the window runs from the first day of the first sowing month to the last day of the last harvest month. The NSO
statistical year is an agricultural year, so some windows start in the previous calendar year.
"""

from __future__ import annotations

import calendar as _cal
import csv
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from fieldshift.data.nso import REGION_ROWS, canonical_province
from fieldshift.paths import project_root

CALENDAR_FILE = project_root() / "rules" / "calendar.yaml"


class Calendar:
    """Windows read from rules/calendar.yaml (05-DATA-CONTRACTS §6b): (season, region) -> ((month, offset), (month, offset))."""

    def __init__(self, raw: dict) -> None:
        self.raw = raw
        self.windows = {
            (w["nso_season"], w["calendar_region"]): (tuple(w["start"]), tuple(w["end"]))
            for w in raw.get("ml_windows", [])
        }
        self.excluded = {(e["nso_season"], e["calendar_region"]): e["reason"] for e in raw.get("excluded", [])}


@lru_cache(maxsize=8)
def load_calendar(path: Path | str = CALENDAR_FILE) -> Calendar:

    return Calendar(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


NSO_REGION_TO_CALENDAR = {
    "Red River Delta": "red_river_delta",
    "Northern midlands and mountain areas": "northern_mountains",
    "Central Highlands": "highlands_southeast",
    "South East": "highlands_southeast",
    "Mekong River Delta": "mekong",
}
CENTRAL_REGION = "North Central and Central coastal areas"
NORTH_CENTRAL_6 = {"Thanh Hoa", "Nghe An", "Ha Tinh", "Quang Binh", "Quang Tri", "Thua Thien-Hue"}  # D-38


def season_window(season: str, region: str, stat_year: int, calendar: Calendar | None = None) -> tuple[date, date]:
    """(first day, last day) of the weather window for a rice season in a calendar region and statistical year."""
    cal = calendar or load_calendar()
    if (season, region) in cal.excluded:
        raise ValueError(cal.excluded[(season, region)])
    if (season, region) not in cal.windows:
        raise ValueError(f"no NSO calendar entry for {season} rice in {region}")
    (m0, y0), (m1, y1) = cal.windows[(season, region)]
    end_year = stat_year + y1
    return date(stat_year + y0, m0, 1), date(end_year, m1, _cal.monthrange(end_year, m1)[1])


@lru_cache(maxsize=4)
def _nso_regions(raw_csv: str) -> dict[str, str]:
    text = Path(raw_csv).read_bytes().replace(b"\x00", b"").decode("utf-8-sig")
    region, members = None, {}
    for row in csv.reader(text.splitlines()):
        if not row[1:]:  # blank row, or a name without a value
            continue
        name = canonical_province(row[0])
        if name in REGION_ROWS:
            region = name
        elif region is not None and region != "WHOLE COUNTRY":
            members[name] = region
    return members


def calendar_region(province: str, nso_export_csv: Path | str) -> str:
    """Calendar region of a province, from the NSO export's region headers [DATA] and D-38."""
    nso_region = _nso_regions(str(nso_export_csv))[province]
    if nso_region == CENTRAL_REGION:
        return "north_central" if province in NORTH_CENTRAL_6 else "central_coast"
    return NSO_REGION_TO_CALENDAR[nso_region]
