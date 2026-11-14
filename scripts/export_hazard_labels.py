"""Write artifacts/hazard_labels.json: official risk-level labels per P-02 plan crop and per year (05 section 4b, E-019).

Usage: PYTHONPATH=src python scripts/export_hazard_labels.py   (after scripts/run_primary_test.py)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from fieldshift.data.power import POWER_CACHE_FILES, load_cells
from fieldshift.features.hazard_labels import hazard_label_rows, plan_crops
from fieldshift.ml.primary_test import SCHEMA_VERSION

PROVINCE = "Nghe An"  # the province of the P-02 trial (province_nso spelling of cell_weights.csv)

weights_table = pd.read_csv("data/processed/cell_weights.csv")  # fixed farmland mask, D-106
nghe_an = weights_table[(weights_table["province_nso"] == PROVINCE) & (weights_table["farmland_weight"] > 0)]
weights = {(round(r.lat, 6), round(r.lon, 6)): float(r.farmland_weight) for r in nghe_an.itertuples()}
cells, _unmatched = load_cells("data/raw/power", "data/raw/power_t2m", POWER_CACHE_FILES)
missing = [c for c in weights if c not in cells]
if missing:
    raise ValueError(f"no cached POWER series for the weighted {PROVINCE} cells {missing}")
plans = yaml.safe_load(Path("rules/rotations.yaml").read_text(encoding="utf-8"))
rows = hazard_label_rows(plan_crops(plans), cells, weights)
gates = json.loads(Path("artifacts/gates.json").read_text(encoding="utf-8"))  # written by run_primary_test.py
doc = {
    "schema_version": SCHEMA_VERSION,
    "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    "freeze_commit": gates["freeze_commit"],
    "rows": rows,
}
# compact: the health endpoint parses every artifact on each request
Path("artifacts/hazard_labels.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8", newline="\n")
print("rows:", len(rows), "| cells:", len(weights), "| crops:", len({r["crop_key"] for r in rows if r["crop_key"]}))
