"""Farmland weights of NASA POWER cells for a province (D-26, D-27, D-36).

Plain words: a province overlaps several NASA weather cells. We want the province's weather to describe where its
farms are, so each cell gets a weight = (farmland inside the province AND that cell) / (all farmland in the province).
Farmland comes from NASA MODIS land cover MCD12C1 (percent of IGBP classes per 0.05 deg pixel): class 12 (croplands,
"At least 60% of area is cultivated cropland" in the MCD12 user guide) counts at 80%, the middle of 60-100% (D-146), and
class 14 (cropland/natural vegetation mosaics, "small-scale cultivation 40-60%") at 50% (D-107). One fixed mask is used for every year: each pixel's minimum farmland fraction over 2001-2015,
i.e. farmland present in every year before the first test year (D-106; a map from 2016 or later would leak).

Routine choices (D-36): a MODIS pixel belongs to the province and POWER cell that contain its centre point (pixel
centres never fall on POWER cell edges because centres sit at x.x25 / x.x75 degrees); each pixel is weighted by its
ground area, proportional to cos(latitude). A province with no farmland raises ValueError (never guessed).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shapely
from shapely.geometry.base import BaseGeometry

POWER_DLAT = 0.5  # verified 2026-11-11: cells centred on multiples of 0.5 deg latitude
POWER_DLON = 0.625  # and 0.625 deg longitude
CLASS_WEIGHTS = {12: 0.8, 14: 0.5}  # D-27; class 12: D-146; class 14: D-107
MASK_YEARS = tuple(range(2001, 2016))  # D-106


def power_cell_centre(lat: float, lon: float) -> tuple[float, float]:
    """Centre of the NASA POWER meteorology cell containing (lat, lon)."""
    clat = float(np.floor(lat / POWER_DLAT + 0.5)) * POWER_DLAT
    clon = float(np.floor(lon / POWER_DLON + 0.5)) * POWER_DLON
    return round(clat, 6), round(clon, 6)


def farmland_fraction(percent: np.ndarray) -> np.ndarray:
    """Farmland fraction 0..1 per pixel from the (rows, cols, 17) percent array (D-27, D-107)."""
    frac = np.zeros(percent.shape[:2], dtype=float)
    for cls, wt in CLASS_WEIGHTS.items():
        frac += wt * percent[:, :, cls].astype(float)
    return frac / 100.0


def fixed_farmland_mask(grids: dict[int, dict]) -> dict:
    """One fixed mask: per pixel, the minimum farmland fraction over exactly the years 2001-2015 (D-106)."""
    if tuple(sorted(grids)) != MASK_YEARS:
        raise ValueError(
            f"the fixed mask needs exactly the land-cover years {MASK_YEARS[0]}-{MASK_YEARS[-1]} (D-106); "
            f"got {sorted(grids)}"
        )
    first = grids[MASK_YEARS[0]]
    geo = (first["lat_max"], first["lon_min"], first["cell"], first["percent"].shape)
    for y, g in grids.items():
        if (g["lat_max"], g["lon_min"], g["cell"], g["percent"].shape) != geo:
            raise ValueError(f"land-cover grid of {y} does not match {MASK_YEARS[0]}")
    farmland = np.min(np.stack([farmland_fraction(grids[y]["percent"]) for y in MASK_YEARS]), axis=0)
    return {"farmland": farmland, "lat_max": first["lat_max"], "lon_min": first["lon_min"], "cell": first["cell"]}


def _pixels(geom: BaseGeometry, grid: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Pixel centres inside the geometry's bounding box: (lat grid, lon grid, inside mask, farmland fraction)."""
    farm_all = grid["farmland"] if "farmland" in grid else farmland_fraction(grid["percent"])
    lat_max, lon_min, cell = grid["lat_max"], grid["lon_min"], grid["cell"]
    minx, miny, maxx, maxy = geom.bounds
    r0 = max(int(np.floor((lat_max - maxy) / cell)), 0)
    r1 = min(int(np.ceil((lat_max - miny) / cell)), farm_all.shape[0])
    c0 = max(int(np.floor((minx - lon_min) / cell)), 0)
    c1 = min(int(np.ceil((maxx - lon_min) / cell)), farm_all.shape[1])
    lats = lat_max - (np.arange(r0, r1) + 0.5) * cell
    lons = lon_min + (np.arange(c0, c1) + 0.5) * cell
    lon_g, lat_g = np.meshgrid(lons, lats)
    inside = shapely.contains_xy(geom, lon_g, lat_g)
    return lat_g, lon_g, inside, farm_all[r0:r1, c0:c1]


def _cell_keys(lat_g: np.ndarray, lon_g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    clat = np.floor(lat_g / POWER_DLAT + 0.5) * POWER_DLAT
    clon = np.floor(lon_g / POWER_DLON + 0.5) * POWER_DLON
    return clat, clon


def province_cell_weights(geom: BaseGeometry, grid: dict) -> dict[tuple[float, float], float]:
    """Farmland weight per POWER cell centre for one province geometry.

    grid: a fixed mask dict(farmland=(rows, cols) fraction 0..1, lat_max, lon_min, cell), or a single-year
    dict(percent=(rows, cols, 17), ...). Returns {(cell_lat, cell_lon): weight} summing to 1; cells with no farmland are
    omitted (see zero_weight_cells).
    """
    lat_g, lon_g, inside, farm = _pixels(geom, grid)
    amount = farm * np.cos(np.radians(lat_g)) * inside
    total = amount.sum()
    if total <= 0:
        raise ValueError("province has no farmland pixels; weights are undefined (ask the team, D-36)")
    clat, clon = _cell_keys(lat_g, lon_g)
    weights: dict[tuple[float, float], float] = {}
    for la, lo, a in zip(clat[amount > 0], clon[amount > 0], amount[amount > 0], strict=True):
        key = (round(float(la), 6), round(float(lo), 6))
        weights[key] = weights.get(key, 0.0) + float(a)
    return {k: v / total for k, v in weights.items()}


def zero_weight_cells(geom: BaseGeometry, grid: dict) -> list[tuple[float, float]]:
    """POWER cells that contain pixel centres of the province but no farmland (reported, 03-ML-SPEC §4)."""
    lat_g, lon_g, inside, farm = _pixels(geom, grid)
    clat, clon = _cell_keys(lat_g, lon_g)
    totals: dict[tuple[float, float], float] = {}
    for la, lo, f in zip(clat[inside], clon[inside], farm[inside], strict=True):
        key = (round(float(la), 6), round(float(lo), 6))
        totals[key] = totals.get(key, 0.0) + float(f)
    return sorted(k for k, v in totals.items() if v <= 0)


def build_cell_weights(geoms: dict[str, BaseGeometry], mask: dict) -> tuple[pd.DataFrame, list[str]]:
    """Cell weights for every province from the fixed mask (05-DATA-CONTRACTS §3). Returns (table, missing provinces)."""

    rows, missing = [], []
    for prov, geom in sorted(geoms.items()):
        try:
            w = province_cell_weights(geom, mask)
        except ValueError:
            missing.append(prov)
            continue
        rows += [(prov, f"{la}_{lo}", la, lo, wt, "farmland_weighted") for (la, lo), wt in sorted(w.items())]
    table = pd.DataFrame(rows, columns=["province_nso", "cell_id", "lat", "lon", "farmland_weight", "method"])
    return table, missing
