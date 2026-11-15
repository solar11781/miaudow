"""English text writes place names without accent marks (D-186, D-191); Vietnamese text keeps them.

Paper and document titles, people's names, official names, credit lines and quoted text stay verbatim: an English
string equal to its Vietnamese one, text inside quotation marks and the fragments in VERBATIM are not checked.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ACCENTED = re.compile(
    r"Nghệ|Lưu Sơn|Đô Lương|Hà Tĩnh|Thanh Hó|Thanh Hoá|Bắc [bB]ộ|Trung [bB]ộ|Nam [bB]ộ|Tây Nguyên|Hà Tây|Tĩnh Gia"
    r"|Quan Hóa|Việt Nam|Viet Nam|Điều \d|tên bài báo|\bmùa\b"
)
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
# Vietnamese titles of papers, journals and books, and an official database name, quoted inside English citations
VERBATIM = (
    "tại tỉnh Nghệ An",
    "Đặc san KH&CN Nghệ An",
    "Tạp chí Khoa học và Công nghệ Nông nghiệp Việt Nam",
    "Những cây thuốc và vị thuốc Việt Nam",
    "Viet Nam national disaster loss database",
    "Nghệ An S&T",
)


def _english(node, found):
    if isinstance(node, dict):
        en, vi = node.get("en"), node.get("vi")
        if isinstance(en, str) and en != vi:
            found.append(en)
        for value in node.values():
            _english(value, found)
    elif isinstance(node, list):
        for value in node:
            _english(value, found)
    return found


def _accented(text):
    text = QUOTED.sub("", text)
    for fragment in VERBATIM:
        text = text.replace(fragment, "")
    return ACCENTED.findall(text)


FILES = sorted((ROOT / "rules").glob("*.yaml")) + sorted((ROOT / "frontend" / "data" / "canonical").glob("*.json"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_english_fields_write_place_names_without_accents(path):
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    bad = [s for s in _english(data, []) if _accented(s)]
    assert bad == []
