"""Tests for the shared abuse caps of the two model routes, POST /api/copilot and POST /api/explain (written before
the code). Spec: D-173 (the team's 30 USD key limit; a routine abuse limit of 20 model calls per client per hour and
1,500 per day for the whole app, in memory, answering 429 with a fixed detail), the security review of PR #55 (the client
is the last X-Forwarded-For entry, the one Railway's proxy appends; fixed answers without a model call do not count).
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import test_copilot
from fieldshift.api import caps
from fieldshift.api.app import create_app
from fieldshift.api.caps import PER_CLIENT_PER_HOUR, PER_DAY, ModelCallCaps
from test_copilot import ANSWERS, REPO, FakeApi, app_client, final

fake_api = test_copilot.fake_api  # the fixture, shared with the copilot tests
EXPLAIN = {"answers": ANSWERS, "plan": "cc1", "field": "why", "lang": "vi"}  # "why" holds no number (test_explain.py)
COPILOT = {"question": "Lúa cần bao nhiêu nước tưới?", "mode": "simple", "lang": "vi"}
FORECAST = {**COPILOT, "question": "Năm sau có hạn không?"}  # a fixed answer: no model call


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_the_caps_are_the_d173_numbers() -> None:
    assert (PER_CLIENT_PER_HOUR, PER_DAY) == (20, 1500)  # D-173


def test_a_client_gets_its_hourly_calls_then_waits_an_hour() -> None:
    clock = Clock()
    c = ModelCallCaps(clock)
    assert all(c.take("a") for _ in range(PER_CLIENT_PER_HOUR))
    assert not c.take("a")
    assert c.take("b")  # another client is not held
    clock.now += 3600
    assert c.take("a")


def test_the_whole_app_gets_its_daily_calls_then_waits_a_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(caps, "PER_DAY", 3)
    clock = Clock()
    c = ModelCallCaps(clock)
    assert [c.take(name) for name in "abcd"] == [True, True, True, False]
    clock.now += 86400
    assert c.take("d")


def test_a_refused_call_is_not_counted() -> None:
    clock = Clock()
    c = ModelCallCaps(clock)
    for _ in range(PER_CLIENT_PER_HOUR + 5):
        c.take("a")
    clock.now += 3600
    assert all(c.take("a") for _ in range(PER_CLIENT_PER_HOUR))


@pytest.mark.parametrize(
    ("headers", "client"),
    [
        ({"x-forwarded-for": "203.0.113.1"}, "203.0.113.1"),
        ({"x-forwarded-for": "1.1.1.1, 203.0.113.1"}, "203.0.113.1"),  # a forged left entry changes nothing
        ({"x-forwarded-for": " 1.1.1.1 ,203.0.113.1 "}, "203.0.113.1"),
        ({}, "testclient"),
    ],
)
def test_the_client_is_the_last_forwarded_entry(headers: dict, client: str) -> None:
    scope = {
        "type": "http",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "client": ("testclient", 50000),
    }
    assert caps.client_of(Request(scope)) == client


def calls(c: TestClient, n: int, path: str, body: dict, forwarded: str = "203.0.113.7") -> list[int]:
    return [c.post(path, json=body, headers={"x-forwarded-for": forwarded}).status_code for _ in range(n)]


def with_both(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The app with the copilot (and its key) and the explain endpoint both on."""
    app_client(monkeypatch)
    monkeypatch.setenv("FIELDSHIFT_EXPLAIN", "1")
    return TestClient(create_app(root=REPO), raise_server_exceptions=False)


def test_explain_and_copilot_share_the_client_cap_and_the_farmer_routes_keep_working(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    fake_api(lambda _: final("Không có số."))
    c = with_both(monkeypatch)
    half = PER_CLIENT_PER_HOUR // 2
    codes = calls(c, half, "/api/copilot", COPILOT) + calls(c, PER_CLIENT_PER_HOUR - half, "/api/explain", EXPLAIN)
    assert 429 not in codes
    over = c.post("/api/explain", json=EXPLAIN, headers={"x-forwarded-for": "203.0.113.7"})
    assert over.status_code == 429
    assert over.json() == {"detail": "Too Many Requests"}
    assert calls(c, 1, "/api/copilot", COPILOT) == [429]
    assert calls(c, 1, "/api/copilot", COPILOT, "1.1.1.1, 203.0.113.7") == [429]  # forging the left entry fails
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.8") != [429]  # another client
    assert c.post("/api/compare", json=ANSWERS).status_code == 200
    assert c.get("/api/past-years", params={"province": "nghe_an"}).status_code == 200
    assert c.get("/api/health").status_code == 200


def test_fixed_answers_do_not_count(monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]) -> None:
    api = fake_api(lambda _: final("Không có số."))
    c = with_both(monkeypatch)
    assert set(calls(c, PER_CLIENT_PER_HOUR + 5, "/api/copilot", FORECAST)) == {200}
    assert api.requests == []
    assert calls(c, 1, "/api/copilot", COPILOT) == [200]


def test_the_daily_cap_answers_429_for_every_client(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    monkeypatch.setattr(caps, "PER_DAY", 2)
    fake_api(lambda _: final("Không có số."))
    c = with_both(monkeypatch)
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.1") == [200]
    assert calls(c, 1, "/api/explain", EXPLAIN, "203.0.113.2") != [429]
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.3") == [429]
    assert c.post("/api/compare", json=ANSWERS).status_code == 200
