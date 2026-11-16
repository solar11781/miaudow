"""The trial site's names after the 2025 change, in the rules texts the API serves (D-198).

Source: Resolution 1678/NQ-UBTVQH15 (16 June 2025), Article 1, item 20 (R-V10): Luu Son commune and eight other units
became Do Luong commune. The app's own sentences (the cards' "why" parts, the assistant's passages) call it the former
commune; facts about a source as published (`site`, the register's `place_years`) keep the study's own names.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
VI = re.compile(r"Lưu Sơn(?! \(cũ\))")
EN = re.compile(r"(?<![Ff]ormer )Luu Son")


def _texts(node: object) -> list[tuple[str, str]]:
    """Every (language, text) pair of a {vi, en} tree."""
    if isinstance(node, dict):
        if set(node) == {"vi", "en"} and all(isinstance(v, str) for v in node.values()):
            return [("vi", node["vi"]), ("en", node["en"])]
        return [pair for value in node.values() for pair in _texts(value)]
    if isinstance(node, list):
        return [pair for value in node for pair in _texts(value)]
    return []


def _unmarked(texts: list[tuple[str, str]]) -> list[str]:
    return [t for lang, t in texts if (VI if lang == "vi" else EN).search(t)]


def test_the_cards_why_parts_call_luu_son_the_former_commune() -> None:
    plans = yaml.safe_load((REPO / "rules" / "rotations.yaml").read_text(encoding="utf-8"))
    assert _unmarked([pair for plan in plans for pair in _texts(plan["why"])]) == []


def test_the_assistant_passages_call_luu_son_the_former_commune() -> None:
    copilot = yaml.safe_load((REPO / "rules" / "copilot.yaml").read_text(encoding="utf-8"))
    texts = [pair for p in copilot["passages"] for pair in _texts({"title": p["title"], "text": p["text"]})]
    assert _unmarked(texts) == []


def test_the_method_page_texts_call_luu_son_the_former_commune() -> None:
    method = yaml.safe_load((REPO / "rules" / "method.yaml").read_text(encoding="utf-8"))
    assert _unmarked(_texts(method)) == []


def test_the_studys_own_place_stays_as_the_study_wrote_it() -> None:
    plans = yaml.safe_load((REPO / "rules" / "rotations.yaml").read_text(encoding="utf-8"))
    assert {plan["site"] for plan in plans} == {"Lưu Sơn, Đô Lương"}
