"""Tests for POST /api/explain, the "explain simply" call to the Claude API (written before the code).

Spec: 02-SRS FR-15 (off by default; the app works without it; the key lives only in the server environment; the text is
marked as AI-generated, R-H15), 01-PRD later idea 5, D-146, D-159 (the anthropic package), QUEUE-DRAFT item 53 (the
endpoint refuses when the key is missing; it sends only the card's shown text, no personal data; the reply is marked
AI-generated; no call when the feature is off), D-165 (the server builds the text from its own compare answer: the
browser sends only the compare answers, a plan code and a field), NFR-01 (this call is the one stated exception),
UI-UX-SPEC H14 (no personal data), python.md (no personal data in logs; invalid input is HTTP 422). The real SDK runs
against a mock transport, so no test reaches the network and each test sees the exact request the SDK would send.
"""

import asyncio
import functools
import html
import json
import logging
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import anthropic
import anyio.to_thread
import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient

from fieldshift.api import explain
from fieldshift.api.app import MAX_BODY_BYTES, create_app
from fieldshift.api.explain import MODEL, PLACEHOLDER, PROMPT, ExplainError
from fieldshift.engine.rules import load_prompt

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = load_prompt(REPO, PROMPT, (PLACEHOLDER,))  # rules/prompts/explain.md, as the app reads it
KEY = "zz-test-key-not-real"
# card-like text with the number forms the app shows (P-02 Table 4 profit, thousand đ/ha; a year; a decimal)
TEXT_VI = "Lợi nhuận 16.200 nghìn đ/ha. Năm 2007 có 1,5 tháng khô hạn."
SIMPLE_VI = "Tiền lãi là 16.200 nghìn đồng mỗi ha. Năm 2007 có 1,5 tháng khô."  # same numbers, order and units
ANSWERS = {"province": "nghe_an", "land": "dry", "years": [1995, 2007], "priority": "income"}  # a valid CompareRequest
# D-165: what identifies a shown text; "evidence" holds numbers (a year, a page, a plot size), so the number check runs
BODY = {"answers": ANSWERS, "plan": "cc1", "field": "evidence", "lang": "vi"}
WHY_PARTS = ("why", "evidence", "benefits", "gaps")  # UI-UX-SPEC §9 row `why`: the four labelled long text parts


@functools.cache
def compared() -> list[dict]:
    return TestClient(create_app(root=REPO)).post("/api/compare", json=ANSWERS).json()["plans"]


def shown(plan: str = "cc1", field: str = "evidence", lang: str = "vi") -> str:
    """The field's text as POST /api/compare shows it for ANSWERS (D-165: the server's own answer)."""
    return next(p for p in compared() if p["id"] == plan)["why"][field][lang]


def reply(text: str, stop_reason: str = "end_turn", headers: dict | None = None) -> httpx2.Response:
    """A Messages API reply as the API sends it."""
    message = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }
    return httpx2.Response(200, json=message, headers=headers)


def tagged(request: httpx2.Request) -> str:
    """The text the app sent inside its <text> tags, unescaped."""
    content = json.loads(request.content)["messages"][0]["content"]
    return html.unescape(content.removeprefix("<text>").removesuffix("</text>"))


def echo(request: httpx2.Request) -> httpx2.Response:
    """A reply with the sent text unchanged, so its numbers always pass the check."""
    return reply(tagged(request))


class FakeApi:
    """Stands in for api.anthropic.com: records each request the SDK sends and answers with `answer`."""

    def __init__(self, answer: Callable[[httpx2.Request], httpx2.Response]) -> None:
        self.answer = answer
        self.requests: list[httpx2.Request] = []
        self.clients: list[dict] = []
        self.client: anthropic.Anthropic | None = None

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.answer(request)


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeApi]:
    """Builds the real SDK client on a mock transport; counts every client the app creates."""

    def install(answer: Callable[[httpx2.Request], httpx2.Response] = echo) -> FakeApi:
        api = FakeApi(answer)
        real = anthropic.Anthropic

        def client(**kwargs: object) -> anthropic.Anthropic:
            api.clients.append(kwargs)
            return real(**kwargs, http_client=httpx2.Client(transport=httpx2.MockTransport(api.handle)))

        monkeypatch.setattr(explain.anthropic, "Anthropic", client)
        return api

    return install


def app_client(monkeypatch: pytest.MonkeyPatch, flag: str | None = "1", key: str | None = KEY) -> TestClient:
    for name, value in (("FIELDSHIFT_EXPLAIN", flag), ("ANTHROPIC_API_KEY", key)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    return TestClient(create_app(root=REPO), raise_server_exceptions=False)


def direct_client(fake_api: Callable[..., FakeApi], answer: Callable[[httpx2.Request], httpx2.Response]) -> FakeApi:
    """The fake API and the app's client on it, for tests of explain() with a text no plan holds."""
    api = fake_api(answer)
    api.client = explain.claude_client({"FIELDSHIFT_EXPLAIN": "1", "ANTHROPIC_API_KEY": KEY})
    return api


def sent_body(api: FakeApi) -> dict:
    assert len(api.requests) == 1
    return json.loads(api.requests[0].content)


# ---- off by default: no key or no flag means "not available" and no client


@pytest.mark.parametrize(
    ("flag", "key"),
    [
        (None, None),  # FR-15: off by default
        ("1", None),  # item 53: refuses when the key is missing
        ("1", ""),
        (None, KEY),  # item 53: no call when the feature is off, even with a key
        ("0", KEY),
    ],
)
def test_explain_is_not_available_without_flag_and_key(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], flag: str | None, key: str | None
) -> None:
    api = fake_api()
    c = app_client(monkeypatch, flag, key)
    r = c.post("/api/explain", json=BODY)
    assert r.status_code == 503
    assert r.json() == {"detail": "Service Unavailable"}
    assert api.clients == []
    assert api.requests == []


def test_health_tells_the_page_whether_explain_is_on_without_a_call(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    # the cards read this flag once to decide on the button, so no probe request is needed
    api = fake_api()
    assert app_client(monkeypatch, None, None).get("/api/health").json()["explain"] is False
    assert app_client(monkeypatch, "1", None).get("/api/health").json()["explain"] is False
    assert app_client(monkeypatch).get("/api/health").json()["explain"] is True
    assert api.requests == []


def test_the_app_works_without_the_feature(monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]) -> None:
    # FR-15: app fully usable without it
    fake_api()
    c = app_client(monkeypatch, None, None)
    assert c.get("/api/method").status_code == 200
    assert c.get("/api/health").status_code == 200


# ---- on: one call with only the shown text and the system prompt


def test_explain_answers_with_the_reworded_text_marked_ai_generated(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    fake_api()
    r = app_client(monkeypatch).post("/api/explain", json=BODY)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    assert r.json() == {"text": shown(), "ai_generated": True, "model": MODEL}  # FR-15 / R-H15: marked AI-generated


def test_the_client_uses_the_key_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    api = fake_api()
    app_client(monkeypatch).post("/api/explain", json=BODY)
    assert len(api.clients) == 1  # one client for the app, made at start
    assert api.clients[0]["api_key"] == KEY
    assert api.clients[0]["timeout"] == explain.TIMEOUT_SECONDS
    assert api.clients[0]["max_retries"] == 0  # review of PR #43: the SDK obeys retry-after without a cap
    assert api.clients[0]["base_url"] == "https://api.anthropic.com"  # review of PR #43: never from the environment


def test_a_base_url_in_the_environment_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    api = fake_api()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://zz-other-host.example")
    assert app_client(monkeypatch).post("/api/explain", json=BODY).status_code == 200
    assert api.requests[0].url == "https://api.anthropic.com/v1/messages"


@pytest.mark.parametrize("field", WHY_PARTS)
@pytest.mark.parametrize(("plan", "lang", "language"), [("cc1", "vi", "Vietnamese"), ("usual_p03", "en", "English")])
def test_the_request_holds_only_the_shown_field_and_the_system_prompt(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], plan: str, field: str, lang: str, language: str
) -> None:
    # D-165: the server takes the field's text in the asked language from its own compare answer for the answers sent
    api = fake_api()
    headers = {"user-agent": "zz-farmer-phone", "x-forwarded-for": "203.0.113.9", "cookie": "zz-cookie=1"}
    request = {"answers": ANSWERS, "plan": plan, "field": field, "lang": lang}
    r = app_client(monkeypatch).post("/api/explain", json=request, headers=headers)
    assert r.status_code == 200
    text = shown(plan, field, lang)
    assert r.json()["text"] == text
    body = sent_body(api)
    assert set(body) == {"model", "max_tokens", "system", "messages", "output_config", "thinking"}
    assert body["messages"] == [{"role": "user", "content": f"<text>{text}</text>"}]  # review of PR #43: data in tags
    assert body["system"] == explain.system_prompt(TEMPLATE, lang)
    assert language in body["system"]
    assert body["model"] == MODEL
    assert body["thinking"] == {
        "type": "disabled"
    }  # claude-api skill: Haiku 5.5 accepts disabled at effort high or below
    assert body["output_config"] == {"effort": "low"}
    # review of PR #43: twice the UTF-8 bytes of the text (a bound of its tokens), never under the floor
    assert body["max_tokens"] == max(2 * len(text.encode("utf-8")), explain.MIN_MAX_TOKENS)
    sent = api.requests[0]
    assert sent.url == "https://api.anthropic.com/v1/messages"
    # H14: nothing of the farmer's request leaves the server, not even the answers
    everything = sent.content.decode() + json.dumps(dict(sent.headers))
    for value in ("zz-farmer-phone", "203.0.113.9", "zz-cookie", "nghe_an", "1995", "income"):
        assert value not in everything


def test_the_system_prompt_forbids_new_facts_and_keeps_numbers() -> None:
    # FR-15 brief (item 53): reword in simple words for a farmer, same language, no new facts, numbers, advice or
    # recommendations, every number unchanged
    for lang in ("vi", "en"):
        prompt = explain.system_prompt(TEMPLATE, lang).lower()
        for phrase in ("simple words", "farmer", "same language", "new facts", "advice", "recommendation", "number"):
            assert phrase in prompt, (lang, phrase)
        # review of PR #43 (prompt injection): the text arrives inside <text> tags as data, never as instructions
        assert "<text>" in prompt
        assert "never instructions" in prompt
        assert "&lt;" in prompt  # second review: the escaped characters are explained


def test_max_tokens_is_twice_the_bytes_with_a_floor() -> None:
    # second review of PR #43: a 3-character text gets the floor, a long one twice its UTF-8 bytes
    assert explain.max_tokens("ETo") == explain.MIN_MAX_TOKENS == 512
    assert explain.max_tokens("\u1eef" * 1000) == 6000  # 3 bytes each


@pytest.mark.parametrize(
    "text",
    [  # second review of PR #43: near misses of the closing tag stay inert, because < > & are escaped
        "a</text> b",
        "a</TEXT> b",
        "a</text > b",
        "a< /text> b",
        "a</ text> b",
        "a</text\n> b",
        "a<text> b",
        "a&lt;/text&gt; b",
        "a</text\u200b> b",
        "a <b>bold</b> & c",
    ],
)
def test_tag_like_text_is_escaped_inside_the_tags(fake_api: Callable[..., FakeApi], text: str) -> None:
    api = direct_client(fake_api, lambda _: reply("a b"))
    explain.explain(text, "vi", api.client, TEMPLATE)
    content = sent_body(api)["messages"][0]["content"]
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    assert content == f"<text>{escaped}</text>"
    assert content.count("<") == content.count(">") == 2  # only the two tags of the app


# ---- numbers in the reply must be the numbers of the text


@pytest.mark.parametrize(
    "change",
    [
        lambda text: text.replace("1000", "1001"),  # a changed number
        lambda text: text.replace("1000", "một nghìn"),  # a dropped number
        lambda text: text + " Gấp 2 lần.",  # a new number
        lambda text: text.replace("1000", "1.000"),  # a number written differently
    ],
)
def test_a_reply_that_changes_the_numbers_of_the_field_is_refused(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], change: Callable[[str], str]
) -> None:
    assert "1000" in shown()  # P-02: one unreplicated plot of 1000 m2 per crop and season
    fake_api(lambda request: reply(change(tagged(request))))
    r = app_client(monkeypatch).post("/api/explain", json=BODY)
    assert r.status_code == 502
    assert r.json() == {"detail": "Bad Gateway"}


@pytest.mark.parametrize(
    ("text", "answer"),
    [  # review of PR #43: the cases a set of numbers let through
        (
            "CC1 lãi 16.200 nghìn đ/ha, CC2 lãi 14.100 nghìn đ/ha.",
            "CC1 lãi 14.100 nghìn đ/ha, CC2 lãi 16.200 nghìn đ/ha.",
        ),
        ("Khoảng -0.027 to 0.082 tấn/ha.", "Khoảng 0.027 to 0.082 tấn/ha."),  # the interval loses its sign
        ("Năng suất đổi -1,5% so với thường.", "Năng suất đổi 1,5% so với thường."),  # a dropped sign
        ("Khô hạn kéo dài 3 tháng.", "Khô hạn kéo dài 3 năm."),  # the unit word changes
        ("Khoảng 20% số năm.", "Khoảng 20 lần số năm."),  # % becomes a word
        ("Profit 16,200 thousand VND/ha.", "Profit 16,200 million VND/ha."),  # second review: a scale word changes
        ("Mưa 30 mm trong 2 ngày.", "Mưa 30 ngày trong 2 mm."),  # units swapped between numbers
    ],
)
def test_a_reply_with_numbers_in_another_order_sign_or_unit_is_refused(
    fake_api: Callable[..., FakeApi], text: str, answer: str
) -> None:
    api = direct_client(fake_api, lambda _: reply(answer))
    with pytest.raises(ExplainError, match="NumbersDiffer"):
        explain.explain(text, "vi", api.client, TEMPLATE)


def test_numbers_are_read_in_order_with_sign_and_unit() -> None:
    text = "Từ -0,027 đến 0,082 (\u22121,5%) trong 1995-2024, 3 tháng"
    assert explain.numbers(text) == [
        ("-", "0,027", ""),  # "đến" is not a unit word
        ("", "0,082", ""),
        ("-", "1,5", "%"),  # the Unicode minus reads as a minus
        ("", "1995", ""),  # the dash of a year range is not a sign
        ("", "2024", ""),
        ("", "3", "tháng"),
    ]
    assert explain.numbers(TEXT_VI) == explain.numbers(SIMPLE_VI)


@pytest.mark.parametrize(
    ("text", "answer"),
    [
        ("Trong 3 tháng hạn, 20% số năm khô.", "Có 3 tháng khô và 20% số năm bị hạn."),
        # second review of PR #43: faithful rewordings the first check refused
        ("In 2007 there were 1.5 dry months.", "In 2007, 1.5 months were dry."),
        ("Năm 2007 có 1,5 tháng khô.", "Năm 2007, có 1,5 tháng khô."),
        ("Khoảng 20% số năm.", "Khoảng 20 % số năm."),
        ("CC1: lãi 16.200 nghìn đ/ha.", "CC1 là phương án lãi 16.200 nghìn đồng mỗi ha."),
    ],
)
def test_a_reply_that_keeps_numbers_units_and_order_passes(
    fake_api: Callable[..., FakeApi], text: str, answer: str
) -> None:
    api = direct_client(fake_api, lambda _: reply(answer))
    assert explain.explain(text, "vi", api.client, TEMPLATE).text == answer


# ---- errors of the Claude API: a generic answer, no internals


def timeout(_: httpx2.Request) -> httpx2.Response:
    raise httpx2.ReadTimeout("zz-secret-timeout")


def refused_connection(_: httpx2.Request) -> httpx2.Response:
    raise httpx2.ConnectError("zz-secret-connect")


@pytest.mark.parametrize(
    "answer",
    [
        timeout,
        refused_connection,
        lambda _: httpx2.Response(500, json={"type": "error", "error": {"type": "api_error", "message": "zz-secret"}}),
        lambda _: httpx2.Response(401, json={"type": "error", "error": {"type": "auth", "message": "zz-secret"}}),
        lambda _: httpx2.Response(429, json={"type": "error", "error": {"type": "rate", "message": "zz-secret"}}),
        lambda _: httpx2.Response(200, content=b"zz-secret not json"),
        lambda _: httpx2.Response(200, json={"zz-secret": "not a message"}),
        lambda _: reply(SIMPLE_VI, stop_reason="refusal"),
        lambda _: reply(SIMPLE_VI, stop_reason="max_tokens"),  # cut off: not the whole text
        lambda _: reply(""),
    ],
)
def test_an_api_failure_answers_a_generic_502(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], answer: Callable
) -> None:
    fake_api(answer)
    r = app_client(monkeypatch).post("/api/explain", json=BODY)
    assert r.status_code == 502
    assert r.json() == {"detail": "Bad Gateway"}
    assert "zz-secret" not in r.text
    assert KEY not in r.text


# ---- the key and the text never reach a log or a response


def test_the_key_and_the_text_never_reach_a_log(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], caplog: pytest.LogCaptureFixture
) -> None:
    fake_api()
    c = app_client(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        ok = c.post("/api/explain", json=BODY)
    assert ok.status_code == 200
    assert KEY not in caplog.text
    assert shown() not in caplog.text
    assert KEY not in ok.text


def test_a_failure_logs_no_text_and_no_key(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], caplog: pytest.LogCaptureFixture
) -> None:
    fake_api(lambda _: httpx2.Response(500, json={"type": "error", "error": {"type": "api_error", "message": "x"}}))
    c = app_client(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        assert c.post("/api/explain", json=BODY).status_code == 502
    assert KEY not in caplog.text
    assert shown() not in caplog.text


def failure_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [rec.getMessage() for rec in caplog.records if "explain failed" in rec.getMessage()]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [  # review of PR #43: one line per 502 with the exception class, status code, stop reason and request id only
        (
            lambda _: httpx2.Response(
                500,
                json={"type": "error", "error": {"type": "api_error", "message": "x"}},
                headers={"request-id": "req_zz1"},
            ),
            ("InternalServerError", "status=500", "stop_reason=None", "request_id=req_zz1"),
        ),
        (timeout, ("APITimeoutError", "status=None", "stop_reason=None", "request_id=None")),
        (
            lambda _: reply(SIMPLE_VI, stop_reason="refusal", headers={"request-id": "req_zz2"}),
            ("NotWhole", "status=200", "stop_reason=refusal", "request_id=req_zz2"),
        ),
        (
            lambda _: reply("Tiền lãi cao.", headers={"request-id": "req_zz3"}),
            ("NumbersDiffer", "status=200", "stop_reason=end_turn", "request_id=req_zz3"),
        ),
    ],
)
def test_every_502_logs_one_line_without_text_key_or_ip(
    monkeypatch: pytest.MonkeyPatch,
    fake_api: Callable[..., FakeApi],
    caplog: pytest.LogCaptureFixture,
    answer: Callable,
    expected: tuple[str, ...],
) -> None:
    fake_api(answer)
    c = app_client(monkeypatch)
    headers = {"x-forwarded-for": "203.0.113.9", "user-agent": "zz-farmer-phone"}
    with caplog.at_level(logging.DEBUG):
        r = c.post("/api/explain", json=BODY, headers=headers)
    assert r.status_code == 502
    lines = failure_lines(caplog)
    assert len(lines) == 1
    for part in expected:
        assert part in lines[0], (part, lines[0])
    for secret in (KEY, shown(), SIMPLE_VI, "Tiền lãi", "203.0.113.9", "zz-farmer-phone", "testclient"):
        assert secret not in caplog.text


# ---- invalid input: HTTP 422 without echo and without a call


def rejected(r: httpx.Response, api: FakeApi, secret: str | None = None) -> None:
    assert r.status_code == 422
    items = r.json()["detail"]
    assert items
    assert all(set(item) == {"type", "loc", "msg"} for item in items), items
    if secret is not None:
        assert secret not in r.text
    assert api.requests == []


@pytest.mark.parametrize(
    ("body", "secret"),
    [
        ({"lang": "vi", "text": "zz-secret-text"}, "zz-secret-text"),  # D-165: the browser never sends the text
        ({**BODY, "text": "zz-secret-text"}, "zz-secret-text"),
        ({**BODY, "name": "zz-secret-name"}, "zz-secret-name"),  # H14: no personal data field
        ({**BODY, "lang": "zz-secret-lang"}, "zz-secret-lang"),  # Lang is vi or en (UI-UX-SPEC §11 Text)
        ({**BODY, "plan": "zz-secret-plan"}, "zz-secret-plan"),  # PlanId (UI-UX-SPEC §11)
        ({**BODY, "field": "zz-secret-field"}, "zz-secret-field"),  # D-165: a field from a closed list
        ({**BODY, "field": "risks"}, None),  # not a why part (UI-UX-SPEC §9: the risks are in the row `check`)
        ({**BODY, "field": "name"}, None),
        ({**BODY, "answers": {**ANSWERS, "years": []}}, None),  # the CompareRequest rules hold (UI-UX-SPEC §6b)
        ({**BODY, "answers": {**ANSWERS, "years": [1990]}}, None),
        ({**BODY, "answers": {**ANSWERS, "land": "irrigated"}}, None),  # §6b rule 4: never reaches the API
        ({**BODY, "answers": {**ANSWERS, "zz": "zz-secret-extra"}}, "zz-secret-extra"),
        ({**BODY, "answers": "zz-secret-answers"}, "zz-secret-answers"),
        ({**ANSWERS, "plan": "cc1", "field": "why", "lang": "vi"}, None),  # the answers nest under "answers"
        ({"plan": "cc1", "field": "why", "lang": "vi"}, None),
        ({"answers": ANSWERS, "field": "why", "lang": "vi"}, None),
        ({"answers": ANSWERS, "plan": "cc1", "lang": "vi"}, None),
        ({"answers": ANSWERS, "plan": "cc1", "field": "why"}, None),
    ],
)
def test_explain_rejects_an_invalid_body(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], body: dict, secret: str | None
) -> None:
    api = fake_api()
    rejected(app_client(monkeypatch).post("/api/explain", json=body), api, secret)


@pytest.mark.parametrize("content", [b"", b"{zz-secret", b"[]", b"null", bytes([0xFF, 0xFE])])
def test_explain_rejects_a_body_that_is_not_an_object(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], content: bytes
) -> None:
    api = fake_api()
    r = app_client(monkeypatch).post("/api/explain", content=content, headers={"content-type": "application/json"})
    rejected(r, api, "zz-secret")


def test_explain_rejects_a_body_over_the_byte_limit(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    api = fake_api()

    def chunks() -> Iterator[bytes]:  # no content-length: the limit counts the bytes as they arrive
        yield json.dumps(BODY).encode()
        yield b" " * MAX_BODY_BYTES

    r = app_client(monkeypatch).post("/api/explain", content=chunks(), headers={"content-type": "application/json"})
    rejected(r, api)


def test_the_byte_limit_holds_the_largest_request_in_its_widest_json_form() -> None:
    # the longest value of each closed list (UI-UX-SPEC §11 Land, Priority, PlanId; §9 why parts), all 30 years
    answers = {"province": "nghe_an", "land": "unsure", "years": list(range(1995, 2025)), "priority": "stability"}
    largest = {"answers": answers, "plan": "usual_p03", "field": "evidence", "lang": "vi"}
    assert len(json.dumps(largest, indent=4).encode()) <= MAX_BODY_BYTES


# ---- one client for the app, and its own small thread limit


def test_the_client_is_made_once_at_start(monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]) -> None:
    api = fake_api()
    c = app_client(monkeypatch)
    assert len(api.clients) == 1
    for _ in range(3):
        c.post("/api/explain", json=BODY)
    assert len(api.clients) == 1
    assert len(api.requests) == 3


def test_a_burst_runs_at_most_the_limit_and_the_rest_get_503_at_once(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    # review of PR #43: stalled Claude calls must never starve the threadpool compare runs in; second review: a burst of
    # 12 parallel calls runs at most EXPLAIN_LIMIT, the rest answer 503 without waiting for a slot
    release = threading.Event()

    def stall(request: httpx2.Request) -> httpx2.Response:
        release.wait(10)
        return echo(request)

    api = fake_api(stall)
    app = app_client(monkeypatch).app
    burst = 12

    async def run() -> tuple[list[int], int, int, list[int]]:
        # the default thread limit made as small as the explain limit: without its own limit, explain would fill it
        anyio.to_thread.current_default_thread_limiter().total_tokens = explain.EXPLAIN_LIMIT
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            calls = [asyncio.create_task(c.post("/api/explain", json=BODY)) for _ in range(burst)]
            try:
                async with asyncio.timeout(5):  # nothing is released yet: the 503s come without waiting
                    while sum(t.done() for t in calls) < burst - explain.EXPLAIN_LIMIT:
                        await asyncio.sleep(0.01)
                    early = [t.result().status_code for t in calls if t.done()]
                    running = len(api.requests)
                    compared = await c.post("/api/compare", json=ANSWERS)
            finally:
                release.set()
            done = sorted(r.status_code for r in await asyncio.gather(*calls))
        return early, running, compared.status_code, done

    early, running, compared, done = asyncio.run(run())
    assert early == [503] * (burst - explain.EXPLAIN_LIMIT)
    assert running <= explain.EXPLAIN_LIMIT
    assert compared == 200
    assert done == [200] * explain.EXPLAIN_LIMIT + [503] * (burst - explain.EXPLAIN_LIMIT)
