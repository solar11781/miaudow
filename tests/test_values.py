"""Tests for the display conversion of computed shares (05-DATA-CONTRACTS §4b API conversion; D-95; D-102).

Expected: the share x 100 rounded half up to an integer (decimal.ROUND_HALF_UP), unit "%" in both languages,
source_ids = [threshold_source_id, values_source_ids..., computed_by], null stays null. Values worked out by hand.
"""

import pytest

from fieldshift.engine.rules import HazardRow
from fieldshift.engine.values import share_value, whole_percent


@pytest.mark.parametrize(
    ("fraction", "shown"),
    [(0.125, "13"), (0.995, "100"), (0.994, "99"), (0.005, "1"), (0.0, "0"), (1.0, "100"), (0.12449, "12")],
)
def test_whole_percent_rounds_half_up(fraction: float, shown: str) -> None:
    assert whole_percent(fraction) == shown


def row(share: float | None) -> HazardRow:
    return HazardRow.model_validate(
        {
            "level": "year",
            "plan_id": None,
            "crop_key": None,
            "season": None,
            "months": [2],
            "field_dates": [["02-01", "03-01"]],
            "year": 1995,
            "rule": "heat",
            "share_farmland": share,
            "n_cells": 7,
            "threshold_source_id": "R-A01",
            "values_source_ids": ["R-N01", "R-N02"],
            "computed_by": "E-019",
        }
    )


def test_a_share_becomes_a_percent_value_with_its_three_sources() -> None:
    value = share_value(row(0.125))
    assert value is not None
    assert value.model_dump() == {
        "value": "13",
        "unit": {"vi": "%", "en": "%"},
        "source_ids": ["R-A01", "R-N01", "R-N02", "E-019"],
    }


def test_a_null_share_stays_null() -> None:
    assert share_value(row(None)) is None
