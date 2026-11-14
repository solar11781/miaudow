"""AI core 04: intents, the deterministic engine, the number check and the Claude tool loop (with a scripted fake
client, so no key and no network are needed)."""

import json
from types import SimpleNamespace

import pytest

from miaudow_api import copilot
from miaudow_api.contracts import CopilotRequest

FARMER_Q = "Ruộng nhà tôi cuối kênh, mùa hè thường thiếu nước, nên xem những cách trồng nào?"
STUDY_ORDER = ["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]
RANKING_WORDS = ("tốt nhất", "nên chọn", "xếp hạng cao", "best plan", "we recommend", "the best")


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Ngày mai có mưa không?", "forecast"),
        ("ngay mai co mua khong", "forecast"),
        ("What is the forecast for next season?", "forecast"),
        (FARMER_Q, "plans"),
        ("Nên trồng gì cho ruộng nhà tôi?", "plans"),
        ("Năm 2010 có hạn không?", "year"),
        ("NASA POWER là gì?", "evidence"),
    ],
)
def test_intent(question, expected):
    assert copilot.intent(question) == expected


def test_water_is_read_from_the_question():
    assert copilot.infer_water(FARMER_Q) == "canal_end"
    assert copilot.infer_water("ruong hay thieu nuoc") == "water_short"
    assert copilot.infer_water("Lúa cần bao nhiêu nước?") is None


def test_farmer_question_lists_every_plan_in_study_order_without_ranking():
    res = copilot.answer(CopilotRequest(question=FARMER_Q))
    assert res.engine == "deterministic"
    assert res.status == "grounded"
    assert [c.ref_id for c in res.cards] == STUDY_ORDER
    assert res.missing_information, "it must say what the tool cannot know"
    low = res.answer.lower()
    assert not any(w in low for w in RANKING_WORDS)
    assert "không chọn" in low


def test_forecast_is_refused():
    res = copilot.answer(CopilotRequest(question="Vụ tới có hạn không?"))
    assert res.status == "insufficient_evidence"
    assert "không có dự báo" in res.answer


def test_unrelated_question_abstains():
    res = copilot.answer(CopilotRequest(question="Giá vé máy bay đi Đà Nẵng bao nhiêu?"))
    assert res.status == "insufficient_evidence"
    assert res.answer.startswith("Chưa đủ dữ liệu để kết luận")


@pytest.mark.parametrize("lang", ["vi", "en"])
def test_year_answer_numbers_all_come_from_the_tool(lang):
    res = copilot.answer(CopilotRequest(question="Năm 2010 có hạn không?", lang=lang))
    assert res.status == "grounded"
    assert res.cards[0].kind == "year"
    known = copilot.numbers_in(copilot.tool_climate_year(2010, lang))
    check = copilot.check_numbers(res.answer, known, "Năm 2010 có hạn không?")
    assert check.checked > 3
    assert check.unverified == []


def test_year_outside_the_data_abstains():
    res = copilot.answer(CopilotRequest(question="Năm 1985 có hạn không?"))
    assert res.status == "insufficient_evidence"


@pytest.mark.parametrize(
    ("token", "readings"),
    [
        ("6.500", {6.5, 6500.0}),
        ("6,500", {6.5, 6500.0}),
        ("25,98", {25.98}),
        ("2.066,7", {2066.7}),
        ("1,234.5", {1234.5}),
    ],
)
def test_parse_number_reads_both_styles(token, readings):
    assert readings <= copilot.parse_number(token) | readings and copilot.parse_number(token) & readings


def test_number_check_allows_unit_changes_and_rounding_only():
    known = {25980.0, 0.8644, 2066.7}
    ok = copilot.check_numbers("Lạc lãi 25,98 triệu đ/ha; 86% đất trồng; mưa 2.067 mm.", known, "")
    assert ok.unverified == []
    bad = copilot.check_numbers("Lạc lãi 31,5 triệu đ/ha.", known, "")
    assert bad.unverified == ["31,5"]


# ---- Claude tool loop with a scripted client ----


def block(**kw):
    return SimpleNamespace(**kw)


def reply(stop, content):
    return SimpleNamespace(stop_reason=stop, content=content, _request_id="req_test")


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        create = self._create
        self.messages = SimpleNamespace(create=create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=create))

    def _create(self, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


def scripted(final_answer: str, plan_ids=("cc1",)):
    return [
        reply(
            "tool_use",
            [block(type="tool_use", id="t1", name="compare_plans", input={"water": "canal_end", "years": []})],
        ),
        reply(
            "end_turn",
            [
                block(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "grounded",
                            "answer": final_answer,
                            "passage_ids": [],
                            "plan_ids": list(plan_ids),
                            "years": [],
                            "missing_information": ["Giá bán năm nay ở xã bạn"],
                        },
                        ensure_ascii=False,
                    ),
                )
            ],
        ),
    ]


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5-5")


def test_claude_answer_with_tool_numbers_is_kept(with_key):
    fake = FakeClient(scripted("Trong thử nghiệm, lạc lãi 25,98 triệu đ/ha. Đây không phải lãi dự kiến."))
    res = copilot.answer(CopilotRequest(question=FARMER_Q), client_factory=lambda key: fake)
    assert res.engine == "claude"
    assert res.model == "claude-opus-5-5"
    assert res.status == "grounded"
    assert [c.ref_id for c in res.cards] == ["cc1"]
    assert res.tool_trace[0].tool == "compare_plans"
    assert res.numbers.unverified == []
    first = fake.calls[0]
    assert first["fallbacks"] == "default" and first["betas"] == ["server-side-fallback-2026-07-01"]
    assert first["output_config"]["format"]["type"] == "json_schema"
    assert all(t.get("strict") for t in first["tools"])


def test_claude_answer_with_an_invented_number_is_discarded(with_key):
    fake = FakeClient(scripted("Lạc lãi khoảng 40 triệu đ/ha mỗi năm."))
    res = copilot.answer(CopilotRequest(question=FARMER_Q), client_factory=lambda key: fake)
    assert res.engine == "deterministic"
    assert res.numbers.unverified == ["40"]
    assert [c.ref_id for c in res.cards] == STUDY_ORDER


def test_unknown_plan_ids_from_the_model_are_dropped(with_key):
    fake = FakeClient(scripted("Xem thẻ bên dưới.", plan_ids=("cc1", "cc9")))
    res = copilot.answer(CopilotRequest(question=FARMER_Q), client_factory=lambda key: fake)
    assert [c.ref_id for c in res.cards] == ["cc1"]


def test_refusal_falls_back_and_says_so(with_key):
    fake = FakeClient([reply("refusal", [])])
    res = copilot.answer(CopilotRequest(question=FARMER_Q), client_factory=lambda key: fake)
    assert res.status == "provider_error"
    assert res.engine == "deterministic"
    assert "Claude" in res.answer


def test_tool_input_errors_go_back_to_the_model_as_errors(with_key):
    script = [
        reply("tool_use", [block(type="tool_use", id="t1", name="climate_year", input={"year": 1980})]),
        reply(
            "end_turn",
            [
                block(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "insufficient_evidence",
                            "answer": "Chưa đủ dữ liệu để kết luận.",
                            "passage_ids": [],
                            "plan_ids": [],
                            "years": [],
                            "missing_information": [],
                        },
                        ensure_ascii=False,
                    ),
                )
            ],
        ),
    ]
    fake = FakeClient(script)
    res = copilot.answer(CopilotRequest(question="Năm 1980 thế nào?"), client_factory=lambda key: fake)
    assert res.tool_trace[0].ok is False
    second = fake.calls[1]["messages"][-1]["content"][0]
    assert second["is_error"] is True
    assert res.status == "insufficient_evidence"
