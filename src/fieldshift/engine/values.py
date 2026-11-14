"""Artifact numbers to display values (D-95: computed shares as whole percent; the engine rounds, 04-TECH-DESIGN §3)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from fieldshift.engine.schemas import Text, Value

PERCENT: Text = {"vi": "%", "en": "%"}  # unit "%" in both languages (05-DATA-CONTRACTS §4b)


def whole_percent(fraction: float) -> str:
    """Fraction x 100 rounded half up to an integer (decimal.ROUND_HALF_UP, D-102); str() keeps 0.995 from binary drift."""
    return str((Decimal(str(fraction)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def share_value(row: dict) -> Value | None:
    """One hazard_labels.json row as its share Value (05-DATA-CONTRACTS §4b API conversion); null stays null."""
    if row["share_farmland"] is None:
        return None
    return Value(
        value=whole_percent(row["share_farmland"]),
        unit=PERCENT,
        source_ids=[row["threshold_source_id"], *row["values_source_ids"], row["computed_by"]],
    )
