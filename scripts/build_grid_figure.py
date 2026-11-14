"""Write artifacts/figures/nghe_an_grid.svg from data/processed/cell_weights.csv, cell_weights_zero.csv and the boundary.

UI-UX-SPEC section 11b item 4 grid figure (D-135). Usage: PYTHONPATH=src python scripts/build_grid_figure.py
(after scripts/build_cell_weights.py; the boundary file comes from scripts/fetch_recorded.py)
"""

from pathlib import Path

import pandas as pd

from fieldshift.data.boundaries import province_geometries
from fieldshift.ml.grid_figure import PROVINCE, grid_figure_svg

table = pd.read_csv("data/processed/cell_weights.csv")
zero_table = pd.read_csv("data/processed/cell_weights_zero.csv")
boundary = province_geometries(
    "data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson", "data/reference/admin_units.csv"
)[PROVINCE]
out = Path("artifacts/figures/nghe_an_grid.svg")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(grid_figure_svg(table, zero_table, boundary), encoding="utf-8", newline="\n")
print("wrote", out, "|", out.read_text(encoding="utf-8").count("data-cell="), "cells")
