"""Tests for POST /api/explain, the "explain simply" call to the Claude API (written before the code).

Spec: 02-SRS FR-15 (off by default; the app works without it; the key lives only in the server environment; the text is
marked as AI-generated, R-H15), 01-PRD later idea 5, D-146, D-159 (the anthropic package), QUEUE-DRAFT item 53 (the
endpoint refuses when the key is missing; it sends only the card's shown text, no personal data; the reply is marked
AI-generated; no call when the feature is off), NFR-01 (this call is the one stated exception), UI-UX-SPEC H14 (no
personal data), python.md (no personal data in logs; invalid input is HTTP 422). The real SDK runs against a mock
transport, so no test reaches the network and each test sees the exact request the SDK would send.
"""

import json
import logging
from collections.abc import Callable, Iterator
from pathlib import Path

import anthropic
import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient

from fieldshift.api import explain
from fieldshift.api.app import create_app
from fieldshift.api.explain import MAX_EXPLAIN_BODY_BYTES, MAX_TEXT_CHARS, MODEL

REPO = Path(__file__).resolve().parents[1]
KEY = "zz-test-key-not-real"
# card-like text with the number forms the app shows (P-02 Table 4 profit, thousand đ/ha; a year; a decimal)
TEXT_VI = "Lợi nhuận 16.200 nghìn đ/ha. Năm 2007 có 1,5 tháng khô hạn."
TEXT_EN = "Profit 16,200 thousand VND/ha. In 2007 there were 1.5 dry months."
SIMPLE_VI = "Năm 2007 có 1,5 tháng khô. Tiền lãi là 16.200 nghìn đồng mỗi ha."


def reply(text: str, stop_reason: str = "end_turn") -> httpx2.Response:
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
    return httpx2.Response(200, json=message)


class FakeApi:
    """Stands in for api.anthropic.com: records each request the SDK sends and answers with `answer`."""

    def __init__(self, answer: Callable[[httpx2.Request], httpx2.Response]) -> None:
        self.answer = answer
        self.requests: list[httpx2.Request] = []
        self.clients: list[dict] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.answer(request)


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeApi]:
    """Builds the real SDK client on a mock transport; counts every client the app creates."""

    def install(answer: Callable[[httpx2.Request], httpx2.Response] = lambda _: reply(SIMPLE_VI)) -> FakeApi:
        api = FakeApi(answer)
        real = anthropic.Anthropic

        def client(**kwargs: object) -> anthropic.Anthropic:
            api.clients.append(kwargs)
            # no retry wait in tests; the app's own retry count is checked in its own test
            options = {**kwargs, "max_retries": 0}
            return real(**options, http_client=httpx2.Client(transport=httpx2.MockTransport(api.handle)))

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
    r = c.post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
    assert r.status_code == 503
    assert r.json() == {"detail": "Service Unavailable"}
    assert api.clients == []
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
    r = app_client(monkeypatch).post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    assert r.json() == {"text": SIMPLE_VI, "ai_generated": True, "model": MODEL}  # FR-15 / R-H15: marked AI-generated


def test_the_client_uses_the_key_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    api = fake_api()
    app_client(monkeypatch).post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
    assert len(api.clients) == 1  # one client for the app, made at start
    assert api.clients[0]["api_key"] == KEY
    assert api.clients[0]["timeout"] == explain.TIMEOUT_SECONDS
    assert api.clients[0]["max_retries"] == explain.MAX_RETRIES


@pytest.mark.parametrize(("lang", "text", "language"), [("vi", TEXT_VI, "Vietnamese"), ("en", TEXT_EN, "English")])
def test_the_request_holds_only_the_shown_text_and_the_system_prompt(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], lang: str, text: str, language: str
) -> None:
    api = fake_api(lambda _: reply(text))
    headers = {"user-agent": "zz-farmer-phone", "x-forwarded-for": "203.0.113.9", "cookie": "zz-cookie=1"}
    r = app_client(monkeypatch).post("/api/explain", json={"lang": lang, "text": text}, headers=headers)
    assert r.status_code == 200
    body = sent_body(api)
    assert set(body) == {"model", "max_tokens", "system", "messages", "output_config"}
    assert body["messages"] == [{"role": "user", "content": text}]
    assert body["system"] == explain.system_prompt(lang)
    assert language in body["system"]
    assert body["model"] == MODEL
    assert body["max_tokens"] == explain.MAX_TOKENS
    sent = api.requests[0]
    assert sent.url == "https://api.anthropic.com/v1/messages"
    # H14: nothing of the farmer's request beyond the text leaves the server
    everything = sent.content.decode() + json.dumps(dict(sent.headers))
    for value in ("zz-farmer-phone", "203.0.113.9", "zz-cookie"):
        assert value not in everything


def test_the_system_prompt_forbids_new_facts_and_keeps_numbers() -> None:
    # FR-15 brief (item 53): reword in simple words for a farmer, same language, no new facts, numbers, advice or
    # recommendations, every number unchanged
    for lang in ("vi", "en"):
        prompt = explain.system_prompt(lang).lower()
        for phrase in ("simple words", "farmer", "same language", "new facts", "advice", "recommendation", "number"):
            assert phrase in prompt, (lang, phrase)


# ---- numbers in the reply must be the numbers of the text


@pytest.mark.parametrize(
    "answer",
    [
        "Năm 2007 có 1,5 tháng khô. Tiền lãi là 16.300 nghìn đồng mỗi ha.",  # a changed number
        "Năm 2007 có 1,5 tháng khô. Tiền lãi khá cao.",  # a dropped number
        "Năm 2007 có 1,5 tháng khô. Tiền lãi là 16.200 nghìn đồng mỗi ha, gấp 2 lần.",  # a new number
        "Năm 2007 có 1.5 tháng khô. Tiền lãi là 16.200 nghìn đồng mỗi ha.",  # a number written differently
    ],
)
def test_a_reply_that_changes_the_numbers_is_refused(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], answer: str
) -> None:
    fake_api(lambda _: reply(answer))
    r = app_client(monkeypatch).post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
    assert r.status_code == 502
    assert r.json() == {"detail": "Bad Gateway"}


def test_numbers_may_move_within_the_text() -> None:
    assert explain.numbers(TEXT_VI) == explain.numbers(SIMPLE_VI) == {"16.200", "2007", "1,5"}


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
        lambda _: reply(SIMPLE_VI, stop_reason="refusal"),
        lambda _: reply(SIMPLE_VI, stop_reason="max_tokens"),  # cut off: not the whole text
        lambda _: reply(""),
    ],
)
def test_an_api_failure_answers_a_generic_502(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], answer: Callable
) -> None:
    fake_api(answer)
    r = app_client(monkeypatch).post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
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
        ok = c.post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
    assert ok.status_code == 200
    assert KEY not in caplog.text
    assert TEXT_VI not in caplog.text
    assert SIMPLE_VI not in caplog.text
    assert KEY not in ok.text


def test_a_failure_logs_no_text_and_no_key(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi], caplog: pytest.LogCaptureFixture
) -> None:
    fake_api(lambda _: httpx2.Response(500, json={"type": "error", "error": {"type": "api_error", "message": "x"}}))
    c = app_client(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        assert c.post("/api/explain", json={"lang": "vi", "text": TEXT_VI}).status_code == 502
    assert KEY not in caplog.text
    assert TEXT_VI not in caplog.text


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
        ({"lang": "vi", "text": TEXT_VI, "extra": "zz-secret-extra"}, "zz-secret-extra"),  # only lang and text
        ({"lang": "vi", "text": TEXT_VI, "name": "zz-secret-name"}, "zz-secret-name"),  # H14: no personal data field
        ({"lang": "fr", "text": "zz-secret-text"}, "zz-secret-text"),  # Lang is vi or en (UI-UX-SPEC §11 Text)
        ({"lang": "vi", "text": ""}, None),
        ({"lang": "vi", "text": "   "}, None),
        ({"lang": "vi", "text": 5}, None),
        ({"lang": "vi"}, None),
        ({"text": "zz-secret-text"}, "zz-secret-text"),
        ({"lang": "vi", "text": "zz-secret " + "a" * MAX_TEXT_CHARS}, "zz-secret"),  # over the text limit
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
        yield json.dumps({"lang": "vi", "text": "a"}).encode()
        yield b" " * MAX_EXPLAIN_BODY_BYTES

    r = app_client(monkeypatch).post("/api/explain", content=chunks(), headers={"content-type": "application/json"})
    rejected(r, api)


def test_the_byte_limit_holds_the_longest_text_in_its_widest_json_form() -> None:
    # json.dumps writes each non-ASCII character of the BMP as \\uXXXX, 6 bytes; Vietnamese letters are all in the BMP
    largest = {"lang": "vi", "text": "ữ" * MAX_TEXT_CHARS}
    assert len(json.dumps(largest, indent=4).encode()) <= MAX_EXPLAIN_BODY_BYTES


def test_the_text_limit_holds_every_plan_of_the_app() -> None:
    # real data: all text and numbers of one plan, all 30 years, one language, joined by spaces (the most a card shows)
    c = TestClient(create_app(root=REPO))
    body = {"province": "nghe_an", "land": "unsure", "years": list(range(1995, 2025)), "priority": "stability"}
    plans = c.post("/api/compare", json=body).json()["plans"]
    skip = {"id", "code", "key", "crop_key", "source_ids", "values_source_ids", "threshold_source_id", "computed_by"}

    def strings(node: object, lang: str) -> Iterator[str]:
        if isinstance(node, dict) and set(node) == {"vi", "en"}:
            yield node[lang]
        elif isinstance(node, dict):
            for k, v in node.items():
                if k not in skip:
                    yield from strings(v, lang)
        elif isinstance(node, list):
            for v in node:
                yield from strings(v, lang)
        elif isinstance(node, str | int | float) and not isinstance(node, bool):
            yield str(node)

    longest = max(len(" ".join(strings(p, lang))) for p in plans for lang in ("vi", "en"))
    assert longest <= MAX_TEXT_CHARS


# ---- the API reads only the key; nothing else in the environment changes the call


def test_the_client_is_made_once_at_start(monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]) -> None:
    api = fake_api()
    c = app_client(monkeypatch)
    assert len(api.clients) == 1
    for _ in range(3):
        c.post("/api/explain", json={"lang": "vi", "text": TEXT_VI})
    assert len(api.clients) == 1
    assert len(api.requests) == 3
