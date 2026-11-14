"""Read the DesInventar Viet Nam XML export (R-A19) for the heavy-rain check E-016.

Plain words: DesInventar lists reported disaster losses, one record per event and place. D-54: we use it only to check
how well our heavy-rain years match years with recorded rice flood damage; its data are never committed or shown.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

RICE_DAMAGED_FIELD, RICE_DAMAGED_LABEL = "NN01", "Rice area damaged (ha)"  # R-A19 data dictionary (diccionario)
# R-A19 event types (eventos nombre_en) that name a flood: Lũ, Lũ quét, Lụt; "Storm" and others are left out (E-016)
FLOOD_EVENTS = ("Flood", "Flash flood", "Inundation")


def _rows(root: ET.Element, section: str) -> list[dict[str, str]]:
    node = root.find(section)
    if node is None:
        raise ValueError(f"DesInventar export has no section {section!r}")
    return [{c.tag: (c.text or "").strip() for c in r} for r in node]


def _read_export(zip_path: Path | str) -> ET.Element:
    """The root of the one XML file of the export zip."""
    with zipfile.ZipFile(zip_path) as z:
        members = [n for n in z.namelist() if n.lower().endswith(".xml")]
        if len(members) != 1:
            raise ValueError(f"{zip_path}: expected one XML export, found {members}")
        data = z.read(members[0])
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError(f"{zip_path}: the export declares a DTD or entities; refused (untrusted download)")
    return ET.fromstring(data)  # noqa: S314  no DTD or entity declarations (checked above), so no entity expansion


def rice_flood_damage_years(zip_path: Path | str, province: str, years: range) -> set[int]:
    """Years in `years` with a flood record (FLOOD_EVENTS) of `province` (lev0 name) whose rice area damaged is > 0."""
    root = _read_export(zip_path)
    labels = {r.get("nombre_campo", "").upper(): r.get("label_campo_en", "") for r in _rows(root, "diccionario")}
    if labels.get(RICE_DAMAGED_FIELD) != RICE_DAMAGED_LABEL:
        raise ValueError(
            f"field {RICE_DAMAGED_FIELD} is labelled {labels.get(RICE_DAMAGED_FIELD)!r}, not {RICE_DAMAGED_LABEL!r}"
        )
    codes = [r["lev0_cod"] for r in _rows(root, "lev0") if r.get("lev0_name") == province]
    if len(codes) != 1:
        raise ValueError(f"province {province!r} found {len(codes)} times in the DesInventar lev0 list")
    event_en = {r["nombre"]: r["nombre_en"] for r in _rows(root, "eventos")}
    damage = {r["clave_ext"]: r.get(RICE_DAMAGED_FIELD.lower(), "") for r in _rows(root, "extension")}
    found = set()
    for rec in _rows(root, "fichas"):
        if rec.get("level0") != codes[0]:
            continue
        if rec["evento"] not in event_en:
            raise ValueError(f"unknown event {rec['evento']!r} in record {rec['clave']}")
        year, text = int(rec["fechano"]), damage.get(rec["clave"], "")
        if event_en[rec["evento"]] not in FLOOD_EVENTS or year not in years or not text:
            continue
        try:
            hectares = float(text)
        except ValueError as err:
            raise ValueError(f"record {rec['clave']}: rice area damaged {text!r} is not a number") from err
        if hectares > 0:
            found.add(year)
    return found
