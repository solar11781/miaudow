"""Read the built canonical files once (data/canonical/*.json); a missing file raises CanonicalMissing.

The crop keys of hazards.json and soil.json are the web app's keys (kept for byte-level parity with the web builder);
CROP_KEYS maps each to the crop_key of the team rulebook (data/rules/rotations.yaml, api/rules/rotations.yaml).
"""

from __future__ import annotations

import json
from functools import lru_cache

from .paths import BUILD_COMMAND, canonical_dir

FILES = (
    "hazards.json",
    "soil.json",
    "geo.json",
    "model.json",
    "climate.json",
    "catalog.json",
    "rotations.generated.json",
    "passages.json",
)

# web crop key (hazards.json, soil.json) -> team crop_key (rotations.yaml)
CROP_KEYS = {
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
TEAM_TO_WEB = {v: k for k, v in CROP_KEYS.items()}


class CanonicalMissing(RuntimeError):
    """A canonical file is missing; the API answers 503 and names the build command."""


@lru_cache(maxsize=32)
def load(name: str) -> dict:
    path = canonical_dir() / name
    if not path.exists():
        raise CanonicalMissing(f"data/canonical/{name} is missing; build it with: {BUILD_COMMAND}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(name: str) -> dict | None:
    """A Phase-2 canonical file (vegetation, MODIS NDVI, GIBS layers, quality) or None when it was not built yet;
    callers turn None into an explicit unavailable state instead of a 503."""
    try:
        return load(name)
    except CanonicalMissing:
        return None


def missing_files() -> list[str]:
    return [name for name in FILES if not (canonical_dir() / name).exists()]


def web_crop_key(key: str) -> str:
    """Accept either key style and return the web key used by hazards.json and soil.json."""
    if key in CROP_KEYS:
        return key
    if key in TEAM_TO_WEB:
        return TEAM_TO_WEB[key]
    raise ValueError(f"unknown crop key {key!r}")


def clear() -> None:
    load.cache_clear()
