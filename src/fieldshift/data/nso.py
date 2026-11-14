"""Parse NSO PX-Web CSV exports into the tidy `crop_stats` table (docs/05-DATA-CONTRACTS.md section 2).

Plain words: each NSO file is a wide table (one row per province, one column per year) for ONE variable
(area, yield or production) of ONE crop-season. We turn all of them into a single long table with one row per
province x year x crop x season, in standard units (ha, t/ha, t), so that later code never has to remember that
NSO publishes rice area in thousand hectares but peanut area in hectares.

Units [DATA, checked 2026-11-10 by magnitude and by area x yield = production; the CSV export has no unit field]:
- rice and maize: area in thousand ha, yield in quintal/ha (1 quintal = 100 kg), production in thousand tonnes
- peanut: area in ha, production in tonnes (no yield table; yield is derived and flagged)
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

MISSING_SYMBOLS = {"..", "...", "-", ""}
HEADER_ROWS = 2  # an export starts with the table title row, then the column heading row

# NSO aggregate rows that are not provinces.
REGION_ROWS = {
    "WHOLE COUNTRY",
    "Red River Delta",
    "Northern midlands and mountain areas",
    "North Central and Central coastal areas",
    "Central Highlands",
    "South East",
    "Mekong River Delta",
}


@dataclass(frozen=True)
class TableSpec:
    crop: str
    season: str  # spring, autumn, winter, annual (NSO season names; see ASSUMPTIONS A-02)
    variable: str  # planted_area_ha, yield_t_ha, production_t
    factor: float  # multiply the NSO value by this to get the standard unit


TABLES: dict[str, TableSpec] = {
    "E06.13": TableSpec("rice", "annual", "planted_area_ha", 1000.0),
    "E06.14": TableSpec("rice", "annual", "yield_t_ha", 0.1),
    "E06.15": TableSpec("rice", "annual", "production_t", 1000.0),
    "E06.16": TableSpec("rice", "spring", "planted_area_ha", 1000.0),
    "E06.17": TableSpec("rice", "spring", "yield_t_ha", 0.1),
    "E06.18": TableSpec("rice", "spring", "production_t", 1000.0),
    "E06.19": TableSpec("rice", "autumn", "planted_area_ha", 1000.0),
    "E06.20": TableSpec("rice", "autumn", "yield_t_ha", 0.1),
    "E06.21": TableSpec("rice", "autumn", "production_t", 1000.0),
    "E06.22": TableSpec("rice", "winter", "planted_area_ha", 1000.0),
    "E06.23": TableSpec("rice", "winter", "yield_t_ha", 0.1),
    "E06.24": TableSpec("rice", "winter", "production_t", 1000.0),
    "E06.25": TableSpec("maize", "annual", "planted_area_ha", 1000.0),
    "E06.26": TableSpec("maize", "annual", "yield_t_ha", 0.1),
    "E06.27": TableSpec("maize", "annual", "production_t", 1000.0),
    "E06.34": TableSpec("peanut", "annual", "planted_area_ha", 1.0),
    "E06.35": TableSpec("peanut", "annual", "production_t", 1.0),
}

KEY = ["province_nso", "year", "crop", "season"]

# NSO files spell some provinces differently (double spaces, "TP." prefix, missing hyphen) [DATA, 2026-11-11].
# Canonical form = the spelling used in most tables.
NAME_ALIASES = {
    "TP. Ho Chi Minh": "Ho Chi Minh city",
    "Thua Thien Hue": "Thua Thien-Hue",
}


def canonical_province(name: str) -> str:
    """Collapse repeated whitespace and map known spelling variants to one canonical NSO English name."""
    name = " ".join(name.split())
    return NAME_ALIASES.get(name, name)


def _to_number(text: str) -> float:
    text = text.strip()
    if text in MISSING_SYMBOLS:
        return np.nan
    return float(text)


def parse_export(raw: bytes) -> pd.DataFrame:
    """Parse one PX-Web 'CSV with heading and comma' export into long form: province_nso, year_label, value.

    Some exports contain stray NUL bytes; they are removed before parsing.
    """
    text = raw.replace(b"\x00", b"").decode("utf-8-sig")
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if len(rows) <= HEADER_ROWS:
        raise ValueError("export has no data rows")
    header = rows[1]  # rows[0] is the table title
    year_labels = [h.strip() for h in header[1:]]
    records = []
    for row in rows[HEADER_ROWS:]:
        name = canonical_province(row[0])
        if name in REGION_ROWS:
            continue
        if len(row) != len(header):
            raise ValueError(f"row for {name!r} has {len(row)} cells, header has {len(header)}")
        for label, cell in zip(year_labels, row[1:], strict=True):
            records.append((name, label, _to_number(cell)))
    return pd.DataFrame(records, columns=["province_nso", "year_label", "value"])


def _year(label: str) -> tuple[int, bool]:
    """'2024' -> (2024, False); 'Prel. 2025' -> (2025, True)."""
    if label.startswith("Prel."):
        return int(label.rsplit(maxsplit=1)[-1]), True
    return int(label), False


def retrieval_dates(manifest: Path | str, raw_dir: Path | str) -> dict[str, str]:
    """{table id: retrieved_on} for each NSO export in raw_dir, from the data/MANIFEST.csv row whose sha256 matches.

    A file with no matching row (for example a new export not yet recorded) is refused: the date is never guessed.
    """
    raw_dir = Path(raw_dir)
    with open(manifest, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for table_id in TABLES:
        path = raw_dir / f"{table_id}.csv"
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        dates = {r["retrieved_on"] for r in rows if r["table"] == table_id and r["sha256"] == digest}
        if len(dates) != 1:
            raise ValueError(
                f"{table_id}: {len(dates)} MANIFEST rows match the sha256 of {path} (need exactly one date)"
            )
        out[table_id] = dates.pop()
    return out


def build_crop_stats(raw_dir: Path | str, retrieved_on: str | Mapping[str, str]) -> pd.DataFrame:
    """Combine all known NSO exports in raw_dir into the crop_stats table (one row per province-year-crop-season).

    retrieved_on: one date for every table, or {table id: date} (retrieval_dates). A row built from tables retrieved
    on different dates is refused, because one retrieved_on could not describe it.
    """
    raw_dir = Path(raw_dir)
    parts = []
    for table_id, spec in TABLES.items():
        path = raw_dir / f"{table_id}.csv"
        if not path.exists():
            continue
        long = parse_export(path.read_bytes())
        parsed = long["year_label"].map(_year)
        long["year"] = parsed.map(lambda t: t[0])
        long["is_preliminary"] = parsed.map(lambda t: t[1])
        long["crop"], long["season"] = spec.crop, spec.season
        long["variable"] = spec.variable
        long["value"] = long["value"] * spec.factor
        long["source_table"] = table_id
        parts.append(long.drop(columns="year_label"))
    if not parts:
        raise FileNotFoundError(f"no NSO exports found in {raw_dir}")
    allrows = pd.concat(parts, ignore_index=True)

    wide = allrows.pivot_table(
        index=[*KEY, "is_preliminary"], columns="variable", values="value", aggfunc="first", dropna=False
    ).reset_index()
    wide.columns.name = None
    for col in ["planted_area_ha", "yield_t_ha", "production_t"]:
        if col not in wide:
            wide[col] = np.nan
    sources = allrows.groupby(KEY)["source_table"].apply(lambda s: ",".join(sorted(set(s)))).rename("source_table")
    wide = wide.merge(sources, on=KEY, how="left")

    # Peanut has no yield table: derive yield = production / planted area and flag it (ASSUMPTIONS A-14).
    # Official blank yields for other crops stay blank (team decision D-33 C).
    derive = (
        (wide["crop"] == "peanut")
        & wide["yield_t_ha"].isna()
        & wide["production_t"].notna()
        & (wide["planted_area_ha"] > 0)
    )
    wide.loc[derive, "yield_t_ha"] = wide.loc[derive, "production_t"] / wide.loc[derive, "planted_area_ha"]
    wide["yield_derived"] = derive

    wide = wide.dropna(subset=["planted_area_ha", "yield_t_ha", "production_t"], how="all")
    if isinstance(retrieved_on, str):
        wide["retrieved_on"] = retrieved_on
    else:
        dates = wide["source_table"].map(lambda ids: {retrieved_on[t] for t in ids.split(",")})
        mixed = dates.map(len) > 1
        if mixed.any():
            raise ValueError(
                f"tables retrieved on different dates in one row: {wide.loc[mixed, 'source_table'].iloc[0]}"
            )
        wide["retrieved_on"] = dates.map(min)
    cols = [
        *KEY,
        "is_preliminary",
        "planted_area_ha",
        "yield_t_ha",
        "production_t",
        "yield_derived",
        "source_table",
        "retrieved_on",
    ]
    return wide[cols].sort_values(KEY).reset_index(drop=True)


def consistency_ratio(df: pd.DataFrame) -> pd.Series:
    """production / (area x yield); about 1.0 means the units are right.

    Contract (documented 2026-11-11): only rows with all three values, area > 0, yield > 0 and a published (not
    derived, `yield_derived` False) yield; derived-yield rows equal 1 by construction and are excluded.
    """
    ok = ~df["yield_derived"] & df[["planted_area_ha", "yield_t_ha", "production_t"]].notna().all(axis=1)
    sub = df[ok & (df["planted_area_ha"] > 0) & (df["yield_t_ha"] > 0)]
    return sub["production_t"] / (sub["planted_area_ha"] * sub["yield_t_ha"])
