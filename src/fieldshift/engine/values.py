"""Artifact numbers to display values (D-95: computed shares as whole percent; the engine rounds, 04-TECH-DESIGN §3)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from fieldshift.engine.rules import HazardRow
from fieldshift.engine.schemas import SourceId, Text, Value

PERCENT: Text = {"vi": "%", "en": "%"}  # unit "%" in both languages (05-DATA-CONTRACTS §4b)
MM: Text = {"vi": "mm", "en": "mm"}
NO_UNIT: Text = {"vi": "", "en": ""}  # a correlation has no unit
ENGINE_ID: SourceId = "E-022"  # engine arithmetic on cited values: sums, counts, min / median / max (D-158)


def whole_percent(fraction: float | Decimal) -> str:
    """Fraction x 100 rounded half up to an integer (decimal.ROUND_HALF_UP, D-102); str() keeps 0.995 from binary drift.

    An exact Decimal (a median of two values, D-156) is rounded once here; a result of minus zero is shown as "0".
    """
    return half_up(Decimal(str(fraction)) * 100, 0)


def half_up(number: float | Decimal, places: int) -> str:
    """A number rounded half up (decimal.ROUND_HALF_UP, D-102) to `places` decimals; str() keeps binary drift out."""
    shown = Decimal(str(number)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return str(abs(shown) if shown == 0 else shown)


def percent(fraction: float | Decimal, source_ids: list[SourceId]) -> Value:
    """A fraction as a whole-percent Value with its sources."""
    return Value(value=whole_percent(fraction), unit=PERCENT, source_ids=source_ids)


def percent_value(fraction: float | Decimal | None, source_ids: list[SourceId]) -> Value | None:
    """A fraction as a whole-percent Value with its sources; null stays null."""
    return None if fraction is None else percent(fraction, source_ids)


def share_value(row: HazardRow) -> Value | None:
    """One hazard_labels.json row as its share Value (05-DATA-CONTRACTS §4b API conversion); null stays null."""
    return percent_value(row.share_farmland, [row.threshold_source_id, *row.values_source_ids, row.computed_by])
