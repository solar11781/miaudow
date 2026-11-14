"""Tests for the API service (written before the code, D-29), on the real rules files and artifacts.

Spec: UI-UX-SPEC §11 (GET /api/past-years?province=nghe_an, POST /api/compare with a JSON CompareRequest body,
GET /api/method, GET /api/health; all responses are JSON; the response checks of "Validation in src/api.ts");
04-TECH-DESIGN §3: invalid input (unknown province, land or priority; years not strictly ascending or outside
1995-2024) gets HTTP 422; UI-UX-SPEC §6b rule 3 (empty years); T34; NFR-01: backend tests pass with outbound network
calls blocked; 04-TECH-DESIGN §1 and D-76: the service serves the built frontend and returns index.html for every
frontend route of UI-UX-SPEC §6 (D-102); unknown /api paths are 404, never index.html; D-92 / 04 §10: uvicorn runs
with --no-access-log. Team note for queue item 20: rules and artifacts are loaded once at startup, an unexpected
error answers a generic 500 without internals, and the request body has a size limit.
"""

import ipaddress
import json
import shutil
import socket
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from fieldshift.api import app as api
from fieldshift.api.app import FRONTEND_ROUTES, MAX_BODY_BYTES, create_app
from fieldshift.engine.schemas import CompareResponse, HealthResponse, MethodResponse, PastYearsResponse

REPO = Path(__file__).resolve().parents[1]
BODY = {"province": "nghe_an", "land": "dry", "years": [1995, 2007, 2013, 2020], "priority": "income"}


def copy_root(tmp_path: Path) -> Path:
    """A copy of the real rules files and artifacts that one test may change."""
    for folder in ("rules", "artifacts"):
        shutil.copytree(REPO / folder, tmp_path / "root" / folder)
    return tmp_path / "root"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(root=REPO))


# ---- the three product endpoints


def test_past_years_answers_the_one_province(client: TestClient) -> None:
    r = client.get("/api/past-years", params={"province": "nghe_an"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    body = PastYearsResponse.model_validate(r.json())
    assert body.province == "nghe_an"
    assert [row.year for row in body.years] == list(range(1995, 2025))  # §11 YearRow: the past years 1995-2024


def test_compare_answers_a_valid_request(client: TestClient) -> None:
    r = client.post("/api/compare", json=BODY)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    body = r.json()
    CompareResponse.model_validate(body)
    assert body["request"] == BODY  # §11: request equals the body sent
    for plan in body["plans"]:  # §11: every per_year lists exactly the requested years
        for crop in plan["exposure"]:
            assert [y["year"] for y in crop["per_year"]] == BODY["years"]


def test_compare_accepts_every_year_and_the_longest_values(client: TestClient) -> None:
    body = {"province": "nghe_an", "land": "unsure", "years": list(range(1995, 2025)), "priority": "stability"}
    r = client.post("/api/compare", json=body)
    assert r.status_code == 200
    assert r.json()["request"] == body


def test_method_answers(client: TestClient) -> None:
    r = client.get("/api/method")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    MethodResponse.model_validate(r.json())


def test_health_lists_each_artifact_with_version_and_time(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    HealthResponse.model_validate(r.json())
    expected = {}
    for f in sorted((REPO / "artifacts").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        expected[f.name] = {"schema_version": data["schema_version"], "generated_at": data["generated_at"]}
    assert r.json() == {"status": "ok", "artifacts": expected}


# ---- invalid input: HTTP 422


def rejected(r: httpx.Response, secret: str | None = None) -> None:
    """A 422 whose items hold type, loc and msg only: no route echoes the input back (review of PR #41)."""
    assert r.status_code == 422
    items = r.json()["detail"]
    assert items
    assert all(set(item) == {"type", "loc", "msg"} for item in items), items
    if secret is not None:
        assert secret not in r.text


@pytest.mark.parametrize(
    ("query", "secret"),
    [
        ({"province": "zz-secret-province"}, "zz-secret-province"),  # 04 §3: unknown province
        ({}, None),  # §11: province is required
    ],
)
def test_past_years_rejects_a_bad_province(client: TestClient, query: dict, secret: str | None) -> None:
    rejected(client.get("/api/past-years", params=query), secret)


@pytest.mark.parametrize(
    ("change", "secret"),
    [
        ({"province": "zz-secret-province"}, "zz-secret-province"),  # 04 §3: unknown province
        ({"land": "irrigated"}, "irrigated"),  # §6b rule 4: irrigated never reaches the API; 04 §3: unknown land
        ({"priority": "zz-secret-priority"}, "zz-secret-priority"),  # 04 §3: unknown priority
        ({"years": [1994, 2000]}, "1994"),  # 04 §3: outside 1995-2024
        ({"years": [2000, 2025]}, "2025"),
        ({"years": [2007, 1996]}, "2007"),  # 04 §3: not strictly ascending
        ({"years": [2008, 2008]}, "2008"),  # duplicate (§6b: strictly ascending, so unique)
        ({"years": []}, None),  # §6b rule 3: years is required, so never empty
        ({"years": [2001.5]}, "2001.5"),  # whole years only
        ({"years": [2001.0]}, "2001"),
        ({"years": ["2003"]}, "2003"),
        ({"years": [True]}, "true"),
        ({"years": None}, None),
        ({"extra": "zz-secret-extra"}, "zz-secret-extra"),  # §11 CompareRequest has exactly four fields
    ],
)
def test_compare_rejects_an_invalid_body(client: TestClient, change: dict, secret: str | None) -> None:
    rejected(client.post("/api/compare", json={**BODY, **change}), secret)


@pytest.mark.parametrize("field", ["province", "land", "years", "priority"])
def test_compare_rejects_a_missing_field(client: TestClient, field: str) -> None:
    rejected(client.post("/api/compare", json={k: v for k, v in BODY.items() if k != field}))


@pytest.mark.parametrize("content", [b"", b"{zz-secret", b"[]", b"null", bytes([0xFF, 0xFE])])
def test_compare_rejects_a_body_that_is_not_a_request_object(client: TestClient, content: bytes) -> None:
    r = client.post("/api/compare", content=content, headers={"content-type": "application/json"})
    rejected(r, "zz-secret")


def test_body_limit_leaves_room_for_the_largest_valid_request() -> None:
    # all 30 years with the longest land and priority values, indented by 4 spaces: 521 bytes (computed 2026-11-14)
    largest = {"province": "nghe_an", "land": "unsure", "years": list(range(1995, 2025)), "priority": "stability"}
    assert len(json.dumps(largest, indent=4).encode()) < MAX_BODY_BYTES


def test_compare_accepts_a_body_of_exactly_the_limit(client: TestClient) -> None:
    content = json.dumps(BODY).encode()
    r = client.post(
        "/api/compare",
        content=content + b" " * (MAX_BODY_BYTES - len(content)),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200


def test_compare_rejects_a_body_over_the_limit(client: TestClient) -> None:
    # the brief for queue item 20: 422 unless the spec names 413; UI-UX-SPEC §11 and 04 §3 name only 422
    content = json.dumps(BODY).encode()
    r = client.post(
        "/api/compare",
        content=content + b" " * (MAX_BODY_BYTES + 1 - len(content)),
        headers={"content-type": "application/json"},
    )
    rejected(r)


def test_compare_rejects_a_streamed_body_over_the_limit(client: TestClient) -> None:
    # no content-length header: the limit counts the bytes as they arrive
    def chunks() -> Iterator[bytes]:
        yield json.dumps(BODY).encode()
        yield b" " * MAX_BODY_BYTES

    rejected(client.post("/api/compare", content=chunks(), headers={"content-type": "application/json"}))


# ---- other errors


def test_unknown_api_routes_are_json_404(client: TestClient) -> None:
    for path in ("/api/nothing", "/api/past-years/nghe_an", "/api"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.json() == {"detail": "Not Found"}, path


def test_an_unexpected_error_answers_a_generic_500(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_: object) -> None:
        raise RuntimeError("C:/secret/path/hazard_labels.json row 7")

    app = create_app(root=REPO)
    monkeypatch.setattr(api, "compare", broken)
    r = TestClient(app, raise_server_exceptions=False).post("/api/compare", json=BODY)
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error"}
    assert "secret" not in r.text


# ---- loading once at startup


def test_endpoints_read_no_file_after_startup(tmp_path: Path) -> None:
    root = copy_root(tmp_path)
    c = TestClient(create_app(root=root))
    shutil.rmtree(root)
    assert c.get("/api/past-years", params={"province": "nghe_an"}).status_code == 200
    assert c.post("/api/compare", json=BODY).status_code == 200
    assert c.get("/api/method").status_code == 200
    assert c.get("/api/health").status_code == 200


def test_an_artifact_without_schema_version_stops_the_start_naming_the_file(tmp_path: Path) -> None:
    # python.md: errors name the input; a broken artifact fails at start, never at a farmer's request
    root = copy_root(tmp_path)
    (root / "artifacts" / "broken.json").write_text('{"generated_at": "2000-01-01T00:00:00+07:00"}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"^broken\.json: no schema_version$"):
        create_app(root=root)


def test_a_missing_artifact_stops_the_start_naming_the_file(tmp_path: Path) -> None:
    root = copy_root(tmp_path)
    (root / "artifacts" / "hazard_labels.json").unlink()
    with pytest.raises(FileNotFoundError, match=r"hazard_labels\.json"):
        create_app(root=root)


# ---- no outbound network (NFR-01)


def test_no_outbound_network_call_while_starting_or_serving(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    real_connect = socket.socket.connect

    def local_only(sock: socket.socket, address: object) -> None:
        # the event loop of the test client talks to itself over loopback (socketpair on Windows); nothing else
        host = address[0] if isinstance(address, tuple) else None
        if host is None or not ipaddress.ip_address(host).is_loopback:
            raise AssertionError(f"outbound network call to {address}")
        real_connect(sock, address)

    def no_lookup(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"name lookup {args}")

    monkeypatch.setattr(socket.socket, "connect", local_only)
    monkeypatch.setattr(socket.socket, "connect_ex", local_only)
    monkeypatch.setattr(socket, "getaddrinfo", no_lookup)
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    c = TestClient(create_app(root=REPO, frontend_dir=tmp_path))
    assert c.get("/api/past-years", params={"province": "nghe_an"}).status_code == 200
    assert c.post("/api/compare", json=BODY).status_code == 200
    assert c.get("/api/method").status_code == 200
    assert c.get("/api/health").status_code == 200
    assert c.get("/").status_code == 200


# ---- frontend, access log, cookies


def test_frontend_routes_return_index_html(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    c = TestClient(create_app(root=REPO, frontend_dir=tmp_path))
    assert set(FRONTEND_ROUTES) == {
        "/",
        "/ruong",
        "/nam",
        "/uu-tien",
        "/phuong-an",
        "/khong-co-phuong-an",
        "/phuong-phap",
        "/gioi-thieu",
        "/nguon",
    }  # UI-UX-SPEC §6 (built routes)
    for route in FRONTEND_ROUTES:
        r = c.get(route)
        assert r.status_code == 200
        assert "app" in r.text
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/api/nothing").status_code == 404


def test_start_command_turns_off_the_access_log() -> None:
    assert "--no-access-log" in (REPO / "Dockerfile").read_text(encoding="utf-8")


def test_no_response_sets_a_cookie(tmp_path: Path) -> None:
    # UI-UX-SPEC T14 (server side): no cookies set
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    c = TestClient(create_app(root=REPO, frontend_dir=tmp_path))
    responses = [c.get(path) for path in ("/api/health", "/api/method", *FRONTEND_ROUTES)]
    responses += [c.get("/api/past-years", params={"province": "nghe_an"}), c.post("/api/compare", json=BODY)]
    for r in responses:
        assert r.status_code == 200, r.url
        assert "set-cookie" not in r.headers, r.url
