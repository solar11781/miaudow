"""Rows of artifacts/hazard_labels.json: official risk-level labels per P-02 plan crop and per year (05-DATA-CONTRACTS
§4b; 03-ML-SPEC §5a; D-79, D-95, D-97).

Plain words: for each crop of the P-02 trial plans and each past year, the share of Nghệ An farmland where each
official rule of features/hazards.py was met while that crop was in the field; the year rows join the field time of
all P-02 crops of the calendar year (Screen 2).
"""

from collections.abc import Iterable

import pandas as pd

from fieldshift.features.hazards import RULES, cell_rules, farmland_share, monthly_climatology

P02_PLANS = ("usual", "cc1", "cc2", "cc3", "cc4")  # §4b: no usual_p03 (P-03 reports no dates)
YEARS = range(1995, 2025)  # §4b: year 1995..2024
THRESHOLD_SOURCE_ID = "R-A01"  # §4b: QĐ 18/2021/QĐ-TTg
VALUES_SOURCE_IDS = ["R-N01", "R-N02"]  # §4b: NASA POWER values, MODIS farmland weights
COMPUTED_BY = "E-019"  # EXPERIMENTS: the computation of hazard_labels.json


def plan_crops(plans: list[dict]) -> list[dict]:
    """Field time of each P-02 plan crop: sowing date to first reported harvest date, and the months between (D-97)."""
    crops = []
    for plan in plans:
        if plan["id"] not in P02_PLANS:
            continue
        for span in plan["seasons"]:
            sow, harvest = span["sow_from"], span["harvest_from"]
            if span["sow_to"] != sow:  # P-02 reports one sowing date per crop (03-ML-SPEC section 5a)
                raise ValueError(f"{span['crop_key']}: sowing range {sow}..{span['sow_to']}, expected one sowing date")
            crops.append(
                {
                    "plan_id": plan["id"],
                    "crop_key": span["crop_key"],
                    "season": span["season"],
                    "field_dates": [(sow, harvest)],
                    "months": list(range(int(sow[:2]), int(harvest[:2]) + 1)),
                }
            )
    return crops


def year_window(crops: list[dict]) -> dict:
    """The union of the field dates and months of all crops (the year rows of §4b)."""
    return {
        "field_dates": sorted({pair for crop in crops for pair in crop["field_dates"]}),
        "months": sorted({m for crop in crops for m in crop["months"]}),
    }


def hazard_label_rows(
    crops: list[dict], cells: dict[tuple, pd.DataFrame], weights: dict[tuple, float], years: Iterable[int] = YEARS
) -> list[dict]:
    """One row per level x crop x year x rule; cells: daily PRECTOTCORR, T2M_MAX, T2M per weighted cell."""
    clim = {c: monthly_climatology(cells[c]["PRECTOTCORR"]) for c in weights}
    year_keys = {"level": "year", "plan_id": None, "crop_key": None, "season": None}
    windows = [({"level": "crop", **{k: c[k] for k in ("plan_id", "crop_key", "season")}}, c) for c in crops]
    windows.append((year_keys, year_window(crops)))
    rows = []
    for keys, window in windows:
        for year in years:
            met = {}
            for c in weights:
                try:
                    met[c] = cell_rules(cells[c], year, window["field_dates"], window["months"], clim[c])
                except (KeyError, ValueError) as err:
                    raise ValueError(f"{keys['crop_key'] or 'year row'} {year} cell {c}: {err}") from err
            for rule in RULES:
                rows.append(
                    {
                        **keys,
                        "months": window["months"],
                        "field_dates": [list(pair) for pair in window["field_dates"]],
                        "year": year,
                        "rule": rule,
                        "share_farmland": farmland_share({c: m[rule] for c, m in met.items()}, weights),
                        "n_cells": len(weights),
                        "threshold_source_id": THRESHOLD_SOURCE_ID,
                        "values_source_ids": VALUES_SOURCE_IDS,
                        "computed_by": COMPUTED_BY,
                    }
                )
    return rows
