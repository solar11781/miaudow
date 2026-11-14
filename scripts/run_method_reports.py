"""Method-page reports: winter claim (E-012, E-018), setup choices (E-012, E-013, E-017), drought readings (E-014) and
the DesInventar heavy-rain check (E-016) (05-DATA-CONTRACTS section 5b ReportItem).

Usage: PYTHONPATH=src python scripts/run_method_reports.py
(after run_sensitivity.py and export_crop_exposure.py; the DesInventar export is fetched by reproduce.sh)
Adds the four reports to artifacts/metrics.json and replaces earlier copies of them; the other reports and every
metric row stay. E-014 unit (provisional choice, 2026-11-14, the register says "per province and season"): one
reading per training-table row, on the province's farmland-weighted daily rain over its NSO season window, against
the 1991-2020 monthly normal of that series (D-118). Texts are drafts for the copy review (vi and en).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from fieldshift.data.desinventar import rice_flood_damage_years
from fieldshift.data.power import POWER_CACHE_FILES, load_cells
from fieldshift.features.climate import province_daily_weather
from fieldshift.features.hazards import monthly_climatology, season_drought_readings
from fieldshift.ml.reports import drought_readings_report, heavy_rain_check_report, setup_report, winter_claim_report

METRICS = Path("artifacts/metrics.json")
DESINVENTAR = "data/raw/desinventar/DI_export_vnm.zip"  # R-A19, checking only, never committed (D-54)
DESINVENTAR_PROVINCE = "Nghệ An"  # lev0 name in the DesInventar export
CHECK_YEARS = range(1995, 2009)  # EXPERIMENTS E-016 and D-54: Nghệ An 1995-2008


def drought_readings() -> pd.DataFrame:
    table = pd.read_csv("data/processed/training_table.csv", parse_dates=["window_start", "window_end"])
    weights = pd.read_csv("data/processed/cell_weights.csv")  # fixed farmland mask, D-106
    cells, _unmatched = load_cells("data/raw/power", "data/raw/power_t2m", POWER_CACHE_FILES)
    out = []
    for province, g in weights.groupby("province_nso"):
        wts = {
            (round(la, 6), round(lo, 6)): w for la, lo, w in zip(g["lat"], g["lon"], g["farmland_weight"], strict=True)
        }
        rain = province_daily_weather({c: cells[c][["PRECTOTCORR"]] for c in wts}, wts)["PRECTOTCORR"]
        clim = monthly_climatology(rain)
        for r in table[table["province_nso"] == province].itertuples(index=False):
            consecutive, any2 = season_drought_readings(rain, r.window_start.date(), r.window_end.date(), clim)
            out.append((province, r.season, r.year, consecutive, any2))
    readings = pd.DataFrame(out, columns=["province_nso", "season", "year", "consecutive", "any2"])
    if len(readings) != len(table):
        raise ValueError(f"drought readings for {len(readings)} of the {len(table)} training rows")
    return readings


labels = json.loads(Path("artifacts/hazard_labels.json").read_text(encoding="utf-8"))["rows"]  # E-019
heavy_rain = {
    r["year"]
    for r in labels
    if r["level"] == "year" and r["rule"] == "heavy_rain" and r["share_farmland"] > 0 and r["year"] in CHECK_YEARS
}
damage = rice_flood_damage_years(DESINVENTAR, DESINVENTAR_PROVINCE, CHECK_YEARS)

doc = json.loads(METRICS.read_text(encoding="utf-8"))
new = [
    winter_claim_report(doc["metrics"]),
    setup_report(),
    drought_readings_report(drought_readings()),
    heavy_rain_check_report(heavy_rain, damage, CHECK_YEARS),
]
titles = {r["title"]["en"] for r in new}
doc["reports"] = [r for r in doc["reports"] if r["title"]["en"] not in titles] + new
doc["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
METRICS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
for r in new:
    print(r["id"], "|", r["title"]["en"], "|", r["text"]["en"])
