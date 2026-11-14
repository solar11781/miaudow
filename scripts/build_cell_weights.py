"""Build data/processed/cell_weights.csv: one fixed farmland mask for all years (D-106, D-107; 05-DATA-CONTRACTS §3).

Usage: PYTHONPATH=src python scripts/build_cell_weights.py
Inputs: data/interim/modis_vn/MCD12C1_<year>_vn.npz for 2001-2015 (scripts/modis_landcover.py) and the geoBoundaries
ADM1 file. Outputs the weights table and data/processed/cell_weights_zero.csv (cells with no farmland, reported).
"""

import csv

import numpy as np

from fieldshift.data.boundaries import province_geometries
from fieldshift.features.farmland_weights import MASK_YEARS, build_cell_weights, fixed_farmland_mask, zero_weight_cells

grids = {}
for y in MASK_YEARS:
    z = np.load(f"data/interim/modis_vn/MCD12C1_{y}_vn.npz")
    grids[y] = {
        "percent": z["percent"],
        "lat_max": float(z["lat_max"]),
        "lon_min": float(z["lon_min"]),
        "cell": float(z["cell"]),
    }
mask = fixed_farmland_mask(grids)
geoms = province_geometries(
    "data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson", "data/reference/admin_units.csv"
)
table, missing = build_cell_weights(geoms, mask)
table.to_csv("data/processed/cell_weights.csv", index=False)
with open("data/processed/cell_weights_zero.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["province_nso", "lat", "lon"])
    for prov, geom in sorted(geoms.items()):
        for la, lo in zero_weight_cells(geom, mask):
            w.writerow([prov, la, lo])
print("provinces:", table["province_nso"].nunique(), "| rows:", len(table), "| no farmland:", missing)
