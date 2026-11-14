"""Tests for bare periods (written before the code). Placeholder dates on the first or last day of a month.

Spec: 05-DATA-CONTRACTS §7: the engine derives `bare_periods` as the days of the year covered by no span from
`sow_from` to `harvest_to`; a bare period that runs over 31 December is one `Period` with `from` later than `to`;
UI-UX-SPEC §11 Plan.bare_periods: [] when dates are missing; 04-TECH-DESIGN §4 (FR-18); days counted out of 365
(D-103, D-104). Expected periods are worked out by hand from the spans.
"""

import pytest

from fieldshift.engine.bare_periods import bare_periods
from fieldshift.engine.schemas import CropSpan

T = {"vi": "[x]", "en": "[x]"}


def spans(*dates: tuple[str, str] | None) -> list[CropSpan]:
    out = []
    for i, d in enumerate(dates):
        sow, harvest = d or (None, None)
        out.append(
            CropSpan(
                crop_key=f"cc1_spring_crop{i}",
                crop_id=f"crop{i}",
                crop=T,
                variety=None,
                season="spring",
                sow_from=sow,
                sow_to=sow,
                harvest_from=harvest,
                harvest_to=harvest,
                source_ids=["R-P02"],
            )
        )
    return out


def periods(found: list) -> list[tuple[str, str]]:
    return [(p.from_, p.to) for p in found]


@pytest.mark.parametrize(
    ("dates", "expected"),
    [
        ([("02-01", "06-30")], [("07-01", "01-31")]),  # one span: the rest of the year wraps over 31 December
        ([("02-01", "05-31"), ("07-01", "10-31")], [("06-01", "06-30"), ("11-01", "01-31")]),  # a gap between spans
        ([("02-01", "06-30"), ("06-01", "12-31")], [("01-01", "01-31")]),  # overlapping spans; 31 December covered
        ([("01-01", "05-31"), ("07-01", "12-31")], [("06-01", "06-30")]),  # both year ends covered: no wrap
        ([("02-01", "05-31"), ("06-01", "08-31")], [("09-01", "01-31")]),  # spans that touch leave no gap
        ([("01-01", "12-31")], []),  # the whole year covered
    ],
)
def test_bare_periods_are_the_days_no_span_covers(dates: list, expected: list) -> None:
    assert periods(bare_periods(spans(*dates))) == expected


def test_no_dates_give_no_bare_periods() -> None:
    assert bare_periods(spans(None, None)) == []  # P-03: no dates reported
    assert bare_periods([]) == []


def test_a_plan_with_some_dates_missing_fails_loudly() -> None:
    with pytest.raises(ValueError, match="crop1"):
        bare_periods(spans(("02-01", "05-31"), None))


def test_a_date_outside_a_365_day_year_fails_loudly() -> None:
    with pytest.raises(ValueError, match="02-29"):
        bare_periods(spans(("02-01", "02-29")))
