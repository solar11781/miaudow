"""Tests for the optional Google sign-in and saved answers (accounts.py and its routes in app.py), written first.

Spec: UI-UX-SPEC §12c (every farmer route works without signing in; store only Google's account id and the saved
answers; a delete-everything call; several saved sets per account), §6b (the answers: land, years, priority, with the
same rules as the compare request), H14 (no cookie). The routes are on only when GOOGLE_CLIENT_ID and DATABASE_URL are
both set; otherwise they answer 503. The database is a throwaway PostgreSQL 18: TEST_DATABASE_URL when set (the
service container in CI), otherwise a container this module starts with Docker; the module is skipped with the reason
when neither is available. Google's token check runs for real, on every account request, on tokens signed with a
test key; only the download of Google's public keys is replaced, so no test touches the network.
"""

import json
import logging
import os
import shutil
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt
from google.auth.exceptions import TransportError

from fieldshift.api import accounts
from fieldshift.api.app import MAX_BODY_BYTES, create_app

REPO = Path(__file__).resolve().parents[1]
CLIENT_ID = "test-client.apps.googleusercontent.com"
GOOGLE_CERTS = "https://www.googleapis.com/oauth2/v1/certs"  # google-auth 2.62.2, google/oauth2/id_token.py
GOOGLE_CACHE = "public, max-age=23762, must-revalidate, no-transform"  # Google's header on GOOGLE_CERTS, 2026-11-14
ANSWERS = {"land": "dry", "years": [1995, 2007, 2013], "priority": "income"}
ROUTES = [
    ("post", "/api/account/sign-in"),
    ("get", "/api/account/saved"),
    ("post", "/api/account/saved"),
    ("delete", "/api/account/saved/1"),
    ("delete", "/api/account"),
]


# ---- a throwaway PostgreSQL 18, the major version of the Railway database image (postgres-ssl:18)


def _ready(url: str, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(url, connect_timeout=2):
                return True
        except psycopg.OperationalError:
            time.sleep(0.5)
    return False


def _docker(docker: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([docker, *args], capture_output=True, text=True, check=False, timeout=300)  # noqa: S603  fixed arguments


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    if url := os.environ.get("TEST_DATABASE_URL"):
        yield url
        return
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker is not installed and TEST_DATABASE_URL is not set: no PostgreSQL for the sign-in tests")
    started = _docker(
        docker, "run", "-d", "--rm", "-e", "POSTGRES_PASSWORD=test", "-p", "127.0.0.1::5432", "postgres:18"
    )
    if started.returncode != 0:
        pytest.skip(f"Docker could not start postgres:18: {started.stderr.strip()[:300]}")
    container = started.stdout.strip()
    try:
        port = _docker(docker, "port", container, "5432/tcp").stdout.strip().rsplit(":", 1)[-1]
        url = f"postgresql://postgres:test@127.0.0.1:{port}/postgres"
        if not _ready(url, 60):
            pytest.fail("the postgres:18 container did not accept connections within 60 s")
        yield url
    finally:
        _docker(docker, "stop", container)  # started with --rm, so stopping also removes it


def rows(url: str, sql: str) -> list[tuple]:
    with psycopg.connect(url) as conn:
        return conn.execute(sql).fetchall()


@pytest.fixture
def on(database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """Sign-in switched on against an empty database."""
    with psycopg.connect(database_url) as conn:
        conn.execute("DROP TABLE IF EXISTS saved_answers, account")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("DATABASE_URL", database_url)
    return database_url


# ---- Google ID tokens signed with a test key


@pytest.fixture(scope="module")
def keys() -> dict[str, rsa.RSAPrivateKey]:
    return {kid: rsa.generate_private_key(public_exponent=65537, key_size=2048) for kid in ("google", "stranger")}


def _pem(key: rsa.RSAPrivateKey) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()


class Answer:
    """What urllib.request.urlopen gives back: a body and a Cache-Control header."""

    def __init__(self, body: bytes, cache: str | None = GOOGLE_CACHE) -> None:
        self.status, self.body = 200, body
        self.headers = {"content-type": "application/json"} | ({"cache-control": cache} if cache else {})

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]

    def __enter__(self) -> "Answer":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def public_keys(keys: dict[str, rsa.RSAPrivateKey]) -> bytes:
    pem = (
        keys["google"]
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    return json.dumps({"google": pem.decode()}).encode()


def fake_download(monkeypatch: pytest.MonkeyPatch, answer: Answer) -> list[SimpleNamespace]:
    """Replace the key download; returns every call with its URL, timeout and TLS context."""
    calls: list[SimpleNamespace] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float | None = None, context: object = None) -> Answer:
        calls.append(SimpleNamespace(url=request.full_url, timeout=timeout, context=context))
        return answer

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


@pytest.fixture
def fetched(keys: dict[str, rsa.RSAPrivateKey], monkeypatch: pytest.MonkeyPatch) -> list[SimpleNamespace]:
    """Google's key download answered locally with the public half of the "google" key."""
    return fake_download(monkeypatch, Answer(public_keys(keys)))


def urls(calls: list[SimpleNamespace]) -> list[str]:
    return [call.url for call in calls]


def google_token(keys: dict[str, rsa.RSAPrivateKey], kid: str = "google", **changes: object) -> str:
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": "110169484474386276334", "iat": now}
    claims |= {"exp": now + 3600, **changes}
    return jwt.encode(crypt.RSASigner.from_string(_pem(keys[kid]), key_id=kid), claims).decode()


def bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def sign_in(c: TestClient, keys: dict[str, rsa.RSAPrivateKey], **changes: object) -> dict[str, str]:
    """Sign in; the same Google token then goes with every account request."""
    me = bearer(google_token(keys, **changes))
    r = c.post("/api/account/sign-in", headers=me)
    assert r.status_code == 204, r.text
    return me


def no_echo(r: object, status: int) -> None:
    assert r.status_code == status, r.text
    assert "zz-secret" not in r.text
    assert "set-cookie" not in r.headers


# ---- off unless both settings are set


@pytest.mark.parametrize(
    "settings",
    [{}, {"GOOGLE_CLIENT_ID": CLIENT_ID}, {"DATABASE_URL": "postgresql://nobody@127.0.0.1:1/none"}],
)
def test_sign_in_is_off_without_both_settings(monkeypatch: pytest.MonkeyPatch, settings: dict[str, str]) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    c = TestClient(create_app(root=REPO))  # a database URL alone is never connected to (port 1 would fail the start)
    assert c.get("/api/account/config").json() == {"available": False, "client_id": None}
    for method, path in ROUTES:
        r = getattr(c, method)(path)
        assert r.status_code == 503, path
        assert r.json() == {"detail": "sign-in is not available"}, path


def test_an_unreachable_database_at_start_turns_sign_in_off(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # §12c: every farmer route MUST keep working without signing in, so a database that is down never stops the start
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    url = "postgresql://zz-secret-user:zz-secret-pass@127.0.0.1:1/zz-secret-db"  # nothing listens on port 1
    monkeypatch.setenv("DATABASE_URL", url)
    with caplog.at_level(logging.DEBUG):
        c = TestClient(create_app(root=REPO))
    assert c.get("/api/health").status_code == 200
    assert c.post("/api/compare", json={"province": "nghe_an", **ANSWERS}).status_code == 200
    assert c.get("/api/account/config").json() == {"available": False, "client_id": None}
    for method, path in ROUTES:
        assert getattr(c, method)(path).json() == {"detail": "sign-in is not available"}, path
    lines = [rec.getMessage() for rec in caplog.records if rec.name.startswith("fieldshift")]
    assert len(lines) == 1, lines
    assert not [rec for rec in caplog.records if rec.exc_info]  # no traceback: it may hold the address
    for secret in ("zz-secret", "postgresql", "127.0.0.1"):
        assert secret not in lines[0]


def test_every_database_connection_gives_up_after_5_seconds(on: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # team, 2026-11-14: a database that is down holds the start (and the farmer routes) for 5 s, not psycopg's 130 s
    timeouts: list[object] = []
    real_connect = psycopg.connect

    def connect(*args: object, **kwargs: object) -> psycopg.Connection:
        timeouts.append(kwargs.get("connect_timeout"))
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(psycopg, "connect", connect)
    TestClient(create_app(root=REPO))
    assert timeouts
    assert set(timeouts) == {5}


def test_a_database_that_goes_down_after_start_answers_503_and_logs_one_line(
    on: str, keys: dict, fetched: list, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)

    def down(*_: object, **__: object) -> None:
        raise psycopg.OperationalError('connection to server at "10.250.7.9", port 5432 failed: zz-secret')

    monkeypatch.setattr(psycopg, "connect", down)
    with caplog.at_level(logging.DEBUG):
        for method, path in ROUTES:
            body = {"json": ANSWERS} if method == "post" else {}
            r = getattr(c, method)(path, headers=me, **body)
            assert r.status_code == 503, path
            assert r.json() == {"detail": "sign-in is not available"}, path
    lines = [rec.getMessage() for rec in caplog.records if rec.name.startswith("fieldshift")]
    assert lines
    assert all(line == lines[0] for line in lines)  # the same one line per failed request
    assert not [rec for rec in caplog.records if rec.exc_info]  # no traceback: the error text holds the host
    assert "10.250.7.9" not in lines[0]
    assert "zz-secret" not in lines[0]


def test_config_names_the_client_id_when_on(on: str) -> None:
    c = TestClient(create_app(root=REPO))
    assert c.get("/api/account/config").json() == {"available": True, "client_id": CLIENT_ID}


# ---- sign-in


def test_sign_in_creates_the_account_with_only_the_google_id(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    r = c.post("/api/account/sign-in", headers=bearer(google_token(keys, email="farmer@example.com", name="Ba")))
    assert r.status_code == 204
    assert r.headers["cache-control"] == "no-store"  # RFC 6749 §5.1: answers about an account are not cached
    assert "set-cookie" not in r.headers  # H14: the page keeps Google's token in memory and sends it; no cookie
    assert rows(on, "SELECT google_sub FROM account") == [("110169484474386276334",)]
    assert urls(fetched) == [GOOGLE_CERTS]  # the one outbound call: Google's public keys, over https
    # §12c: only Google's account id and the saved answers are stored
    columns = rows(
        on,
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' "
        "ORDER BY table_name, ordinal_position",
    )
    assert columns == [
        ("account", "id"),
        ("account", "google_sub"),
        ("saved_answers", "id"),
        ("saved_answers", "account_id"),
        ("saved_answers", "land"),
        ("saved_answers", "years"),
        ("saved_answers", "priority"),
    ]
    assert "farmer@example.com" not in str(rows(on, "SELECT * FROM account"))


def test_signing_in_again_keeps_one_account(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    sign_in(c, keys)
    sign_in(c, keys)
    assert rows(on, "SELECT count(*) FROM account") == [(1,)]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"authorization": "zz-secret"},
        {"authorization": "Basic zz-secret"},
        {"authorization": "Bearer zz-secret"},
        {"authorization": "Bearer "},
    ],
)
def test_no_google_token_is_401_without_echo_on_every_route(on: str, fetched: list, headers: dict) -> None:
    c = TestClient(create_app(root=REPO))
    for method, path in ROUTES:
        r = getattr(c, method)(path, headers=headers)
        no_echo(r, 401)
        assert r.headers["www-authenticate"] == "Bearer"  # RFC 6750 §3
    assert rows(on, "SELECT count(*) FROM account") == [(0,)]


@pytest.mark.parametrize(
    "token",
    [
        lambda keys: google_token(keys, aud="someone-else.apps.googleusercontent.com"),  # audience = our client id
        lambda keys: google_token(keys, iss="https://zz-secret.example.com"),  # issuer = Google
        lambda keys: google_token(keys, exp=int(time.time()) - 60),  # expired
        lambda keys: google_token(keys, kid="stranger"),  # not signed by Google's key
        lambda keys: google_token(keys, sub=""),  # no account id
    ],
)
def test_a_token_google_did_not_issue_to_us_is_401_on_every_route(
    on: str, keys: dict, fetched: list, token: Callable[[dict], str]
) -> None:
    c = TestClient(create_app(root=REPO))
    sign_in(c, keys)  # the account exists, so only the token check can refuse the other routes
    for method, path in ROUTES:
        no_echo(getattr(c, method)(path, headers=bearer(token(keys))), 401)
    assert rows(on, "SELECT count(*) FROM account") == [(1,)]


def test_a_valid_token_without_a_sign_in_is_401(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    for method, path in ROUTES[1:]:
        no_echo(getattr(c, method)(path, headers=bearer(google_token(keys))), 401)
    assert rows(on, "SELECT count(*) FROM account") == [(0,)]


def test_every_account_route_answers_503_when_google_keys_cannot_be_fetched(
    on: str, keys: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreachable(*_: object, **__: object) -> None:
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(urllib.request, "urlopen", unreachable)
    c = TestClient(create_app(root=REPO))
    for method, path in ROUTES:
        r = getattr(c, method)(path, headers=bearer(google_token(keys)))
        assert r.status_code == 503, path
        assert r.json() == {"detail": "google sign-in check is not reachable"}, path


def test_google_keys_are_downloaded_once_while_google_says_they_are_fresh(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    c.post("/api/account/saved", headers=me, json=ANSWERS)
    c.get("/api/account/saved", headers=me)
    assert urls(fetched) == [GOOGLE_CERTS]  # the max-age of Google's Cache-Control header has not run out


# ---- account requests never hold the farmer routes


def test_farmer_routes_answer_promptly_while_the_key_download_is_slow(
    on: str, keys: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # security review of the pull request: 80 junk tokens, each starting its own slow key download in the shared
    # worker threads, held GET /api/past-years for 5.6 s
    calls: list[str] = []

    def slow_urlopen(request: urllib.request.Request, **_: object) -> Answer:
        calls.append(request.full_url)
        time.sleep(3)
        return Answer(public_keys(keys))

    monkeypatch.setattr(urllib.request, "urlopen", slow_urlopen)
    with TestClient(create_app(root=REPO)) as c, ThreadPoolExecutor(80) as pool:
        junk = [pool.submit(c.get, "/api/account/saved", headers=bearer("zz-secret")) for _ in range(80)]
        time.sleep(0.5)  # the junk requests are now waiting on the download
        started = time.monotonic()
        assert c.get("/api/past-years", params={"province": "nghe_an"}).status_code == 200
        waited = time.monotonic() - started
        assert all(f.result().status_code == 401 for f in junk)
    assert waited < 1.0, waited
    assert calls == [GOOGLE_CERTS]  # one download at a time; the waiting requests use its result


def test_a_failed_key_download_is_not_retried_at_once(on: str, keys: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def unreachable(request: urllib.request.Request, **_: object) -> None:
        calls.append(request.full_url)
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(urllib.request, "urlopen", unreachable)
    c = TestClient(create_app(root=REPO))
    for _ in range(5):
        assert c.post("/api/account/sign-in", headers=bearer(google_token(keys))).status_code == 503
    assert calls == [GOOGLE_CERTS]  # the later requests fail fast during the pause after the failure


# ---- the download of Google's keys (standard-library transport)


def test_the_key_download_checks_tls_with_the_default_context_and_has_a_timeout(
    keys: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = fake_download(monkeypatch, Answer(public_keys(keys)))
    assert accounts.HttpsRequest()(GOOGLE_CERTS).status == 200
    [call] = calls
    assert call.timeout == 10  # team, 2026-11-14: an account request never hangs for minutes
    # Python ssl docs: ssl.create_default_context() requires a valid certificate and checks the host name
    assert call.context.verify_mode == ssl.CERT_REQUIRED
    assert call.context.check_hostname


def test_the_key_download_refuses_plain_http(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_download(monkeypatch, Answer(b"{}"))
    with pytest.raises(TransportError):
        accounts.HttpsRequest()("http://www.googleapis.com/oauth2/v1/certs")
    assert calls == []


def test_an_answer_over_the_size_cap_is_refused(on: str, keys: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_download(monkeypatch, Answer(b" " * (accounts.KEYS_MAX_BYTES + 1)))
    with pytest.raises(TransportError):
        accounts.HttpsRequest()(GOOGLE_CERTS)
    r = TestClient(create_app(root=REPO)).post("/api/account/sign-in", headers=bearer(google_token(keys)))
    assert r.status_code == 503


@pytest.mark.parametrize("cache", [None, "no-store", "public, max-age=0"])
def test_keys_without_a_fresh_cache_life_are_downloaded_again(
    keys: dict, monkeypatch: pytest.MonkeyPatch, cache: str | None
) -> None:
    calls = fake_download(monkeypatch, Answer(public_keys(keys), cache))
    download = accounts.HttpsRequest()
    download(GOOGLE_CERTS)
    download(GOOGLE_CERTS)
    assert len(calls) == 2


# ---- saved sets


def test_saved_sets_round_trip(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    assert c.get("/api/account/saved", headers=me).json() == {"saved": []}
    second = {"land": "unsure", "years": list(range(1995, 2025)), "priority": "stability"}
    made = [c.post("/api/account/saved", headers=me, json=answers) for answers in (ANSWERS, second)]
    assert [r.status_code for r in made] == [201, 201]
    ids = [r.json()["id"] for r in made]
    assert [r.json() for r in made] == [{"id": ids[0], **ANSWERS}, {"id": ids[1], **second}]
    listed = c.get("/api/account/saved", headers=me)
    assert listed.json() == {"saved": [{"id": ids[0], **ANSWERS}, {"id": ids[1], **second}]}  # D-150: several sets
    assert listed.headers["cache-control"] == "no-store"


def test_saved_sets_survive_a_restart_and_the_schema_is_kept(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    c.post("/api/account/saved", headers=sign_in(c, keys), json=ANSWERS)
    c = TestClient(create_app(root=REPO))  # the schema already exists: the start keeps it and its rows
    assert c.get("/api/account/saved", headers=sign_in(c, keys)).json()["saved"][0]["years"] == ANSWERS["years"]


@pytest.mark.parametrize(
    "body",
    [
        {**ANSWERS, "land": "irrigated"},  # §6b rule 4: irrigated never gets plans
        {**ANSWERS, "priority": "zz-secret"},
        {**ANSWERS, "years": [2007, 1995]},  # strictly ascending
        {**ANSWERS, "years": [1994]},  # within 1995-2024
        {**ANSWERS, "years": []},  # §6b rule 3
        {**ANSWERS, "years": ["2001"]},
        {**ANSWERS, "name": "zz-secret"},  # no free text: the saved set is the three answers only
        {**ANSWERS, "province": "nghe_an"},
        {k: v for k, v in ANSWERS.items() if k != "land"},
    ],
)
def test_saved_answers_follow_the_compare_request_rules(on: str, keys: dict, fetched: list, body: dict) -> None:
    c = TestClient(create_app(root=REPO))
    r = c.post("/api/account/saved", headers=sign_in(c, keys), json=body)
    no_echo(r, 422)
    assert all(set(item) == {"type", "loc", "msg"} for item in r.json()["detail"])
    assert rows(on, "SELECT count(*) FROM saved_answers") == [(0,)]


def test_saved_answers_over_the_body_limit_are_422(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    content = json.dumps(ANSWERS).encode()
    padded = content + b" " * (MAX_BODY_BYTES + 1 - len(content))
    headers = {**sign_in(c, keys), "content-type": "application/json"}
    no_echo(c.post("/api/account/saved", headers=headers, content=padded), 422)


def test_another_account_can_neither_read_nor_delete_my_sets(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    other = sign_in(c, keys, sub="222222222222222222222")
    mine = c.post("/api/account/saved", headers=me, json=ANSWERS).json()["id"]
    assert c.get("/api/account/saved", headers=other).json() == {"saved": []}
    assert c.delete(f"/api/account/saved/{mine}", headers=other).status_code == 404  # the same answer as no such set
    assert c.delete("/api/account", headers=other).status_code == 204
    assert [s["id"] for s in c.get("/api/account/saved", headers=me).json()["saved"]] == [mine]


def test_deleting_one_set_keeps_the_others(on: str, keys: dict, fetched: list) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    first, second = (c.post("/api/account/saved", headers=me, json=ANSWERS).json()["id"] for _ in range(2))
    assert c.delete(f"/api/account/saved/{first}", headers=me).status_code == 204
    assert [s["id"] for s in c.get("/api/account/saved", headers=me).json()["saved"]] == [second]
    assert c.delete(f"/api/account/saved/{first}", headers=me).status_code == 404


@pytest.mark.parametrize("set_id", ["0", "-1", "9223372036854775808", "zz-secret"])
def test_a_set_id_outside_the_database_range_is_422(on: str, keys: dict, fetched: list, set_id: str) -> None:
    c = TestClient(create_app(root=REPO))
    no_echo(c.delete(f"/api/account/saved/{set_id}", headers=sign_in(c, keys)), 422)


def test_delete_everything_leaves_no_row_and_ends_the_sign_in(on: str, keys: dict, fetched: list) -> None:
    # §12c: one call deletes the account and all saved answers
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    for _ in range(3):
        c.post("/api/account/saved", headers=me, json=ANSWERS)
    assert c.delete("/api/account", headers=me).status_code == 204
    assert rows(on, "SELECT count(*) FROM account") == [(0,)]
    assert rows(on, "SELECT count(*) FROM saved_answers") == [(0,)]
    assert c.get("/api/account/saved", headers=me).status_code == 401


# ---- more than one server


def test_another_server_instance_accepts_the_same_sign_in(on: str, keys: dict, fetched: list) -> None:
    # the database lets more than one instance serve, and a restart signs nobody out
    me = sign_in(TestClient(create_app(root=REPO)), keys)
    assert TestClient(create_app(root=REPO)).get("/api/account/saved", headers=me).status_code == 200


# ---- the farmer routes with sign-in on


def test_farmer_routes_set_no_cookie_and_call_no_network_with_sign_in_on(
    on: str, keys: dict, fetched: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    # NFR-01 and T14 with sign-in on: only loopback (the test database); Google's key download is the stated exception
    real_connect = socket.socket.connect

    def local_only(sock: socket.socket, address: object) -> None:
        if not (isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1")):
            raise AssertionError(f"outbound network call to {address}")
        real_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)
    c = TestClient(create_app(root=REPO))
    body = {"province": "nghe_an", **ANSWERS}
    for r in (c.get("/api/health"), c.get("/api/past-years", params={"province": "nghe_an"})):
        assert r.status_code == 200
        assert "set-cookie" not in r.headers
    r = c.post("/api/compare", json=body)
    assert r.status_code == 200
    assert "set-cookie" not in r.headers
    sign_in(c, keys)
    assert urls(fetched) == [GOOGLE_CERTS]
