"""Build the app's data files from real inputs only. Nothing is invented; a missing input stops the build.

Run from the repository root (it provides the fieldshift package, the cached NASA POWER files, the committed farmland
weights, the geoBoundaries file and the model artifacts):

    PYTHONPATH=src .venv/Scripts/python web/pipeline/build_data.py web/src/data/generated

Inputs
- NASA POWER daily point data, 1990-2024, for the five Nghe An cells with a MODIS farmland weight (R-N01, R-N02),
  fetched by pipeline/fetch_nghe_an.py.
- data/processed/cell_weights.csv (MODIS farmland weights per POWER cell).
- artifacts/risk_table.json, metrics.json, gates.json (NSO yield anomalies and the primary-test results, E-012).
- data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson (geoBoundaries gbOpen, public domain per its metadata).

Crop field times are the sowing and first harvest dates reported by the P-02 trial (Tables 1, 5 and 9). Rules are the
QD 18/2021/QD-TTg risk-level rules as implemented in fieldshift.features.hazards (level 1 or higher).
"""

import csv
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import box, shape

from fieldshift.data.power import PowerRequest, fetch_daily
from fieldshift.features.hazards import RULES, cell_rules, drought_months, monthly_climatology

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
YEARS = list(range(1995, 2025))
START, END = date(1990, 1, 1), date(2024, 12, 31)
CLIM = (1991, 2020)
HOT_DAY_C = 35.0  # lower bound of QD 18/2021 Art. 47.1 a (35 included), for the measured hot-day count
COLD_DAY_C = 13.0  # upper bound of Art. 53.1 a (13 included), for the measured cold-day count
MIN_RING_AREA = 0.002  # square degrees; smaller outline islands are dropped from the drawing

# P-02 field times (MM-DD sowing, MM-DD first reported harvest), Tables 1, 5 and 9 of the trial report.
CROPS = {
    "cc1_peanut": ("01-18", "05-12"),
    "cc1_mung": ("06-10", "08-30"),
    "cc1_maize": ("09-01", "12-22"),
    "cc2_chili": ("01-17", "06-25"),
    "cc2_soy": ("06-10", "09-09"),
    "cc2_biomaize": ("09-10", "11-26"),
    "cc3_maize": ("01-17", "05-04"),
    "cc3_sesame": ("06-10", "09-04"),
    "cc3_pumpkin": ("09-05", "11-21"),
    "cc4_biomaize1": ("01-17", "04-05"),
    "cc4_biomaize2": ("06-10", "08-20"),
    "cc4_sweetpotato": ("09-05", "12-02"),
    "cc5_rice": ("01-17", "05-17"),
    "cc5_blackbean": ("06-06", "08-25"),
    "cc5_sweetpotato": ("08-15", "12-10"),
}


def months_of(windows):
    out = set()
    for s, e in windows:
        out.update(range(int(s[:2]), int(e[:2]) + 1))
    return sorted(out)


def field_days(year, windows):
    days = set()
    for s, e in windows:
        days.update(pd.date_range(date(year, int(s[:2]), int(s[3:])), date(year, int(e[:2]), int(e[3:])), freq="D"))
    return pd.DatetimeIndex(sorted(days))


def as_dated(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


with open("data/processed/cell_weights.csv", newline="") as f:
    rows = [r for r in csv.DictReader(f) if r["province_nso"] == "Nghe An"]
cells = [
    {"id": r["cell_id"], "lat": float(r["lat"]), "lon": float(r["lon"]), "weight": float(r["farmland_weight"])}
    for r in rows
]
cells.sort(key=lambda c: (-c["lat"], c["lon"]))

daily = {}
for c in cells:
    main, _ = fetch_daily(PowerRequest(c["lat"], c["lon"], START, END), "data/raw/power")
    t2m, _ = fetch_daily(PowerRequest(c["lat"], c["lon"], START, END, parameters=("T2M",)), "data/raw/power_t2m")
    df = as_dated(main).join(as_dated(t2m)[["T2M"]], how="inner")
    if df[["PRECTOTCORR", "T2M_MAX", "T2M", "GWETROOT"]].isna().any().any():
        raise SystemExit(f"missing values in the POWER series of cell {c['id']}")
    daily[c["id"]] = df

weights = {c["id"]: c["weight"] for c in cells}
wsum = sum(weights.values())
clim = {cid: monthly_climatology(df["PRECTOTCORR"]) for cid, df in daily.items()}


def shares(windows):
    """Per rule: list over YEARS of the share of Nghe An farmland where the rule was met (level 1 or higher)."""
    months = months_of(windows)
    out = {r: [] for r in RULES}
    per_cell = {r: {cid: [] for cid in daily} for r in RULES}
    for y in YEARS:
        met = {cid: cell_rules(df, y, windows, months, clim[cid]) for cid, df in daily.items()}
        for r in RULES:
            out[r].append(round(sum(weights[cid] for cid in daily if met[cid][r]) / wsum, 4))
            for cid in daily:
                per_cell[r][cid].append(bool(met[cid][r]))
    return out, per_cell, months


all_windows = list(CROPS.values())
year_level, cell_level, year_months = shares(all_windows)
crop_level = {key: shares([w])[0] for key, w in CROPS.items()}

# Measured magnitudes per cell and year over the joined field time, so the 3D view shows real amounts, not a score.
magnitudes = {"max_rain_mm": {}, "hot_days": {}, "cold_days": {}, "drought_months": {}}
for cid, df in daily.items():
    for series in magnitudes.values():
        series[cid] = []
    for y in YEARS:
        win = df.reindex(field_days(y, all_windows))
        magnitudes["max_rain_mm"][cid].append(round(float(win["PRECTOTCORR"].max()), 1))
        magnitudes["hot_days"][cid].append(int((win["T2M_MAX"] >= HOT_DAY_C).sum()))
        magnitudes["cold_days"][cid].append(int((win["T2M"] <= COLD_DAY_C).sum()))
        totals = {}
        for m in year_months:
            mdays = pd.date_range(pd.Timestamp(y, m, 1), pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0), freq="D")
            totals[m] = float(df["PRECTOTCORR"].reindex(mdays).sum())
        magnitudes["drought_months"][cid].append(int(drought_months(pd.Series(totals), clim[cid]).sum()))


# NASA soil wetness (GWETROOT, MERRA-2 model value) per crop: farmland-weighted mean over the field days, and the
# 1991-2020 mean of the same field window.
def weighted_wetness(year, window):
    """Farmland-weighted mean root-zone wetness over one crop's field days in one year."""
    days = field_days(year, [window])
    return sum(weights[cid] * float(df["GWETROOT"].reindex(days).mean()) for cid, df in daily.items()) / wsum


soil = {}
for key, w in CROPS.items():
    values = [round(weighted_wetness(y, w), 3) for y in YEARS]
    normal = round(float(np.mean([weighted_wetness(y, w) for y in range(CLIM[0], CLIM[1] + 1)])), 3)
    soil[key] = {"values": values, "normal_1991_2020": normal}

# Province boundary and the POWER grid around it (0.5 deg latitude x 0.625 deg longitude cells, centred on the points).
gj = json.loads(Path("data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson").read_text(encoding="utf-8"))
feat = next(
    f
    for f in gj["features"]
    if "Nghe An" in f["properties"].get("shapeName", "") or "Nghệ An" in f["properties"].get("shapeName", "")
)
geom = shape(feat["geometry"]).simplify(0.01, preserve_topology=True)
polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
outline = [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in polys if p.area > MIN_RING_AREA]
minx, miny, maxx, maxy = geom.bounds
by_point = {(round(c["lat"], 3), round(c["lon"], 4)): c for c in cells}
grid = []
for lat in np.arange(np.floor(miny * 2) / 2, maxy + 0.5, 0.5):
    for lon in np.arange(np.floor(minx / 0.625) * 0.625, maxx + 0.625, 0.625):
        cell = box(lon - 0.3125, lat - 0.25, lon + 0.3125, lat + 0.25)
        if cell.intersects(geom):
            known = by_point.get((round(float(lat), 3), round(float(lon), 4)))
            grid.append(
                {
                    "id": known["id"] if known else f"{lat:.1f}_{lon:.3f}",
                    "lat": float(lat),
                    "lon": float(lon),
                    "weight": known["weight"] if known else 0.0,
                    "inside_share": round(cell.intersection(geom).area / cell.area, 3),
                }
            )

# Model artifacts (copied in part, unchanged values).
art = Path("artifacts")
risk = json.loads((art / "risk_table.json").read_text(encoding="utf-8"))
na_rows = [r for r in risk["rows"] if r["unit_id"] == "Nghe An" and r["crop"] == "rice"]
history = {}
for s in ("spring", "summer_autumn", "winter"):
    rr = {r["year"]: r for r in na_rows if r["season"] == s}
    history[s] = {
        "anom_history": [rr[y]["anom_history"] if y in rr else None for y in YEARS],
        "anom_oos": [rr[y]["anom_oos"] if y in rr else None for y in YEARS],
        "oos_low_80": [rr[y]["oos_low_80"] if y in rr else None for y in YEARS],
        "oos_high_80": [rr[y]["oos_high_80"] if y in rr else None for y in YEARS],
    }
metrics = json.loads((art / "metrics.json").read_text(encoding="utf-8"))
keep = {"national", "na_ht_th", "unit:Nghe An"}
metric_rows = [r for r in metrics["metrics"] if r["subset"] in keep and not r["sensitivity"]]
gates = json.loads((art / "gates.json").read_text(encoding="utf-8"))

stamp = datetime.now(UTC).isoformat(timespec="seconds")
common = {"generated_at": stamp, "years": YEARS}
(OUT / "hazards.json").write_text(
    json.dumps(
        {
            **common,
            "rules": list(RULES),
            "cells": cells,
            "year_months": year_months,
            "crops": {k: {"sow": s, "harvest": e} for k, (s, e) in CROPS.items()},
            "year_level": year_level,
            "crop_level": crop_level,
            "cell_level": cell_level,
            "magnitudes": magnitudes,
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
(OUT / "soil.json").write_text(json.dumps({**common, "crops": soil}, ensure_ascii=False), encoding="utf-8")
(OUT / "geo.json").write_text(
    json.dumps(
        {"generated_at": stamp, "outline": outline, "grid": grid, "bounds": [minx, miny, maxx, maxy]},
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
(OUT / "model.json").write_text(
    json.dumps(
        {
            **common,
            "freeze_commit": metrics["freeze_commit"],
            "test_years": metrics["test_years"],
            "seasons": risk["seasons"],
            "history": history,
            "metrics": metric_rows,
            "gates": gates["gates"],
            "weather_claims": metrics["weather_claims"],
            "reports": metrics["reports"],
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
sys.stdout.write(f"written {sorted(p.name for p in OUT.iterdir())}\n")
