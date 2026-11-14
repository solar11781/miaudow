"""Match province boundary shapes (geoBoundaries VNM ADM1) to canonical NSO province names.

Why: farmland-weighted weather (D-26) needs one shape per NSO province. The boundary file spells names in Vietnamese
with its own conventions; data/reference/admin_units.csv holds the canonical NSO name and the Vietnamese name.
Unknown names raise KeyError: never guess a match.

Known differences (observed 2026-11-11): "Hà Nội\\t" has a stray tab; the name of Bà Rịa - Vũng Tàu joins its two parts with an en dash (U+2013);
"Ho Chi Minh" is ASCII; "Côn Đảo" is listed separately although it was a district of Bà Rịa - Vũng Tàu before
2025-07-01 (D-35), so it is merged into that province.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

# Names whose spelling cannot be matched by normalization alone (source in the module docstring).
ALIASES = {
    "côn đảo": "Ba Ria - Vung Tau",
    "ho chi minh": "Ho Chi Minh city",
}


def _norm(name: str) -> str:
    name = unicodedata.normalize("NFC", name).replace("\u2013", "-").replace("—", "-")
    name = re.sub(r"\s*-\s*", "-", " ".join(name.split()))
    return name.lower()


@lru_cache(maxsize=4)
def _lookup(admin_csv: str) -> dict[str, str]:
    admin = pd.read_csv(admin_csv)
    table: dict[str, str] = {}
    for nso, vi in zip(admin["province_nso"], admin["name_vi"], strict=True):
        table[_norm(vi)] = nso
        table[_norm(nso)] = nso
    return table


def match_boundary_name(shape_name: str, admin_csv: Path | str) -> str:
    """Canonical NSO province name for a boundary shape name; KeyError if unknown."""
    key = _norm(shape_name)
    if key in ALIASES:
        return ALIASES[key]
    table = _lookup(str(admin_csv))
    if key not in table:
        raise KeyError(f"no NSO province matches boundary name {shape_name!r}")
    return table[key]


def province_geometries(geojson_path: Path | str, admin_csv: Path | str) -> dict[str, BaseGeometry]:
    """One shapely geometry per NSO province (shapes of the same province are merged)."""
    features = json.loads(Path(geojson_path).read_text(encoding="utf-8"))["features"]
    parts: dict[str, list] = {}
    for f in features:
        parts.setdefault(match_boundary_name(f["properties"]["shapeName"], admin_csv), []).append(shape(f["geometry"]))
    return {prov: unary_union(geoms) for prov, geoms in parts.items()}
