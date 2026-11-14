"""Write the crop exposure artifacts of the plan cards (UI-UX-SPEC CropExposure) for the P-02 crops in Nghe An:
artifacts/hazard_labels.json, official risk-level labels per crop and per year (05 section 4b, E-019), and
artifacts/soil_wetness.json, root-zone soil wetness per crop and year (05 section 4d, E-020).

Usage: PYTHONPATH=src python scripts/export_crop_exposure.py   (after scripts/run_primary_test.py)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from fieldshift.data.power import POWER_CACHE_FILES, load_cells
from fieldshift.features.hazard_labels import hazard_label_rows, plan_crops
from fieldshift.features.soil_wetness import soil_wetness_rows
from fieldshift.ml.primary_test import SCHEMA_VERSION

PROVINCE = "Nghe An"  # the province of the P-02 trial (province_nso spelling of cell_weights.csv)

weights_table = pd.read_csv("data/processed/cell_weights.csv")  # fixed farmland mask, D-106
in_mask = (weights_table["province_nso"] == PROVINCE) & (weights_table["method"] == "farmland_weighted")
nghe_an = weights_table[in_mask & (weights_table["farmland_weight"] > 0)]
weights = {(round(r.lat, 6), round(r.lon, 6)): float(r.farmland_weight) for r in nghe_an.itertuples()}
cells, _unmatched = load_cells("data/raw/power", "data/raw/power_t2m", POWER_CACHE_FILES)
NEEDED = ("PRECTOTCORR", "T2M_MAX", "T2M", "GWETROOT")  # the rules (05 section 4b) and soil wetness (section 4d)
missing = [c for c in weights if c not in cells or any(col not in cells[c] for col in NEEDED)]
if missing:
    raise ValueError(f"cached POWER series missing or without {NEEDED} for the weighted {PROVINCE} cells {missing}")
crops = plan_crops(yaml.safe_load(Path("rules/rotations.yaml").read_text(encoding="utf-8")))
gates = json.loads(Path("artifacts/gates.json").read_text(encoding="utf-8"))  # written by run_primary_test.py
for name, rows, field in (
    ("hazard_labels.json", hazard_label_rows(crops, cells, weights), "share_farmland"),
    ("soil_wetness.json", soil_wetness_rows(crops, cells, weights), "value"),
):
    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "freeze_commit": gates["freeze_commit"],
        "rows": rows,
    }
    # compact: the health endpoint parses every artifact on each request
    Path("artifacts", name).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(name, "rows:", len(rows), "| cells:", len(weights), "| null:", sum(r[field] is None for r in rows))
