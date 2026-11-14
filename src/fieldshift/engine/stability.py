"""Stability blocks of the rice crops of a plan (UI-UX-SPEC §11 Stability; 05-DATA-CONTRACTS §5; 04-TECH-DESIGN §4).

The real NSO anomaly per picked year; the out-of-sample prediction only in the test years of a season whose model is
shown (D-82, D-83), its 80% range only where G4 passed for that season (D-94); min / median / max over the exact
non-null anomalies, each rounded once (D-95, D-156), and the years whose real value equals the minimum.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fieldshift.engine.rules import RISK_TABLE, RiskRow, RiskSeason
from fieldshift.engine.schemas import (
    SUMMARY_MIN_YEARS,
    CropSpan,
    GateRow,
    Province,
    Range80,
    SeasonCode,
    Stability,
    StabilityYear,
    Summary,
    Text,
    YearSpan,
)
from fieldshift.engine.values import ENGINE_ID, percent, percent_value

RICE = "rice"  # crop id of rules/crops.yaml and `crop` of risk_table.json rows (05-DATA-CONTRACTS §5, §6)
RISK_UNITS: dict[Province, str] = {"nghe_an": "Nghe An"}  # the province's `unit_id` in artifacts/risk_table.json


@dataclass(frozen=True)
class RiceHistory:
    """The province's rice rows of risk_table.json by (season, year), the model status and the G4 verdicts."""

    rows: dict[tuple[SeasonCode, int], RiskRow]
    seasons: dict[SeasonCode, RiskSeason]
    g4_passed: frozenset[SeasonCode]
    test_years: YearSpan
    scope: Text


def rice_history(
    province: Province,
    rows: list[RiskRow],
    seasons: dict[SeasonCode, RiskSeason],
    gates: list[GateRow],
    test_years: YearSpan,
    scope: Text,
) -> RiceHistory:
    by_key: dict[tuple[SeasonCode, int], RiskRow] = {}
    for row in rows:
        if (row.unit_id, row.crop) != (RISK_UNITS[province], RICE):
            continue
        if (row.season, row.year) in by_key:
            raise ValueError(f"artifacts/{RISK_TABLE}: two rows for {row.unit_id} {row.season} {row.year}")
        by_key[(row.season, row.year)] = row
    g4_passed = frozenset(g.season for g in gates if g.gate == "G4" and g.passed)
    return RiceHistory(by_key, seasons, g4_passed, test_years, scope)


def stability_year(row: RiskRow, shown: bool, g4_passed: bool, test_years: YearSpan) -> StabilityYear:
    predicted = shown and row.anom_oos is not None and test_years.first <= row.year <= test_years.last
    prediction = percent_value(row.anom_oos, row.anom_oos_source_ids) if predicted else None
    low = percent_value(row.oos_low_80, row.anom_oos_source_ids)
    high = percent_value(row.oos_high_80, row.anom_oos_source_ids)
    with_range = prediction is not None and g4_passed and low is not None and high is not None
    return StabilityYear(
        year=row.year,
        real=percent_value(row.anom_history, row.anom_history_source_ids),
        oos_prediction=prediction,
        range_80=Range80(low=low, high=high) if with_range else None,
    )


def summary(rows: list[RiskRow]) -> Summary | None:
    """Min / median / max of the exact non-null anomalies; the median of an even count is the mean of the two middle
    values, rounded once (D-156); None from fewer than two values (D-95)."""
    real = [r for r in rows if r.anom_history is not None]
    if len(real) < SUMMARY_MIN_YEARS:
        return None
    exact = sorted(Decimal(str(r.anom_history)) for r in real)
    middle = len(exact) // 2
    median = exact[middle] if len(exact) % 2 else (exact[middle - 1] + exact[middle]) / 2
    ids = list(dict.fromkeys([*(sid for r in real for sid in r.anom_history_source_ids), ENGINE_ID]))
    return Summary(min=percent(exact[0], ids), median=percent(median, ids), max=percent(exact[-1], ids))


def stability(span: CropSpan, label: Text, years: list[int], history: RiceHistory) -> Stability:
    """The Stability block of one rice crop over the picked years."""
    if span.season not in history.seasons:
        raise ValueError(f"artifacts/{RISK_TABLE}: no model status for season {span.season}")
    missing = [y for y in years if (span.season, y) not in history.rows]
    if missing:
        raise ValueError(f"artifacts/{RISK_TABLE}: no rice row for season {span.season} years {missing}")
    rows = [history.rows[(span.season, y)] for y in years]
    status = history.seasons[span.season].model_status
    shown, g4_passed = status == "shown", span.season in history.g4_passed
    per_year = [stability_year(row, shown, g4_passed, history.test_years) for row in rows]
    top = summary(rows)
    worst = [] if top is None else [r.year for r in per_year if r.real is not None and r.real.value == top.min.value]
    return Stability(
        crop_key=span.crop_key,
        season=span.season,
        label=label,
        model_status=status,
        years_count=sum(r.real is not None for r in per_year),
        scope=history.scope,
        per_year=per_year,
        summary=top,
        worst_years=worst,
    )
