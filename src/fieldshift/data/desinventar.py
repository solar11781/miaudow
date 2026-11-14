"""Read the DesInventar Viet Nam XML export (R-A19) for the heavy-rain check E-016.

Plain words: DesInventar lists reported disaster losses, one record per event and place. D-54: we use it only to check
how well our heavy-rain years match years with recorded rice flood damage; its data are never committed or shown.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.parsers import expat

from fieldshift.data.manifest import MANIFEST, check_recorded

RICE_DAMAGED_FIELD, RICE_DAMAGED_LABEL = "NN01", "Rice area damaged (ha)"  # R-A19 data dictionary (diccionario)
# R-A19 event types (eventos nombre_en) that name a flood: Lũ, Lũ quét, Lụt. D-54 checks "recorded rice flood damage",
# so storm records ("Storm", "Typhoon") and the others are not counted (E-016)
FLOOD_EVENTS = ("Flood", "Flash flood", "Inundation")
# memory bound for an untrusted download (a zip can inflate far beyond its size): the recorded export's XML is
# 19,494,076 bytes (data/MANIFEST.csv version, 2026-11-14), so 64 MiB leaves room for a larger later export
MAX_XML_BYTES = 64 * 1024 * 1024
ROW_DEPTH, FIELD_DEPTH = 3, 4  # DESINVENTAR > section > TR > field


def _refuse(*_args: object) -> None:
    raise ValueError("the export declares a DTD or entities; refused (untrusted download)")


def _sections(data: bytes) -> dict[str, list[dict[str, str]]]:
    """{section: [row {field: text}]} of the export; the parser refuses any DOCTYPE or entity declaration."""
    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = _refuse
    parser.EntityDeclHandler = _refuse
    sections: dict[str, list[dict[str, str]]] = {}
    path: list[str] = []
    text: list[str] = []

    def start(name: str, _attrs: dict) -> None:
        path.append(name)
        if len(path) == ROW_DEPTH:
            sections.setdefault(path[1], []).append({})
        elif len(path) == FIELD_DEPTH:
            text.clear()

    def end(name: str) -> None:
        if len(path) == FIELD_DEPTH:
            sections[path[1]][-1][name] = "".join(text).strip()
        path.pop()

    def chars(data: str) -> None:
        if len(path) == FIELD_DEPTH:
            text.append(data)

    parser.StartElementHandler, parser.EndElementHandler, parser.CharacterDataHandler = start, end, chars
    parser.Parse(data, True)
    return sections


def _read_export(zip_path: str, manifest: Path | str) -> dict[str, list[dict[str, str]]]:
    """The sections of the one XML file of the export zip, after its sha256 matched the manifest."""
    check_recorded(zip_path, manifest)
    with zipfile.ZipFile(zip_path) as z:
        members = [i for i in z.infolist() if i.filename.lower().endswith(".xml")]
        if len(members) != 1:
            raise ValueError(f"{zip_path}: expected one XML export, found {[i.filename for i in members]}")
        with z.open(members[0]) as f:
            data = f.read(MAX_XML_BYTES + 1)  # the header size can be wrong: read at most one byte past the cap
    if len(data) > MAX_XML_BYTES:
        raise ValueError(f"{zip_path}: XML export larger than {MAX_XML_BYTES} bytes; refused (untrusted download)")
    return _sections(data)


def _rows(sections: dict[str, list[dict[str, str]]], name: str) -> list[dict[str, str]]:
    if name not in sections:
        raise ValueError(f"DesInventar export has no section {name!r}")
    return sections[name]


def rice_flood_damage_years(zip_path: str, province: str, years: range, manifest: Path | str = MANIFEST) -> set[int]:
    """Years in `years` with a flood record (FLOOD_EVENTS) of `province` (lev0 name) whose rice area damaged is > 0.

    zip_path: the path recorded in the manifest; a file whose sha256 is not the recorded one is refused."""
    root = _read_export(zip_path, manifest)
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
