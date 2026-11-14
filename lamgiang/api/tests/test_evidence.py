"""Core 02: normalisation, abstention, and passages whose numbers equal the canonical data."""

import re

import pytest

from miaudow_api import canonical, evidence, knowledge


def test_normalize_strips_diacritics_and_d_bar():
    assert evidence.normalize("Hạn HÁN, đất!") == "han han dat"
    assert evidence.has_diacritics("hạn hán")
    assert evidence.has_diacritics("đât")
    assert not evidence.has_diacritics("han han")


def test_tokens_drop_stop_words_and_add_synonym_keys():
    toks = evidence.tokens("Lúa của tôi có bị hạn không?", accented=True)
    assert "của" not in toks
    assert "tôi" not in toks
    assert "lúa" in toks
    assert "k_lua" in toks
    assert "k_han" in toks


@pytest.mark.parametrize(
    "question",
    [
        "Cách nấu phở bò ngon?",
        "How do I fix my laptop screen?",
        "Mua xe máy Honda ở đâu rẻ?",
        "câu hỏi không liên quan xe hơi",
    ],
)
def test_unrelated_questions_abstain(question):
    res = evidence.search(question)
    assert res.abstained
    assert res.hits == []


@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("Thời tiết ngày mai ở Đô Lương thế nào?", "forecast_not_available"),
        ("Giá phân bón hiện nay bao nhiêu?", "current_price_not_available"),
        ("Cơ cấu nào tốt nhất cho ruộng tôi?", "ranking_not_supported"),
        ("Which plan is best for me?", "ranking_not_supported"),
    ],
)
def test_scope_guard_abstains_on_forecasts_prices_and_ranking(question, reason):
    res = evidence.search(question)
    assert res.abstained
    assert res.reason == reason


def test_answerable_question_finds_the_passage():
    res = evidence.search("How much water does peanut need?", 3)
    assert not res.abstained
    assert res.hits[0].passage.passage_id.startswith("water-peanut")
    plain = evidence.search("nam 2010 co han khong", 3)
    assert not plain.abstained
    assert any(h.passage.passage_id in ("hazards-2010", "climate-2010") for h in plain.hits)


def test_passage_lookup():
    assert evidence.passage("legumes").source_id == "R-B01"
    assert evidence.passage("nope") is None


def test_no_embedder_is_the_default():
    idx = evidence.default_index()
    assert idx.embedder is None
    assert isinstance(evidence.NoEmbedder(), evidence.NoEmbedder)


def _num(pattern: str, text: str, lang: str) -> float:
    m = re.search(pattern, text)
    assert m, pattern
    return knowledge.parse_number(m.group(1), lang)


@pytest.mark.parametrize("year", [1991, 1998, 2008, 2020, 2024])
def test_climate_passages_equal_climate_json(year):
    row = canonical.load("climate.json")["series"]["farmland_weighted"][str(year)]
    p = evidence.passage(f"climate-{year}")
    vi, en = p.text.vi, p.text.en
    assert _num(r"tổng mưa năm ([\d\.,]+) mm", vi, "vi") == row["annual_rain_mm"]
    assert _num(r"annual rain ([\d\.,]+) mm", en, "en") == row["annual_rain_mm"]
    assert _num(r"số ngày nóng từ 35 °C: ([\d\.,]+) ngày", vi, "vi") == row["hot_days"]
    assert _num(r"số ngày lạnh đến 13 °C: ([\d\.,]+) ngày", vi, "vi") == row["cold_days"]
    assert _num(r"đợt khô dài nhất \(mưa dưới 1 mm\): ([\d\.,]+) ngày", vi, "vi") == row["longest_dry_spell_days"]
    assert "không phải số đo tại ruộng" in vi
    assert "không phải dự báo" in vi


@pytest.mark.parametrize("year", [1995, 2010, 2024])
def test_hazard_passages_equal_hazards_json(year):
    hz = canonical.load("hazards.json")
    i = hz["years"].index(year)
    text = evidence.passage(f"hazards-{year}").text.en
    for rule, (_, label_en) in knowledge.RULE_LABEL.items():
        found = _num(re.escape(label_en) + r" ([\d\.,]+) %", text, "en")
        assert found == round(hz["year_level"][rule][i] * 100, 1)


def test_money_passages_equal_the_rulebook():
    plans = {p["id"]: p for p in canonical.load("rotations.generated.json")["plans"]}
    for pid in ("usual", "cc1", "cc2", "cc3", "cc4"):
        text = evidence.passage(f"plan-{pid}-money").text.en
        profits = [knowledge.parse_number(x, "en") for x in re.findall(r"net profit ([\d,]+) thousand", text)]
        assert profits == [r["profit_value"] for r in plans[pid]["reported_economics"]["per_crop"]]
        total = evidence.passage(f"plan-{pid}-year-total").text.en
        assert _num(r": ([\d,]+) thousand VND/ha", total, "en") == sum(profits)


def test_every_passage_has_a_location_unless_it_is_our_own_work():
    for p in evidence.load_passages():
        if p.validation_status == "VERIFIED":
            assert p.location, p.passage_id
