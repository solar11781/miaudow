"""Bare periods of a plan: the days of the year covered by no crop span from `sow_from` to `harvest_to`.

05-DATA-CONTRACTS §7; UI-UX-SPEC §11 `Period` (a period over 31 December is one Period with `from` later than `to`);
days are counted in a 365-day year (D-103, D-104); the schemas already rejected dates that do not exist there.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fieldshift.engine.schemas import REFERENCE_YEAR, CropSpan, Period

YEAR_START = date(REFERENCE_YEAR, 1, 1)
DAYS = 365


def _day(mmdd: str) -> int:
    return (datetime.strptime(f"{REFERENCE_YEAR}-{mmdd}", "%Y-%m-%d").date() - YEAR_START).days


def _mmdd(day: int) -> str:
    return (YEAR_START + timedelta(days=day)).strftime("%m-%d")


def bare_periods(calendar: list[CropSpan]) -> list[Period]:
    """Bare periods in date order; [] when the plan has no dates (P-03)."""
    undated = [s.crop_key for s in calendar if s.sow_from is None]
    if len(undated) == len(calendar):
        return []
    if undated:
        raise ValueError(f"crop spans without dates in a plan with dates: {undated}")
    covered = [False] * DAYS
    for span in calendar:
        for day in range(_day(span.sow_from), _day(span.harvest_to) + 1):
            covered[day] = True
    starts = [d for d in range(DAYS) if not covered[d] and covered[d - 1]]  # covered[-1] is 31 December
    periods = []
    for start in starts:
        end = start
        while not covered[(end + 1) % DAYS]:
            end = (end + 1) % DAYS
        periods.append(Period(from_=_mmdd(start), to=_mmdd(end)))
    return periods
