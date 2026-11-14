"""Build every file of data/canonical/ from real inputs only. Nothing is invented; a missing input stops the build.

Run from the project root:

    .venv\\Scripts\\python pipeline/build_canonical.py

Inputs
- NASA POWER daily point data, 1990-2024, for the five Nghệ An cells with a MODIS farmland weight (R-N01, R-N02):
  data/raw/power/ and data/raw/power_t2m/ (cached API responses, fill value -999 read as missing).
- data/reference/cell_weights_nghe_an.csv (MODIS farmland weight per POWER cell, R-N02).
- data/reference/risk_table.json, metrics.json, gates.json (NSO yield anomalies and the primary-test results, E-012),
  hazard_labels.json (E-019) and soil_wetness.json (E-020), copied from the team's Miaudow repository.
- data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson (geoBoundaries gbOpen).
- data/rules/*.yaml (the team rulebook) and api/rules/rotations.yaml (the audited plan text, via scripts/sync_rotations.py).
- Optional, when another pipeline has fetched them: data/raw/chirps_v3/ and data/raw/modis_mod13q1/ (each with a
  MANIFEST.json), and data/raw/documents/*/chunks.jsonl.

Outputs (data/canonical/)
- hazards.json, soil.json, geo.json, model.json: the same structure and values as web/pipeline/build_data.py writes
  (pipeline/tests/test_canonical_identity.py proves it; only generated_at differs).
- climate.json, catalog.json, rotations.generated.json, passages.json.

Crop field times are the sowing and first harvest dates reported by the P-02 trial (Tables 1, 5 and 9). Rules are the
QĐ 18/2021/QĐ-TTg risk-level rules as implemented in miaudow_api.science.hazards (level 1 or higher).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))

from miaudow_api import knowledge  # noqa: E402
from miaudow_api.contracts import CompareRequest, Dataset, MethodDef, SourceFact, Text  # noqa: E402
from miaudow_api.science.hazards import (  # noqa: E402
    CLIM_YEARS,
    DROUGHT_DEFICIT,
    RULES,
    cell_rules,
    drought_months,
    monthly_climatology,
)
from miaudow_api.science.power import (  # noqa: E402
    SOURCE_URL,
    check_calendar,
    days_in_month,
    load_cached_cells,
    sha256_of_files,
)

DATA = ROOT / "data"
RAW = DATA / "raw"
REF = DATA / "reference"
RULES_DIR = DATA / "rules"
OUT = DATA / "canonical"

YEARS = list(range(1995, 2025))
CLIMATE_YEARS = list(range(1991, 2025))
FIRST_DAILY_YEAR, LAST_DAILY_YEAR = 1990, 2024
CLIM = (1991, 2020)
HOT_DAY_C = 35.0  # lower bound of QĐ 18/2021 Art. 47.1 a (35 included), for the measured hot-day count
COLD_DAY_C = 13.0  # upper bound of Art. 53.1 a (13 included), for the measured cold-day count
DRY_DAY_MM = 1.0  # ETCCDI CDD: a dry day has PRECTOTCORR < 1 mm (Zhang et al. 2011, R-A10)
MIN_RING_AREA = 0.002  # square degrees; smaller outline islands are dropped from the drawing
NEEDED = ["PRECTOTCORR", "T2M_MAX", "T2M", "GWETROOT"]

# P-02 field times (MM-DD sowing, MM-DD first reported harvest), Tables 1, 5 and 9 of the trial report. The keys are
# the web app's crop keys; TEAM_CROP_KEY maps each to the crop_key of data/rules/rotations.yaml, and the build checks
# that the dates are the team's sow_from and harvest_from.
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
TEAM_CROP_KEY = {
    "cc1_peanut": "cc1_spring_peanut",
    "cc1_mung": "cc1_summer_autumn_mung_bean",
    "cc1_maize": "cc1_autumn_winter_maize_grain",
    "cc2_chili": "cc2_spring_chili",
    "cc2_soy": "cc2_summer_autumn_soybean",
    "cc2_biomaize": "cc2_autumn_winter_maize_biomass",
    "cc3_maize": "cc3_spring_maize_grain",
    "cc3_sesame": "cc3_summer_autumn_black_sesame",
    "cc3_pumpkin": "cc3_autumn_winter_pumpkin",
    "cc4_biomaize1": "cc4_spring_maize_biomass",
    "cc4_biomaize2": "cc4_summer_autumn_maize_biomass",
    "cc4_sweetpotato": "cc4_autumn_winter_sweet_potato",
    "cc5_rice": "usual_spring_rice",
    "cc5_blackbean": "usual_summer_autumn_black_bean",
    "cc5_sweetpotato": "usual_autumn_winter_sweet_potato",
}


class BuildError(SystemExit):
    """Stops the build with a plain message (no partial canonical layer is ever presented as complete)."""


def fail(message: str) -> None:
    raise BuildError(f"build_canonical: {message}")


# ---------------------------------------------------------------- inputs


def load_cells() -> list[dict]:
    with open(REF / "cell_weights_nghe_an.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["province_nso"] == "Nghe An"]
    if not rows:
        fail("no Nghe An rows in data/reference/cell_weights_nghe_an.csv")
    cells = [
        {"id": r["cell_id"], "lat": float(r["lat"]), "lon": float(r["lon"]), "weight": float(r["farmland_weight"])}
        for r in rows
    ]
    cells.sort(key=lambda c: (-c["lat"], c["lon"]))
    return cells


def load_daily(cells: list[dict]) -> tuple[dict[str, pd.DataFrame], dict]:
    cached = load_cached_cells(RAW / "power", RAW / "power_t2m")
    daily, files, versions, sources, units = {}, [], set(), set(), {}
    for c in cells:
        key = (round(c["lat"], 6), round(c["lon"], 6))
        if key not in cached:
            fail(f"no cached POWER file for weighted cell {c['id']}")
        cell = cached[key]
        df = cell.frame.sort_index()
        if df[NEEDED].isna().any().any():
            fail(f"missing values in the POWER series of cell {c['id']}")
        problems = check_calendar(df.index, FIRST_DAILY_YEAR, LAST_DAILY_YEAR)
        if problems:
            fail(f"calendar problems in cell {c['id']}: {problems[:5]}")
        daily[c["id"]] = df
        files.extend(cell.files)
        versions.add(cell.api_version)
        sources.update(cell.sources)
        units.update(cell.units)
    meta = {
        "files": files,
        "sha256": sha256_of_files(files),
        "api_versions": sorted(v for v in versions if v),
        "sources": sorted(sources),
        "units": units,
    }
    return daily, meta


def check_team_dates() -> None:
    plans = yaml.safe_load((RULES_DIR / "rotations.yaml").read_text(encoding="utf-8"))
    seasons = {s["crop_key"]: s for p in plans for s in p["seasons"]}
    for web_key, (sow, harvest) in CROPS.items():
        s = seasons.get(TEAM_CROP_KEY[web_key])
        if s is None or (s["sow_from"], s["harvest_from"]) != (sow, harvest):
            fail(f"crop {web_key}: field dates differ from data/rules/rotations.yaml")


# ---------------------------------------------------------------- web parity files (port of web/pipeline/build_data.py)


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


def build_hazards(cells, daily, weights, clim):
    wsum = sum(weights.values())

    def shares(windows):
        """Per rule: list over YEARS of the share of Nghệ An farmland where the rule was met (level 1 or higher)."""
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
    return {
        "years": YEARS,
        "rules": list(RULES),
        "cells": cells,
        "year_months": year_months,
        "crops": {k: {"sow": s, "harvest": e} for k, (s, e) in CROPS.items()},
        "year_level": year_level,
        "crop_level": crop_level,
        "cell_level": cell_level,
        "magnitudes": magnitudes,
    }


def build_soil(daily, weights):
    wsum = sum(weights.values())

    def weighted_wetness(year, window):
        days = field_days(year, [window])
        return sum(weights[cid] * float(df["GWETROOT"].reindex(days).mean()) for cid, df in daily.items()) / wsum

    soil = {}
    for key, w in CROPS.items():
        values = [round(weighted_wetness(y, w), 3) for y in YEARS]
        normal = round(float(np.mean([weighted_wetness(y, w) for y in range(CLIM[0], CLIM[1] + 1)])), 3)
        soil[key] = {"values": values, "normal_1991_2020": normal}
    return {"years": YEARS, "crops": soil}


def build_geo(cells):
    path = RAW / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"
    gj = json.loads(path.read_text(encoding="utf-8"))
    feat = next(
        (
            f
            for f in gj["features"]
            if "Nghe An" in f["properties"].get("shapeName", "") or "Nghệ An" in f["properties"].get("shapeName", "")
        ),
        None,
    )
    if feat is None:
        fail("no Nghệ An feature in the geoBoundaries file")
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
    return {"outline": outline, "grid": grid, "bounds": [minx, miny, maxx, maxy]}


def build_model():
    risk = json.loads((REF / "risk_table.json").read_text(encoding="utf-8"))
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
    metrics = json.loads((REF / "metrics.json").read_text(encoding="utf-8"))
    keep = {"national", "na_ht_th", "unit:Nghe An"}
    metric_rows = [r for r in metrics["metrics"] if r["subset"] in keep and not r["sensitivity"]]
    gates = json.loads((REF / "gates.json").read_text(encoding="utf-8"))
    return {
        "years": YEARS,
        "freeze_commit": metrics["freeze_commit"],
        "test_years": metrics["test_years"],
        "seasons": risk["seasons"],
        "history": history,
        "metrics": metric_rows,
        "gates": gates["gates"],
        "weather_claims": metrics["weather_claims"],
        "reports": metrics["reports"],
    }


# ---------------------------------------------------------------- climate.json


def longest_true_run(mask) -> int:
    best = run = 0
    for flag in np.asarray(mask, dtype=bool):
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def r1(v: float | None) -> float | None:
    return None if v is None else round(float(v), 1)


def cell_year(df: pd.DataFrame, year: int, normal: pd.Series) -> dict:
    """One cell and one calendar year. A month with any missing day has no total (null); nothing is filled."""
    totals: list[float | None] = []
    for m in range(1, 13):
        idx = pd.date_range(date(year, m, 1), date(year, m, days_in_month(year, m)), freq="D")
        vals = df["PRECTOTCORR"].reindex(idx)
        totals.append(None if vals.isna().any() else float(vals.sum()))
    year_idx = pd.date_range(date(year, 1, 1), date(year, 12, 31), freq="D")
    win = df.reindex(year_idx)
    missing = {v: int(win[v].isna().sum()) for v in ("PRECTOTCORR", "T2M_MAX", "T2M")}
    complete = [(m + 1, t) for m, t in enumerate(totals) if t is not None]
    flags = drought_months(pd.Series(dict(complete)), normal) if complete else pd.Series(dtype=bool)
    return {
        "monthly_rain_mm": totals,
        "annual_rain_mm": None if any(t is None for t in totals) else float(sum(totals)),
        "hot_days": None if missing["T2M_MAX"] else int((win["T2M_MAX"] >= HOT_DAY_C).sum()),
        "cold_days": None if missing["T2M"] else int((win["T2M"] <= COLD_DAY_C).sum()),
        "longest_dry_spell_days": None if missing["PRECTOTCORR"] else longest_true_run(win["PRECTOTCORR"] < DRY_DAY_MM),
        "drought_rain_months": [int(m) for m, f in flags.items() if f],
        "missing_days": missing,
    }


def finish(raw: dict, normal: list[float]) -> dict:
    """Round for display and add anomalies against the 1991-2020 monthly normal (computed from unrounded values)."""
    totals = raw["monthly_rain_mm"]
    return {
        "monthly_rain_mm": [r1(t) for t in totals],
        "anomaly_mm": [None if t is None else r1(t - n) for t, n in zip(totals, normal, strict=True)],
        "anomaly_pct": [None if t is None else r1((t - n) / n * 100.0) for t, n in zip(totals, normal, strict=True)],
        "annual_rain_mm": r1(raw["annual_rain_mm"]),
        "hot_days": raw["hot_days"] if isinstance(raw["hot_days"], int) else r1(raw["hot_days"]),
        "cold_days": raw["cold_days"] if isinstance(raw["cold_days"], int) else r1(raw["cold_days"]),
        "longest_dry_spell_days": raw["longest_dry_spell_days"]
        if isinstance(raw["longest_dry_spell_days"], int)
        else r1(raw["longest_dry_spell_days"]),
        "drought_rain_months": raw["drought_rain_months"],
        "missing_days": raw["missing_days"],
    }


def weighted(values: list, weights: list[float]) -> float | None:
    """Farmland-weighted mean; null when any cell is null (never re-weighted over the cells that remain)."""
    if any(v is None for v in values):
        return None
    return sum(w * v for w, v in zip(weights, values, strict=True)) / sum(weights)


def build_climate(cells, daily, clim, power_meta, chirps):
    ids = [c["id"] for c in cells]
    w = [c["weight"] for c in cells]
    normal_cells = {cid: [float(clim[cid][m]) for m in range(1, 13)] for cid in ids}
    normal_w = [weighted([normal_cells[cid][m] for cid in ids], w) for m in range(12)]
    per_cell, farm = {cid: {} for cid in ids}, {}
    for y in CLIMATE_YEARS:
        raws = {cid: cell_year(daily[cid], y, clim[cid]) for cid in ids}
        for cid in ids:
            per_cell[cid][str(y)] = finish(raws[cid], normal_cells[cid])
        totals = [weighted([raws[cid]["monthly_rain_mm"][m] for cid in ids], w) for m in range(12)]
        complete = {m + 1: t for m, t in enumerate(totals) if t is not None}
        flags = drought_months(pd.Series(complete), pd.Series(dict(enumerate(normal_w, start=1)))) if complete else {}
        farm[str(y)] = finish(
            {
                "monthly_rain_mm": totals,
                "annual_rain_mm": None if any(t is None for t in totals) else sum(totals),
                "hot_days": weighted([raws[cid]["hot_days"] for cid in ids], w),
                "cold_days": weighted([raws[cid]["cold_days"] for cid in ids], w),
                "longest_dry_spell_days": weighted([raws[cid]["longest_dry_spell_days"] for cid in ids], w),
                "drought_rain_months": [int(m) for m, f in dict(flags).items() if f],
                "missing_days": {
                    v: sum(raws[cid]["missing_days"][v] for cid in ids) for v in ("PRECTOTCORR", "T2M_MAX", "T2M")
                },
            },
            normal_w,
        )
    leap = [y for y in CLIMATE_YEARS if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)]
    for cid in ids:
        for y in leap:
            if pd.Timestamp(y, 2, 29) not in daily[cid].index:
                fail(f"29 February {y} missing in cell {cid}")
    return {
        "dataset_id": "nasa_power_daily",
        "source_id": "R-N01",
        "source_url": SOURCE_URL,
        "source_revision": ", ".join(f"POWER Daily API {v}" for v in power_meta["api_versions"]) or None,
        "version_sha256": power_meta["sha256"],
        "is_forecast": False,
        "is_field_measurement": False,
        "years": CLIMATE_YEARS,
        "baseline_years": list(CLIM_YEARS),
        "thresholds": {
            "hot_day_t2m_max_c_at_least": HOT_DAY_C,
            "cold_day_t2m_c_at_most": COLD_DAY_C,
            "dry_day_rain_mm_below": DRY_DAY_MM,
            "drought_month_deficit_above": DROUGHT_DEFICIT,
        },
        "methods": {
            "monthly_rain_mm": "sum_daily_precip_complete_month",
            "anomaly_mm": "anomaly_vs_1991_2020_normal",
            "anomaly_pct": "anomaly_vs_1991_2020_normal",
            "annual_rain_mm": "sum_complete_months",
            "hot_days": "count_days_t2m_max_ge_35",
            "cold_days": "count_days_t2m_le_13",
            "longest_dry_spell_days": "etccdi_cdd_calendar_year",
            "drought_rain_months": "art48_drought_rain_month",
            "farmland_weighted": "farmland_weighted_mean",
        },
        "cells": cells,
        "leap_years_checked": leap,
        "normal_mm": {
            "farmland_weighted": [r1(v) for v in normal_w],
            "cells": {k: [r1(v) for v in vs] for k, vs in normal_cells.items()},
        },
        "series": {"farmland_weighted": farm, "cells": per_cell},
        "chirps": chirps,
    }


# ---------------------------------------------------------------- optional acquisitions (another pipeline fetches them)


def read_manifest(folder: Path) -> dict | None:
    path = folder / "MANIFEST.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail(f"{path} is not valid JSON: {err}")
    return None


CHIRPS_VALUE_COLUMNS = ("precip_mm", "rain_mm", "precipitation_mm", "value_mm", "chirps_mm", "value")
CHIRPS_CELL_COLUMNS = ("cell_id", "area_id", "cell", "power_cell_id")


def load_chirps() -> dict | None:
    """CHIRPS v3 monthly totals per POWER cell, kept beside POWER (never merged). None when the file is absent."""
    path = RAW / "chirps_v3" / "chirps_v3_monthly_nghe_an.csv"
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail(f"{path} has no rows")
    cols = set(rows[0])
    cell_col = next((c for c in CHIRPS_CELL_COLUMNS if c in cols), None)
    value_col = next((c for c in CHIRPS_VALUE_COLUMNS if c in cols), None)
    if cell_col is None or value_col is None or not {"year", "month"} <= cols:
        return {
            "status": "unreadable",
            "reason": f"columns {sorted(cols)} do not name a cell, year, month and a rain value in mm",
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        }
    series: dict[str, dict[str, list]] = {}
    for r in rows:
        y, m = int(r["year"]), int(r["month"])
        raw = (r[value_col] or "").strip()
        value = None if raw in ("", "nan", "NaN", "null", "None") else float(raw)
        if value is not None and value < 0:
            value = None  # a negative rain total is a fill value, never 0
        series.setdefault(r[cell_col], {}).setdefault(str(y), [None] * 12)[m - 1] = None if value is None else r1(value)
    return {
        "status": "loaded",
        "dataset_id": "chirps_v3_monthly",
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "unit": "mm/month",
        "note": {
            "vi": "Tổng mưa tháng CHIRPS v3 đặt cạnh NASA POWER, không trộn hai nguồn với nhau.",
            "en": "CHIRPS v3 monthly totals kept beside NASA POWER; the two sources are never merged.",
        },
        "cells": series,
    }


# ---------------------------------------------------------------- catalog.json


def t(vi: str, en: str) -> Text:
    return Text(vi=vi, en=en)


def manifest_dataset(dataset_id, title, folder, base: dict) -> Dataset:
    manifest = read_manifest(folder)
    if manifest is None:
        return Dataset(
            **base,
            dataset_id=dataset_id,
            title=title,
            retrieved_at=None,
            source_revision=None,
            version_sha256=None,
            ingestion_status="CONTRACT_ONLY",
            notes=[
                t(
                    "Chưa tải về: chưa có tệp MANIFEST.json khi dựng dữ liệu.",
                    "Not fetched: no MANIFEST.json existed at build time.",
                )
            ],
        )
    status = str(manifest.get("ingestion_status") or manifest.get("status") or "").upper()
    if status not in ("INGESTED", "PARTIAL", "CONTRACT_ONLY", "BLOCKED"):
        status = "PARTIAL"
    notes = [
        t(
            "Trạng thái lấy từ MANIFEST.json của bước tải dữ liệu.",
            "Status read from the MANIFEST.json of the fetch step.",
        )
    ]
    for note in manifest.get("notes", []) if isinstance(manifest.get("notes"), list) else []:
        if isinstance(note, dict) and {"vi", "en"} <= set(note):
            notes.append(t(str(note["vi"]), str(note["en"])))
        elif isinstance(note, str):
            notes.append(t(note, note))
    return Dataset(
        **{
            **base,
            "source_url": manifest.get("source_url") or base["source_url"],
            "license": manifest.get("license") or base["license"],
        },
        dataset_id=dataset_id,
        title=title,
        retrieved_at=manifest.get("retrieved_at"),
        source_revision=manifest.get("source_revision") or manifest.get("version"),
        version_sha256=manifest.get("sha256") or manifest.get("version_sha256"),
        ingestion_status=status,
        notes=notes,
    )


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_datasets(power_meta) -> list[Dataset]:
    na = "Không phải số đo tại ruộng."
    common_power = {
        "provider": "NASA Langley Research Center, POWER Project",
        "source_id": "R-N01",
        "source_url": SOURCE_URL,
        "license": "NASA open data (no restriction on use; credit NASA POWER)",
        "geometry_crs": "EPSG:4326",
        "is_field_measurement": False,
    }
    ref = json.loads((REF / "metrics.json").read_text(encoding="utf-8"))
    datasets = [
        Dataset(
            **common_power,
            dataset_id="nasa_power_daily",
            title=t(
                "NASA POWER, số liệu ngày (5 ô lưới có đất trồng ở Nghệ An)",
                "NASA POWER daily (5 farmland cells of Nghệ An)",
            ),
            source_revision=", ".join(f"POWER Daily API {v}" for v in power_meta["api_versions"]) or None,
            retrieved_at=None,
            temporal_coverage="1990-01-01/2024-12-31",
            spatial_resolution="0.5° x 0.625° (MERRA-2 grid)",
            variables=["PRECTOTCORR", "T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT"],
            missing_policy="Fill value -999 read as missing; a month with any missing day has no total; the build stops when a weighted cell misses a day.",
            allowed_use=t(
                "Xem lại thời tiết của các năm đã qua theo ô lưới mô hình. " + na + " Năm đã qua không phải dự báo.",
                "Look back at past weather per model grid cell. Not measured at the field. A past year is not a forecast.",
            ),
            version_sha256=power_meta["sha256"],
            ingestion_status="INGESTED",
            notes=[
                t(
                    "Tệp lưu trong data/raw/power và data/raw/power_t2m không ghi ngày tải; vì vậy retrieved_at để trống.",
                    "The cached files in data/raw/power and data/raw/power_t2m do not record a download date, so retrieved_at is empty.",
                )
            ],
        ),
        Dataset(
            dataset_id="geoboundaries_adm1",
            title=t(
                "Ranh giới tỉnh (geoBoundaries ADM1, bản đơn giản)",
                "Province boundaries (geoBoundaries ADM1, simplified)",
            ),
            provider="geoBoundaries (William & Mary geoLab)",
            source_id="X-GEOBOUNDARIES",
            source_url="https://www.geoboundaries.org/",
            license="gbOpen: public domain per the file metadata, as recorded by the team",
            source_revision=None,
            retrieved_at=None,
            temporal_coverage="static",
            spatial_resolution="simplified polygon",
            geometry_crs="EPSG:4326",
            variables=["shapeName", "geometry"],
            missing_policy="The build stops when Nghệ An is not in the file.",
            allowed_use=t(
                "Vẽ đường viền tỉnh. Không phải ranh giới pháp lý.", "Draw the province outline. Not a legal boundary."
            ),
            version_sha256=file_sha(RAW / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"),
            ingestion_status="INGESTED",
            is_field_measurement=False,
        ),
        Dataset(
            dataset_id="modis_farmland_weights",
            title=t(
                "Trọng số đất trồng trọt theo ô lưới (MODIS MCD12C1)", "Farmland weight per grid cell (MODIS MCD12C1)"
            ),
            provider="NASA LP DAAC (MODIS); weights computed by the Miaudow team",
            source_id="R-N02",
            source_url="https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MCD12C1&version=061",
            license="NASA open data",
            source_revision="MCD12C1 v061, years 2001-2015",
            retrieved_at=None,
            temporal_coverage="2001/2015 (one fixed map)",
            spatial_resolution="0.05° land cover aggregated to 5 POWER cells",
            geometry_crs="EPSG:4326",
            variables=["farmland_weight"],
            missing_policy="The build stops when Nghệ An has no weighted cell.",
            allowed_use=t("Cân các ô lưới theo phần đất trồng trọt.", "Weight grid cells by their farmland share."),
            version_sha256=file_sha(REF / "cell_weights_nghe_an.csv"),
            ingestion_status="INGESTED",
            is_field_measurement=False,
            notes=[
                t(
                    "Một bản đồ cố định; không theo kịp thay đổi sử dụng đất về sau.",
                    "One fixed map; misses later land-cover change.",
                )
            ],
        ),
        Dataset(
            dataset_id="nso_rice_yield",
            title=t(
                "Độ lệch năng suất lúa của tỉnh (Cục Thống kê, bảng rủi ro)",
                "Province rice yield anomalies (NSO, risk table)",
            ),
            provider="Cục Thống kê (NSO Vietnam); anomalies computed by the Miaudow team (E-010)",
            source_id="R-D01",
            source_url="https://pxweb.nso.gov.vn/pxweb/en/",
            license="NSO terms; credit Cục Thống kê",
            source_revision=f"risk_table.json schema {json.loads((REF / 'risk_table.json').read_text(encoding='utf-8'))['schema_version']}",
            retrieved_at=None,
            temporal_coverage="1995/2024",
            spatial_resolution="province",
            geometry_crs=None,
            variables=["anom_history", "anom_oos", "oos_low_80", "oos_high_80"],
            missing_policy="Years without an NSO value stay null.",
            allowed_use=t(
                "Xem năng suất lúa của cả tỉnh trong quá khứ. Không phải năng suất của một ruộng.",
                "Look at past province rice yields. Not the yield of one field.",
            ),
            version_sha256=file_sha(REF / "risk_table.json"),
            ingestion_status="INGESTED",
            is_field_measurement=False,
        ),
        Dataset(
            dataset_id="e012_model",
            title=t("Kết quả kiểm tra mô hình E-012", "Model test results E-012"),
            provider="Miaudow team",
            source_id="E-012",
            source_url=None,
            license="Apache-2.0 (team artifacts)",
            source_revision=f"freeze commit {ref['freeze_commit']}",
            retrieved_at=None,
            temporal_coverage=f"test years {ref['test_years']['first']}/{ref['test_years']['last']}",
            spatial_resolution="province",
            geometry_crs=None,
            variables=["rmse", "mae", "r2_oos", "skill", "gates G1-G4"],
            missing_policy="Copied unchanged.",
            allowed_use=t(
                "Cho biết mô hình có đủ tốt để hiện hay không.", "Tells whether the model is good enough to show."
            ),
            version_sha256=file_sha(REF / "metrics.json"),
            ingestion_status="INGESTED",
            is_field_measurement=False,
        ),
        Dataset(
            dataset_id="e019_hazard_labels",
            title=t(
                "Phần đất trồng đạt từng quy tắc chính thức (E-019)",
                "Farmland share meeting each official rule (E-019)",
            ),
            provider="Miaudow team",
            source_id="E-019",
            source_url=None,
            license="Apache-2.0 (team artifacts)",
            source_revision="hazard_labels.json schema "
            + json.loads((REF / "hazard_labels.json").read_text(encoding="utf-8"))["schema_version"],
            retrieved_at=None,
            temporal_coverage="1995/2024",
            spatial_resolution="farmland-weighted province area (5 POWER cells)",
            geometry_crs=None,
            variables=["share_farmland"],
            missing_policy="Copied unchanged.",
            allowed_use=t(
                "Cách đọc máy móc các ngưỡng của Quyết định 18/2021 trên số liệu quá khứ; không phải ghi nhận chính thức.",
                "A mechanical reading of the Decision 18/2021 thresholds on past values; not an official record.",
            ),
            version_sha256=file_sha(REF / "hazard_labels.json"),
            ingestion_status="INGESTED",
            is_field_measurement=False,
        ),
        Dataset(
            dataset_id="e020_soil_wetness",
            title=t(
                "Độ ẩm đất tầng rễ khi cây ở ngoài ruộng (E-020)",
                "Root-zone soil wetness while each crop was in the field (E-020)",
            ),
            provider="Miaudow team, from NASA POWER GWETROOT (MERRA-2)",
            source_id="E-020",
            source_url=None,
            license="Apache-2.0 (team artifacts)",
            source_revision="soil_wetness.json schema "
            + json.loads((REF / "soil_wetness.json").read_text(encoding="utf-8"))["schema_version"],
            retrieved_at=None,
            temporal_coverage="1995/2024, normal 1991-2020",
            spatial_resolution="farmland-weighted province area (5 POWER cells)",
            geometry_crs=None,
            variables=["value", "normal"],
            missing_policy="Copied unchanged.",
            allowed_use=t(
                "Giá trị mô hình, không phải số đo; không có ngưỡng tốt xấu.",
                "A model value, not a measurement; no good or bad threshold.",
            ),
            version_sha256=file_sha(REF / "soil_wetness.json"),
            ingestion_status="INGESTED",
            is_field_measurement=False,
        ),
        Dataset(
            dataset_id="study_p02",
            title=t("Kết quả thử nghiệm P-02 (bảng của bài báo)", "P-02 trial results (the paper's tables)"),
            provider="Trịnh Đức Toàn et al. (2023); values transcribed by the Miaudow team",
            source_id="R-P02",
            source_url="https://vjol.info.vn/vaas/vi/article/download/167049/143292/289735",
            license="Journal article; values quoted with citation",
            source_revision="Tạp chí KH&CN Nông nghiệp Việt Nam 04(146): 43-51",
            retrieved_at=None,
            temporal_coverage="2020-06/2021-06",
            spatial_resolution="one 1,000 m2 trial plot per crop and season, Lưu Sơn, Đô Lương",
            geometry_crs=None,
            variables=[
                "Lãi thuần (Table 13)",
                "Tổng chi (Tables 4, 8, 12)",
                "sowing and harvest dates (Tables 1, 5, 9)",
            ],
            missing_policy="A value the paper does not give stays absent.",
            allowed_use=t(
                "Kết quả đã báo cáo của một thử nghiệm không lặp lại, giá năm 2020-21. Không phải thu nhập dự kiến.",
                "Reported results of one unreplicated trial at 2020-21 prices. Not expected income.",
            ),
            version_sha256=file_sha(ROOT / "api" / "rules" / "rotations.yaml"),
            ingestion_status="INGESTED",
            is_field_measurement=True,
            notes=[
                t(
                    "Đo trên ô thử ở Lưu Sơn năm 2020-21, không phải trên ruộng của bạn.",
                    "Measured on the Lưu Sơn trial plots in 2020-21, not on your field.",
                )
            ],
        ),
        Dataset(
            dataset_id="study_p03",
            title=t("Kết quả thử nghiệm P-03 (lời văn của bài báo)", "P-03 trial results (the paper's text)"),
            provider="Trịnh Đức Toàn et al. (2023); text transcribed by the Miaudow team",
            source_id="R-P03",
            source_url="https://ngheandost.gov.vn/tap-chi-chuyen-san/tap-chi-kh-cn-nghe-an/dac-san-kh-cn-nghe-an-so-2-2023-112.html?download=1&id=0",
            license="Journal article; text quoted with citation",
            source_revision="Đặc san KH&CN Nghệ An 2/2023",
            retrieved_at=None,
            temporal_coverage="2020-06/2021-06",
            spatial_resolution="one 1,000 m2 trial plot per crop, Lưu Sơn, Đô Lương",
            geometry_crs=None,
            variables=["economic return of the control (text)"],
            missing_policy="No sowing or harvest dates are reported; they stay absent.",
            allowed_use=t(
                "Kết quả đã báo cáo, chỉ dạng chữ; lợi nhuận chỉ trừ chi phí vật chất.",
                "Reported results, as text only; profit subtracts material costs only.",
            ),
            version_sha256=file_sha(ROOT / "api" / "rules" / "rotations.yaml"),
            ingestion_status="INGESTED",
            is_field_measurement=True,
            notes=[],
        ),
        manifest_dataset(
            "chirps_v3_monthly",
            t("CHIRPS v3, tổng mưa tháng", "CHIRPS v3 monthly rainfall"),
            RAW / "chirps_v3",
            {
                "provider": "Climate Hazards Center, UC Santa Barbara",
                "source_id": "X-CHIRPS-V3",
                "source_url": "https://www.chc.ucsb.edu/data/chirps3",
                "license": "CC BY 4.0 (to confirm against the download page)",
                "temporal_coverage": "1981/near present",
                "spatial_resolution": "0.05°",
                "geometry_crs": "EPSG:4326",
                "variables": ["precip"],
                "missing_policy": "Kept beside NASA POWER, never merged; a missing month stays null.",
                "allowed_use": t(
                    "Nguồn mưa thứ hai để đặt cạnh NASA POWER. Ước tính từ vệ tinh và trạm, không phải số đo tại ruộng.",
                    "A second rain source beside NASA POWER. A satellite and station estimate, not measured at the field.",
                ),
                "is_field_measurement": False,
            },
        ),
        manifest_dataset(
            "modis_mod13q1_ndvi",
            t("MODIS MOD13Q1, chỉ số thực vật NDVI 16 ngày", "MODIS MOD13Q1 16-day NDVI"),
            RAW / "modis_mod13q1",
            {
                "provider": "NASA LP DAAC",
                "source_id": "X-MODIS-MOD13Q1",
                "source_url": "https://lpdaac.usgs.gov/products/mod13q1v061/",
                "license": "NASA open data",
                "temporal_coverage": "2000/near present",
                "spatial_resolution": "250 m",
                "geometry_crs": "MODIS sinusoidal",
                "variables": ["NDVI"],
                "missing_policy": "Cloud-flagged pixels stay missing.",
                "allowed_use": t(
                    "Xem độ xanh của thảm thực vật. NDVI không phải chẩn đoán cây trồng và không dùng làm đầu vào mô hình.",
                    "Look at vegetation greenness. NDVI is not a crop diagnosis and is not a model input.",
                ),
                "is_field_measurement": False,
            },
        ),
        Dataset(
            dataset_id="sentinel2_l2a",
            title=t("Sentinel-2 L2A, phản xạ bề mặt", "Sentinel-2 L2A surface reflectance"),
            provider="ESA Copernicus",
            source_id="X-SENTINEL2-L2A",
            source_url="https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html",
            license="Copernicus open data licence",
            source_revision=None,
            retrieved_at=None,
            temporal_coverage="2017/near present",
            spatial_resolution="10/20/60 m",
            geometry_crs="UTM",
            variables=["B02", "B03", "B04", "B08", "SCL"],
            missing_policy="Not loaded.",
            allowed_use=t("Chưa dùng.", "Not used yet."),
            version_sha256=None,
            ingestion_status="CONTRACT_ONLY",
            is_field_measurement=False,
            notes=[
                t(
                    "Chưa tải ảnh nào. Không ghép ô lưới NASA POWER 0,5° với ảnh 10 m mà không ghi rõ sự khác nhau về độ phân giải.",
                    "No scene fetched. NASA POWER 0.5° cells must never be joined to 10 m pixels without recording the resolution mismatch.",
                )
            ],
        ),
        Dataset(
            dataset_id="nasa_hls",
            title=t("NASA HLS v2 (Landsat và Sentinel-2 hài hòa)", "NASA HLS v2 (harmonized Landsat and Sentinel-2)"),
            provider="NASA LP DAAC",
            source_id="X-NASA-HLS",
            source_url="https://hls.gsfc.nasa.gov/data-products/",
            license="NASA open data",
            source_revision=None,
            retrieved_at=None,
            temporal_coverage="2013/near present",
            spatial_resolution="30 m",
            geometry_crs="UTM",
            variables=["surface reflectance"],
            missing_policy="Not loaded.",
            allowed_use=t("Chưa dùng.", "Not used yet."),
            version_sha256=None,
            ingestion_status="CONTRACT_ONLY",
            is_field_measurement=False,
            notes=[
                t(
                    "Chưa tải. Không đo trực tiếp độ ẩm của ruộng.",
                    "Not fetched. It does not measure field moisture directly.",
                )
            ],
        ),
    ]
    return datasets


EXTRA_SOURCES = [
    SourceFact(
        id="X-GEOBOUNDARIES",
        citation=t(
            "geoBoundaries, ranh giới hành chính cấp tỉnh của Việt Nam (ADM1)",
            "geoBoundaries, Viet Nam ADM1 administrative boundaries",
        ),
        study_type=t("Bộ dữ liệu ranh giới mở", "Open boundary dataset"),
        read_status="catalog entry; not in the team rulebook",
        full_text_read=None,
        limitations=[t("Không phải ranh giới pháp lý.", "Not a legal boundary.")],
        url="https://www.geoboundaries.org/",
    ),
    SourceFact(
        id="X-CHIRPS-V3",
        citation=t("CHIRPS v3 (Climate Hazards Center)", "CHIRPS v3 (Climate Hazards Center)"),
        study_type=t("Số liệu mưa từ vệ tinh và trạm đo", "Satellite and station rainfall data"),
        read_status="catalog entry; not in the team rulebook",
        full_text_read=None,
        limitations=[
            t(
                "Ước tính trên lưới 0,05°, không phải số đo tại ruộng.",
                "A 0.05° gridded estimate, not measured at the field.",
            )
        ],
        url="https://www.nature.com/articles/s41597-026-07096-4",
    ),
    SourceFact(
        id="X-MODIS-MOD13Q1",
        citation=t("MODIS MOD13Q1 v061, chỉ số thực vật 16 ngày", "MODIS MOD13Q1 v061, 16-day vegetation indices"),
        study_type=t("Số liệu vệ tinh của NASA", "NASA satellite data"),
        read_status="catalog entry; not in the team rulebook",
        full_text_read=None,
        limitations=[t("NDVI không phải chẩn đoán cây trồng.", "NDVI is not a crop diagnosis.")],
        url="https://lpdaac.usgs.gov/products/mod13q1v061/",
    ),
    SourceFact(
        id="X-SENTINEL2-L2A",
        citation=t(
            "Sentinel-2 L2A, tài liệu Copernicus Data Space", "Sentinel-2 L2A, Copernicus Data Space documentation"
        ),
        study_type=t("Số liệu vệ tinh", "Satellite data"),
        read_status="catalog entry; not in the team rulebook",
        full_text_read=None,
        limitations=[t("Chưa tải về.", "Not fetched.")],
        url="https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html",
    ),
    SourceFact(
        id="X-NASA-HLS",
        citation=t("NASA HLS v2, các sản phẩm số liệu", "NASA HLS v2 data products"),
        study_type=t("Số liệu vệ tinh", "Satellite data"),
        read_status="catalog entry; not in the team rulebook",
        full_text_read=None,
        limitations=[t("Chưa tải về.", "Not fetched.")],
        url="https://hls.gsfc.nasa.gov/data-products/",
    ),
    SourceFact(
        id="E-022",
        citation=t(
            "Các phép tính của ứng dụng (cộng tiền lãi các vụ, đếm cây, đếm ngày)",
            "The app's own computations (sum of season profits, crop counts, day counts)",
        ),
        study_type=t("Tính toán của chúng tôi", "Our computation"),
        read_status=None,
        full_text_read=None,
        limitations=[
            t(
                "Phép cộng và phép đếm trên số liệu đã trích dẫn; không phải kết quả mới.",
                "Sums and counts over cited values; not a new finding.",
            )
        ],
        url=None,
    ),
]


def build_sources() -> list[SourceFact]:
    rows = yaml.safe_load((RULES_DIR / "sources.yaml").read_text(encoding="utf-8"))
    out = []
    for r in rows:
        out.append(
            SourceFact(
                id=r["id"],
                citation=Text(**r["citation"]),
                study_type=Text(**r["study_type"]) if r.get("study_type") else None,
                place_years=Text(**r["place_years"]) if r.get("place_years") else None,
                read_status=r.get("read_status"),
                full_text_read=r.get("full_text_read"),
                limitations=[Text(**x) for x in r.get("limitations") or []],
                url=r.get("url"),
            )
        )
    known = {s.id for s in out}
    return out + [s for s in EXTRA_SOURCES if s.id not in known]


METHODS = [
    (
        "sum_daily_precip_complete_month",
        "Tổng mưa tháng (chỉ tháng đủ ngày)",
        "Monthly rain total (complete months only)",
        "Cộng lượng mưa ngày PRECTOTCORR của mọi ngày trong tháng. Thiếu một ngày thì tháng đó để trống, không đoán.",
        "Sum of daily PRECTOTCORR over every day of the month. A month with a missing day stays empty; nothing is guessed.",
        ["R-N01"],
    ),
    (
        "sum_complete_months",
        "Tổng mưa năm",
        "Annual rain total",
        "Cộng 12 tổng tháng; thiếu một tháng thì năm đó để trống.",
        "Sum of the 12 monthly totals; empty when a month is empty.",
        ["R-N01"],
    ),
    (
        "anomaly_vs_1991_2020_normal",
        "Chênh lệch so với mức thường 1991-2020",
        "Anomaly against the 1991-2020 normal",
        "Lấy tổng tháng trừ trung bình của cùng tháng trong 1991-2020 (mm), và chia cho trung bình đó (%).",
        "Monthly total minus the 1991-2020 mean of the same month (mm), and divided by that mean (%).",
        ["R-N01", "R-A15"],
    ),
    (
        "count_days_t2m_max_ge_35",
        "Số ngày nóng (nhiệt độ cao nhất từ 35 °C)",
        "Hot days (daily maximum at least 35 °C)",
        "Đếm số ngày có T2M_MAX từ 35 °C trở lên; 35 °C là mức dưới của Quyết định 18/2021 Điều 47.1 a. Đây là số ngày, không phải đợt nắng nóng theo luật.",
        "Count of days with T2M_MAX at or above 35 °C, the lower bound of Decision 18/2021 Art. 47.1 a. A day count, not a heat spell under the rule.",
        ["R-A01", "R-N01"],
    ),
    (
        "count_days_t2m_le_13",
        "Số ngày lạnh (nhiệt độ trung bình đến 13 °C)",
        "Cold days (daily mean at most 13 °C)",
        "Đếm số ngày có T2M trung bình ngày từ 13 °C trở xuống; 13 °C là mức trên của Điều 53.1 a. Đây là số ngày, không phải đợt rét hại theo luật.",
        "Count of days with daily mean T2M at or below 13 °C, the upper bound of Art. 53.1 a. A day count, not a cold spell under the rule.",
        ["R-A01", "R-N01"],
    ),
    (
        "etccdi_cdd_calendar_year",
        "Đợt khô dài nhất (CDD)",
        "Longest dry spell (CDD)",
        "Số ngày liên tiếp dài nhất trong năm có mưa dưới 1 mm (chỉ số CDD của ETCCDI). Đợt khô bị cắt ở ngày 1 tháng 1.",
        "The longest run of consecutive days in the calendar year with rain below 1 mm (ETCCDI CDD index). A spell is cut at 1 January.",
        ["R-A10", "R-N01"],
    ),
    (
        "art48_drought_rain_month",
        "Tháng thiếu mưa theo Điều 48",
        "Drought-rain month under Art. 48",
        "Tháng có tổng mưa thiếu hụt trên 50% so với trung bình 1991-2020 của cùng tháng (chỉ phần lượng mưa của Điều 48.1; phần nước mặt không tính được).",
        "A month whose rain total is more than 50% below the 1991-2020 mean of that month (rain part of Art. 48.1 only; the surface-water part cannot be computed).",
        ["R-A01", "R-N01", "R-A15"],
    ),
    (
        "farmland_weighted_mean",
        "Trung bình có trọng số đất trồng",
        "Farmland-weighted mean",
        "Giá trị của 5 ô lưới nhân với trọng số đất trồng (MODIS) rồi chia cho tổng trọng số. Thiếu một ô thì để trống.",
        "The 5 cell values times their MODIS farmland weights, divided by the weight sum. Empty when any cell is empty.",
        ["R-N02"],
    ),
    (
        "E-019",
        "Phần đất trồng đạt quy tắc chính thức",
        "Farmland share meeting an official rule",
        "Áp ngưỡng cấp độ 1 của Quyết định 18/2021 cho từng ô lưới trong thời gian cây ở ngoài ruộng, rồi cộng trọng số đất trồng của các ô đạt.",
        "Apply the level-1 thresholds of Decision 18/2021 to each grid cell over the crop's field time, then add the farmland weights of the cells that meet them.",
        ["E-019", "R-A01", "R-N01", "R-N02"],
    ),
    (
        "E-020",
        "Độ ẩm đất tầng rễ khi cây ở ngoài ruộng",
        "Root-zone wetness while the crop was in the field",
        "Trung bình GWETROOT có trọng số đất trồng trong thời gian cây ở ngoài ruộng, đặt cạnh trung bình 1991-2020.",
        "Farmland-weighted mean GWETROOT over the crop's field time, next to its 1991-2020 mean.",
        ["E-020", "R-W12", "R-N01"],
    ),
    (
        "E-012",
        "Mô hình độ lệch năng suất lúa",
        "Rice yield anomaly model",
        "Mô hình hồi quy ridge (M1) và các bước kiểm tra G1-G4 trên các năm 2016-2024.",
        "Ridge regression (M1) and gates G1-G4 on the test years 2016-2024.",
        ["E-012", "E-010", "R-D01"],
    ),
    (
        "E-022",
        "Phép tính của ứng dụng",
        "Engine computations",
        "Cộng tiền lãi các vụ của một cơ cấu, đếm số cây, số cây họ đậu và số ngày có cây trên ruộng, từ số liệu đã trích dẫn.",
        "Sum of the season profits of a plan, counts of crops, legumes and days with a crop in the field, from cited values.",
        ["E-022", "R-P02", "R-B01"],
    ),
    (
        "study_table_copy",
        "Chép từ bảng của bài báo",
        "Copied from the paper's table",
        "Số được chép nguyên từ bảng của bài báo, kèm số bảng và trang.",
        "A number copied unchanged from the paper's table, with table and page.",
        ["R-P02", "R-P03"],
    ),
    (
        "live_power_complete_month",
        "Tải NASA POWER theo yêu cầu",
        "On-demand NASA POWER fetch",
        "Tải số liệu ngày của một điểm từ API NASA POWER; tổng tháng chỉ khi đủ ngày; trung bình nhiệt độ cao nhất chỉ khi đủ ngày.",
        "Fetch daily values for one point from the NASA POWER API; monthly totals and mean maximum temperature only for complete months.",
        ["R-N01"],
    ),
    (
        "chirps_monthly_cell",
        "Tổng mưa tháng CHIRPS theo ô",
        "CHIRPS monthly total per cell",
        "Tổng mưa tháng của CHIRPS v3 cho từng ô NASA POWER, đặt cạnh POWER, không trộn.",
        "CHIRPS v3 monthly total per NASA POWER cell, kept beside POWER, never merged.",
        ["X-CHIRPS-V3"],
    ),
]


def build_methods() -> list[MethodDef]:
    return [
        MethodDef(method_id=m, title=t(tv, te), description=t(dv, de), source_ids=s) for m, tv, te, dv, de, s in METHODS
    ]


def metric_def(title, unit, method_id, dataset_id, desc, not_prove):
    return {
        "title": {"vi": title[0], "en": title[1]},
        "unit": unit,
        "method_id": method_id,
        "dataset_id": dataset_id,
        "description": {"vi": desc[0], "en": desc[1]},
        "does_not_prove": {"vi": not_prove[0], "en": not_prove[1]},
    }


GRID = (
    "Giá trị ô lưới mô hình không cho biết mưa hay nhiệt độ trên ruộng của bạn.",
    "A model grid value does not tell the rain or temperature on your field.",
)
PAST = ("Năm đã qua không phải dự báo.", "A past year is not a forecast.")


def build_metrics() -> dict:
    return {
        "monthly_rain_total": metric_def(
            ("Tổng mưa tháng", "Monthly rain total"),
            "mm",
            "sum_daily_precip_complete_month",
            "nasa_power_daily",
            ("Tổng mưa của một tháng theo NASA POWER.", "The rain total of one month from NASA POWER."),
            GRID,
        ),
        "monthly_rain_anomaly_mm": metric_def(
            ("Chênh lệch mưa tháng (mm)", "Monthly rain anomaly (mm)"),
            "mm",
            "anomaly_vs_1991_2020_normal",
            "nasa_power_daily",
            ("Tổng tháng trừ mức thường 1991-2020.", "Monthly total minus the 1991-2020 normal."),
            PAST,
        ),
        "monthly_rain_anomaly_pct": metric_def(
            ("Chênh lệch mưa tháng (%)", "Monthly rain anomaly (%)"),
            "%",
            "anomaly_vs_1991_2020_normal",
            "nasa_power_daily",
            ("Chênh lệch chia cho mức thường 1991-2020.", "Anomaly divided by the 1991-2020 normal."),
            PAST,
        ),
        "monthly_rain_normal": metric_def(
            ("Mức thường của mưa tháng 1991-2020", "1991-2020 monthly rain normal"),
            "mm",
            "anomaly_vs_1991_2020_normal",
            "nasa_power_daily",
            ("Trung bình tổng mưa của cùng tháng trong 1991-2020.", "Mean of the same month's totals over 1991-2020."),
            GRID,
        ),
        "annual_rain_total": metric_def(
            ("Tổng mưa năm", "Annual rain total"),
            "mm",
            "sum_complete_months",
            "nasa_power_daily",
            ("Tổng mưa của cả năm.", "The rain total of the whole year."),
            GRID,
        ),
        "hot_days": metric_def(
            ("Số ngày nóng từ 35 °C", "Hot days at or above 35 °C"),
            "days",
            "count_days_t2m_max_ge_35",
            "nasa_power_daily",
            ("Số ngày trong năm có nhiệt độ cao nhất từ 35 °C.", "Days in the year with a maximum at or above 35 °C."),
            (
                "Không phải số đợt nắng nóng theo Quyết định 18/2021.",
                "Not the number of heat spells under Decision 18/2021.",
            ),
        ),
        "cold_days": metric_def(
            ("Số ngày lạnh đến 13 °C", "Cold days at or below 13 °C"),
            "days",
            "count_days_t2m_le_13",
            "nasa_power_daily",
            (
                "Số ngày trong năm có nhiệt độ trung bình đến 13 °C.",
                "Days in the year with a daily mean at or below 13 °C.",
            ),
            (
                "Không phải số đợt rét hại theo Quyết định 18/2021.",
                "Not the number of cold spells under Decision 18/2021.",
            ),
        ),
        "longest_dry_spell": metric_def(
            ("Đợt khô dài nhất", "Longest dry spell"),
            "days",
            "etccdi_cdd_calendar_year",
            "nasa_power_daily",
            ("Số ngày liên tiếp dài nhất có mưa dưới 1 mm.", "Longest run of days with rain below 1 mm."),
            (
                "Không cho biết ruộng có đủ nước tưới hay không.",
                "Does not tell whether the field had irrigation water.",
            ),
        ),
        "drought_rain_months": metric_def(
            ("Số tháng thiếu mưa theo Điều 48", "Drought-rain months under Art. 48"),
            "months",
            "art48_drought_rain_month",
            "nasa_power_daily",
            ("Số tháng có mưa thiếu trên 50% so với mức thường.", "Months with rain more than 50% below normal."),
            (
                "Không phải công bố hạn hán chính thức; phần nước mặt của Điều 48 không tính được.",
                "Not an official drought declaration; the surface-water part of Art. 48 cannot be computed.",
            ),
        ),
        "hazard_share": metric_def(
            ("Phần đất trồng đạt quy tắc", "Farmland share meeting a rule"),
            "share 0-1",
            "E-019",
            "e019_hazard_labels",
            (
                "Tổng trọng số đất trồng của các ô lưới đạt quy tắc cấp độ 1.",
                "Sum of farmland weights of the cells meeting the level-1 rule.",
            ),
            (
                "Không phải ghi nhận thiên tai chính thức; không nói ruộng của bạn bị ảnh hưởng.",
                "Not an official disaster record; does not say your field was affected.",
            ),
        ),
        "soil_wetness": metric_def(
            ("Độ ẩm đất tầng rễ", "Root-zone soil wetness"),
            "0-1",
            "E-020",
            "e020_soil_wetness",
            (
                "Giá trị mô hình MERRA-2 từ 0 (khô) đến 1 (bão hòa).",
                "MERRA-2 model value from 0 (dry) to 1 (saturated).",
            ),
            (
                "Không phải số đo độ ẩm tại ruộng; không có ngưỡng tốt xấu.",
                "Not a field moisture measurement; no good or bad threshold.",
            ),
        ),
        "reported_profit": metric_def(
            ("Lãi thuần đã báo cáo", "Reported net profit"),
            "thousand VND/ha",
            "study_table_copy",
            "study_p02",
            (
                "Lãi thuần của một vụ trong thử nghiệm P-02 (Bảng 13).",
                "Net profit of one season in the P-02 trial (Table 13).",
            ),
            (
                "Kết quả 2020-21 của một ô thử không lặp lại; không phải thu nhập dự kiến.",
                "A 2020-21 result of one unreplicated plot; not expected income.",
            ),
        ),
        "reported_cost": metric_def(
            ("Tổng chi đã báo cáo", "Reported total cost"),
            "thousand VND/ha",
            "study_table_copy",
            "study_p02",
            (
                "Tổng chi của một vụ trong thử nghiệm P-02 (Bảng 4, 8, 12).",
                "Total cost of one season in the P-02 trial (Tables 4, 8, 12).",
            ),
            ("Giá năm 2020-21; chi phí năm nay có thể khác.", "2020-21 prices; this year's cost may differ."),
        ),
        "year_profit_total": metric_def(
            ("Tổng lãi cả năm (phép cộng)", "Whole-year profit (sum)"),
            "thousand VND/ha",
            "E-022",
            "study_p02",
            ("Cộng lãi thuần của các vụ trong một cơ cấu.", "Sum of the season net profits of one plan."),
            (
                "Bài báo không nói cả cơ cấu được trồng liền trên một ruộng.",
                "The paper does not say one field carried the whole plan.",
            ),
        ),
        "crops_in_year": metric_def(
            ("Số cây trong năm", "Crops in the year"),
            "crops",
            "E-022",
            "study_p02",
            ("Số vụ có cây trong cơ cấu.", "Seasons with a crop in the plan."),
            ("Không nói gì về đất tốt lên.", "Says nothing about soil improvement."),
        ),
        "legume_count": metric_def(
            ("Số cây họ đậu", "Legume crops"),
            "crops",
            "E-022",
            "study_p02",
            ("Số cây thuộc họ Đậu (Fabaceae) theo GRIN-Global.", "Crops in the family Fabaceae per GRIN-Global."),
            ("Không nói cây cố định bao nhiêu đạm trên ruộng.", "Does not say how much nitrogen is fixed in a field."),
        ),
        "living_days": metric_def(
            ("Số ngày có cây trên ruộng", "Days with a crop in the field"),
            "days",
            "E-022",
            "study_p02",
            (
                "Số ngày từ ngày gieo đến ngày thu hoạch cuối của các vụ; ngày chồng nhau tính một lần.",
                "Days from sowing to the last reported harvest of each season; overlapping days counted once.",
            ),
            (
                "Bài báo không nói các vụ được trồng liền trên một ruộng.",
                "The paper does not say the seasons followed each other on one field.",
            ),
        ),
    }


# ---------------------------------------------------------------- rotations and passages


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_rotations", ROOT / "scripts" / "sync_rotations.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(name: str, payload: dict, stamp: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    body = {"generated_at": stamp, **payload}
    (OUT / name).write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


def build_decision_view() -> dict:
    """The decision core's own text for the web app (one implementation): per plan, how the study land relates to
    each water answer, and the questions for the extension officer. Read back from the canonical files just written."""
    from miaudow_api import canonical as canon  # noqa: PLC0415 - after the canonical files exist
    from miaudow_api import decision  # noqa: PLC0415

    canon.clear()
    waters = [None, "canal_end", "high_field", "water_short", "reliable"]
    plans: dict[str, dict] = {}
    for water in waters:
        res = decision.compare(CompareRequest(water=water))
        for p in res.plans:
            entry = plans.setdefault(p.plan_id, {"applicability": {}, "questions_for_officer": []})
            entry["applicability"][water or "unknown"] = p.applicability.model_dump()
            entry["questions_for_officer"] = [q.model_dump() for q in p.questions_for_officer]
    first = decision.compare(CompareRequest())
    return {
        "plan_order": list(decision.STUDY_ORDER),
        "plans": plans,
        "missing_information": [m.model_dump() for m in first.missing_information],
    }


def build_ndvi_modis() -> dict | None:
    """MODIS MOD13Q1 NDVI at the study site, per 16-day date: median and quartiles of the valid 250 m pixels in the
    9 x 9 block around Lưu Sơn. Dates without a valid pixel stay null (never interpolated)."""
    folder = DATA / "raw" / "modis_mod13q1"
    summary = folder / "ndvi_study_site_summary.csv"
    if not summary.exists():
        return None
    manifest = read_manifest(folder) or {}
    rows = list(csv.DictReader(summary.open(encoding="utf-8")))

    def num(v: str) -> float | None:
        return None if v in ("", None) else round(float(v), 4)

    return {
        "dataset_id": "modis_mod13q1_ndvi",
        "source_url": manifest.get("source_url"),
        "license": manifest.get("license"),
        "retrieved_at": manifest.get("retrieved_at"),
        "spatial_resolution": "250 m, 9 x 9 pixels around the study point",
        "is_field_measurement": False,
        "dates": [r["date"] for r in rows],
        "median": [num(r["ndvi_median"]) for r in rows],
        "p25": [num(r["ndvi_p25"]) for r in rows],
        "p75": [num(r["ndvi_p75"]) for r in rows],
        "n_valid": [int(r["n_valid"]) for r in rows],
        "n_total": [int(r["n_total"]) for r in rows],
        "limitations": {
            "vi": "NDVI là độ xanh của mặt đất nhìn từ vệ tinh, không chẩn đoán sâu bệnh, năng suất hay độ ẩm đất. Một điểm ảnh 250 m gồm nhiều thửa ruộng.",
            "en": "NDVI is the greenness of the land surface seen from space; it does not diagnose pests, yield or soil moisture. A 250 m pixel mixes several fields.",
        },
    }


def main() -> None:
    check_team_dates()
    cells = load_cells()
    daily, power_meta = load_daily(cells)
    weights = {c["id"]: c["weight"] for c in cells}
    clim = {cid: monthly_climatology(df["PRECTOTCORR"]) for cid, df in daily.items()}
    stamp = datetime.now(UTC).isoformat(timespec="seconds")

    hazards = build_hazards(cells, daily, weights, clim)
    soil = build_soil(daily, weights)
    geo = build_geo(cells)
    model = build_model()
    climate = build_climate(cells, daily, clim, power_meta, load_chirps())
    sync = load_sync_module()
    rotations = sync.build()
    catalog = {
        "datasets": [d.model_dump(mode="json") for d in build_datasets(power_meta)],
        "methods": [m.model_dump(mode="json") for m in build_methods()],
        "sources": [s.model_dump(mode="json") for s in build_sources()],
        "metrics": build_metrics(),
    }
    passages = knowledge.build_passages(
        climate=climate, hazards=hazards, model=model, rotations=rotations, catalog=catalog, root=ROOT
    )

    write("hazards.json", {"years": hazards.pop("years"), **hazards}, stamp)
    write("soil.json", soil, stamp)
    write("geo.json", geo, stamp)
    write("model.json", model, stamp)
    write("climate.json", climate, stamp)
    write("catalog.json", catalog, stamp)
    write("rotations.generated.json", rotations, stamp)
    write("passages.json", {"passages": [p.model_dump(mode="json") for p in passages]}, stamp)
    write("decision.json", build_decision_view(), stamp)
    ndvi = build_ndvi_modis()
    if ndvi:
        write("ndvi_modis.json", ndvi, stamp)
    sys.stdout.write(f"written {sorted(p.name for p in OUT.iterdir())}\n")


if __name__ == "__main__":
    main()
