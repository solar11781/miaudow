"""Write the grid figure in English and Vietnamese: artifacts/figures/nghe_an_grid.svg and nghe_an_grid.vi.svg.

Reads data/processed/cell_weights.csv, cell_weights_zero.csv and the boundary. UI-UX-SPEC section 11b item 4 grid
figure (D-135). Usage: PYTHONPATH=src python scripts/build_grid_figure.py
(after scripts/build_cell_weights.py; the boundary file comes from scripts/fetch_recorded.py)
"""

from pathlib import Path

import pandas as pd

from fieldshift.data.boundaries import province_geometries
from fieldshift.ml.grid_figure import PROVINCE, grid_figure_svg

table = pd.read_csv("data/processed/cell_weights.csv", float_precision="round_trip")
zero_table = pd.read_csv("data/processed/cell_weights_zero.csv", float_precision="round_trip")
boundary = province_geometries(
    "data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson", "data/reference/admin_units.csv"
)[PROVINCE]
out_dir = Path("artifacts/figures")
out_dir.mkdir(parents=True, exist_ok=True)
for name, lang in (("nghe_an_grid.svg", "en"), ("nghe_an_grid.vi.svg", "vi")):
    out = out_dir / name
    out.write_text(grid_figure_svg(table, zero_table, boundary, lang), encoding="utf-8", newline="\n")
    print("wrote", out, "|", out.read_text(encoding="utf-8").count("data-cell="), "cells")
