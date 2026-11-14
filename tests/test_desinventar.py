"""Tests for the DesInventar export reader (E-016, D-54: checking only, its data are never committed).

The toy export below is written by this test in the layout of the DesInventar XML export (R-A19: sections lev0,
eventos, diccionario, fichas, extension; the dictionary labels field NN01 "Rice area damaged (ha)"); its records are
invented, not DesInventar data.
"""

import csv
import hashlib
import zipfile
from pathlib import Path

import pytest

from fieldshift.data import desinventar
from fieldshift.data.desinventar import rice_flood_damage_years

DICTIONARY = (
    "<diccionario><TR><nombre_campo>NN01</nombre_campo><label_campo_en>{label}</label_campo_en></TR></diccionario>"
)


def _record(serial: str, province: str, event: str, year: str) -> str:
    return (
        f"<TR><level0>{province}</level0><evento>{event}</evento><fechano>{year}</fechano><clave>{serial}</clave></TR>"
    )


def _export(tmp_path: Path, records: list[tuple[str, str, str, str, str]], label="Rice area damaged (ha)") -> Path:
    """records: (key, province code, event name, year, NN01 text)."""
    xml = (
        "<?xml version='1.0' encoding='UTF-8'?><DESINVENTAR>"
        "<eventos><TR><nombre>Lũ</nombre><nombre_en>Flood</nombre_en></TR>"
        "<TR><nombre>Lũ quét</nombre><nombre_en>Flash flood</nombre_en></TR>"
        "<TR><nombre>Lụt</nombre><nombre_en>Inundation</nombre_en></TR>"
        "<TR><nombre>Bão</nombre><nombre_en>Storm</nombre_en></TR></eventos>"
        "<lev0><TR><lev0_cod>403</lev0_cod><lev0_name>Nghệ An</lev0_name></TR>"
        "<TR><lev0_cod>405</lev0_cod><lev0_name>Hà Tĩnh</lev0_name></TR></lev0>"
        + DICTIONARY.format(label=label)
        + "<fichas>"
        + "".join(_record(k, p, e, y) for k, p, e, y, _ in records)
        + "</fichas><extension>"
        + "".join(f"<TR><clave_ext>{k}</clave_ext><nn01>{v}</nn01></TR>" for k, _, _, _, v in records)
        + "</extension></DESINVENTAR>"
    )
    path = tmp_path / "DI_export_toy.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("DI_export_toy.xml", xml)
    return path


def _zip(tmp_path: Path, name: str, xml: bytes) -> Path:
    path = tmp_path / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name.replace(".zip", ".xml"), xml)
    return path


def _years(path: Path, province: str = "Nghệ An", record: bool = True) -> set[int]:
    """rice_flood_damage_years with a toy manifest that records `path` (or records another version of it)."""
    manifest = path.parent / "MANIFEST.csv"
    sha = hashlib.sha256(path.read_bytes() if record else b"another version").hexdigest()
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["path", "source_id", "table", "title", "url", "retrieved_on", "method", "sha256"])
        w.writerow([path.as_posix(), "desinventar", "", "toy", "https://x/toy.zip", "2026-11-14", "test", sha])
    return rice_flood_damage_years(path.as_posix(), province, range(1995, 2009), manifest=manifest)


def test_years_with_rice_area_damaged_by_a_flood_flash_flood_or_inundation(tmp_path: Path):
    path = _export(
        tmp_path,
        [
            ("1", "403", "Lũ", "2000", "120"),  # flood with damage: counted
            ("2", "403", "Lũ quét", "2001", "5"),  # flash flood: counted
            ("3", "403", "Lụt", "2002", "0.5"),  # inundation: counted
            ("4", "403", "Bão", "2003", "900"),  # storm: not a flood record
            ("5", "403", "Lũ", "2004", "0"),  # flood without rice damage
            ("6", "403", "Lũ", "2005", ""),  # no value recorded
            ("7", "405", "Lũ", "2006", "300"),  # another province
            ("8", "403", "Lũ", "1990", "300"),  # outside the period
        ],
    )
    assert _years(path) == {2000, 2001, 2002}


def test_unknown_event_province_or_field_label_fails_loudly(tmp_path: Path):
    with pytest.raises(ValueError, match="unknown event"):
        _years(_export(tmp_path, [("1", "403", "Mưa", "2000", "1")]))
    with pytest.raises(ValueError, match="province"):
        _years(_export(tmp_path, []), "Quảng Bình")
    with pytest.raises(ValueError, match="NN01"):
        _years(_export(tmp_path, [], label="Rice (ton(s))"))
    with pytest.raises(ValueError, match="not a number"):
        _years(_export(tmp_path, [("1", "403", "Lũ", "2000", "n/a")]))


def test_an_export_with_a_doctype_or_entities_is_refused_inside_the_parser(tmp_path: Path):
    # security: an untrusted download may declare entities that expand without bound; a real export declares none.
    # The parser itself refuses, so a UTF-16 file (where a byte search for "<!DOCTYPE" finds nothing) is refused too.
    entity = '<?xml version="1.0"?><!DOCTYPE a [<!ENTITY e "x">]><a>&e;</a>'
    with pytest.raises(ValueError, match="refused"):
        _years(_zip(tmp_path, "bad.zip", entity.encode("utf-8")))
    utf16 = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE a><a/>'.encode("utf-16")
    with pytest.raises(ValueError, match="refused"):
        _years(_zip(tmp_path, "bad16.zip", utf16))


def test_an_oversized_xml_member_is_refused_before_it_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(desinventar, "MAX_XML_BYTES", 100)
    with pytest.raises(ValueError, match="larger than"):
        _years(_zip(tmp_path, "big.zip", b"<a>" + b" " * 200 + b"</a>"))


def test_a_download_that_is_not_the_recorded_version_is_refused(tmp_path: Path):
    with pytest.raises(ValueError, match="does not match"):
        _years(_export(tmp_path, []), record=False)
