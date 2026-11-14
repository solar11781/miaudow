"""Tests for the shared abuse caps of the two model routes, POST /api/copilot and POST /api/explain (written before
the code). Spec: D-173 (the team's 30 USD key limit; a routine abuse limit of 20 model calls per client per hour and
1,500 per day, in memory, answering 429 with a fixed detail), the two security passes of PR #55 (the client is
Railway's X-Real-IP, never a client-sent X-Forwarded-For entry; each route has its own daily pool; model calls are
counted, not requests, and fixed answers without a model call do not count).
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
EXPLAIN = {"answers": ANSWERS, "plan": "cc1", "field": "why", "lang": "vi"}
COPILOT = {"question": "Lúa cần bao nhiêu nước tưới?", "mode": "simple", "lang": "vi"}
FORECAST = {**COPILOT, "question": "Năm sau có hạn không?"}  # a fixed answer: no model call
NO_NUMBER = (lambda _: final(),)  # one model call per copilot answer


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
    assert all(c.take("a", "copilot") for _ in range(PER_CLIENT_PER_HOUR))
    assert not c.take("a", "copilot")
    assert not c.take("a", "explain")  # the hour is the client's, across both routes: they share the key
    assert c.take("b", "copilot")  # another client is not held
    clock.now += 3600
    assert c.take("a", "explain")


def test_each_route_has_its_own_daily_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(caps, "PER_DAY", 3)
    clock = Clock()
    c = ModelCallCaps(clock)
    assert [c.take(name, "copilot") for name in "abcd"] == [True, True, True, False]
    assert c.take("e", "explain")  # the copilot cannot drain the explain pool
    clock.now += 86400
    assert c.take("d", "copilot")


def test_a_refused_call_is_not_counted() -> None:
    clock = Clock()
    c = ModelCallCaps(clock)
    for _ in range(PER_CLIENT_PER_HOUR + 5):
        c.take("a", "copilot")
    clock.now += 3600
    assert all(c.take("a", "copilot") for _ in range(PER_CLIENT_PER_HOUR))


@pytest.mark.parametrize(
    ("headers", "client"),
    [
        # docs.railway.com/networking/public-networking/specs-and-limits: "X-Real-IP for identifying client's remote IP"
        ({"x-real-ip": "203.0.113.1"}, "203.0.113.1"),
        ({"x-real-ip": " 203.0.113.1 ", "x-forwarded-for": "1.1.1.1"}, "203.0.113.1"),
        ({"x-forwarded-for": "1.1.1.1, 203.0.113.1"}, "testclient"),  # a client-sent entry is never the client
        ({}, "testclient"),
    ],
)
def test_the_client_is_railways_real_ip_or_the_socket_peer(headers: dict, client: str) -> None:
    scope = {
        "type": "http",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "client": ("testclient", 50000),
    }
    assert caps.client_of(Request(scope)) == client


def calls(c: TestClient, n: int, path: str, body: dict, ip: str = "203.0.113.7", forwarded: str = "") -> list[int]:
    headers = {"x-real-ip": ip, **({"x-forwarded-for": forwarded} if forwarded else {})}
    return [c.post(path, json=body, headers=headers).status_code for _ in range(n)]


def with_both(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The app with the copilot (and its key) and the explain endpoint both on."""
    app_client(monkeypatch)
    monkeypatch.setenv("FIELDSHIFT_EXPLAIN", "1")
    return TestClient(create_app(root=REPO), raise_server_exceptions=False)


def test_explain_and_copilot_share_the_client_cap_and_the_farmer_routes_keep_working(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    fake_api(*NO_NUMBER)
    c = with_both(monkeypatch)
    half = PER_CLIENT_PER_HOUR // 2
    codes = calls(c, half, "/api/copilot", COPILOT) + calls(c, PER_CLIENT_PER_HOUR - half, "/api/explain", EXPLAIN)
    assert 429 not in codes
    over = c.post("/api/explain", json=EXPLAIN, headers={"x-real-ip": "203.0.113.7"})
    assert over.status_code == 429
    assert over.json() == {"detail": "Too Many Requests"}
    assert calls(c, 1, "/api/copilot", COPILOT) == [429]
    assert calls(c, 1, "/api/copilot", COPILOT, forwarded="203.0.113.99") == [429]  # a forwarded entry changes nothing
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.8") != [429]  # another client
    assert c.post("/api/compare", json=ANSWERS).status_code == 200
    assert c.get("/api/past-years", params={"province": "nghe_an"}).status_code == 200
    assert c.get("/api/health").status_code == 200


def test_each_question_takes_one_model_call(monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]) -> None:
    api = fake_api(*NO_NUMBER)
    c = with_both(monkeypatch)
    assert calls(c, PER_CLIENT_PER_HOUR, "/api/copilot", COPILOT) == [200] * PER_CLIENT_PER_HOUR
    assert len(api.requests) == PER_CLIENT_PER_HOUR  # one call per question: the server retrieves, the model picks
    assert calls(c, 1, "/api/copilot", COPILOT) == [429]
    assert len(api.requests) == PER_CLIENT_PER_HOUR
    assert c.post("/api/compare", json=ANSWERS).status_code == 200


def test_fixed_answers_do_not_count(monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]) -> None:
    api = fake_api(*NO_NUMBER)
    c = with_both(monkeypatch)
    assert set(calls(c, PER_CLIENT_PER_HOUR + 5, "/api/copilot", FORECAST)) == {200}
    assert api.requests == []
    assert calls(c, 1, "/api/copilot", COPILOT) == [200]


def test_the_copilot_cannot_drain_the_explain_pool(
    monkeypatch: pytest.MonkeyPatch, fake_api: Callable[..., FakeApi]
) -> None:
    monkeypatch.setattr(caps, "PER_DAY", 2)
    fake_api(*NO_NUMBER)
    c = with_both(monkeypatch)
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.1") == [200]
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.2") == [200]
    assert calls(c, 1, "/api/copilot", COPILOT, "203.0.113.3") == [429]  # the copilot's day is full, for every client
    assert calls(c, 1, "/api/explain", EXPLAIN, "203.0.113.4") != [429]  # the explain pool is its own
    assert c.post("/api/compare", json=ANSWERS).status_code == 200
