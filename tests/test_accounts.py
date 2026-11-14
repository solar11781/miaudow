"""Tests for the optional Google sign-in and saved answers (accounts.py and its routes in app.py), written first.

Spec: UI-UX-SPEC §12c (every farmer route works without signing in; store only Google's account id and the saved
answers; a delete-everything call; several saved sets per account), §6b (the answers: land, years, priority, with the
same rules as the compare request), H14 (no cookie). The routes are on only when GOOGLE_CLIENT_ID and DATABASE_URL are
both set; otherwise they answer 503. The database is a throwaway PostgreSQL 17: TEST_DATABASE_URL when set (the
service container in CI), otherwise a container this module starts with Docker; the module is skipped with the reason
when neither is available. Google's token check runs for real on tokens signed with a test key; only the download of
Google's public keys is replaced, so no test touches the network.
"""

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt

from fieldshift.api import accounts
from fieldshift.api.app import MAX_BODY_BYTES, create_app

REPO = Path(__file__).resolve().parents[1]
CLIENT_ID = "test-client.apps.googleusercontent.com"
GOOGLE_CERTS = "https://www.googleapis.com/oauth2/v1/certs"  # google-auth 2.62.2, google/oauth2/id_token.py
ANSWERS = {"land": "dry", "years": [1995, 2007, 2013], "priority": "income"}
ROUTES = [
    ("post", "/api/account/sign-in"),
    ("get", "/api/account/saved"),
    ("post", "/api/account/saved"),
    ("delete", "/api/account/saved/1"),
    ("delete", "/api/account"),
]


# ---- a throwaway PostgreSQL 17


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
        docker, "run", "-d", "--rm", "-e", "POSTGRES_PASSWORD=test", "-p", "127.0.0.1::5432", "postgres:17"
    )
    if started.returncode != 0:
        pytest.skip(f"Docker could not start postgres:17: {started.stderr.strip()[:300]}")
    container = started.stdout.strip()
    try:
        port = _docker(docker, "port", container, "5432/tcp").stdout.strip().rsplit(":", 1)[-1]
        url = f"postgresql://postgres:test@127.0.0.1:{port}/postgres"
        if not _ready(url, 60):
            pytest.fail("the postgres:17 container did not accept connections within 60 s")
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


@pytest.fixture
def fetched(keys: dict[str, rsa.RSAPrivateKey], monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Google's key download answered locally with the public half of the "google" key; returns the URLs asked for."""
    asked: list[str] = []
    public = (
        keys["google"]
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    body = json.dumps({"google": public.decode()}).encode()

    class Answer:
        def __init__(self) -> None:
            self.status, self.headers = 200, {"content-type": "application/json"}

        def read(self) -> bytes:
            return body

        def __enter__(self) -> "Answer":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def fake_urlopen(request: urllib.request.Request, timeout: float | None = None) -> Answer:
        asked.append(request.full_url)
        return Answer()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return asked


def google_token(keys: dict[str, rsa.RSAPrivateKey], kid: str = "google", **changes: object) -> str:
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": "110169484474386276334", "iat": now}
    claims |= {"exp": now + 3600, **changes}
    return jwt.encode(crypt.RSASigner.from_string(_pem(keys[kid]), key_id=kid), claims).decode()


def bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def sign_in(c: TestClient, keys: dict[str, rsa.RSAPrivateKey], **changes: object) -> dict[str, str]:
    r = c.post("/api/account/sign-in", headers=bearer(google_token(keys, **changes)))
    assert r.status_code == 200, r.text
    return bearer(r.json()["token"])


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


def test_config_names_the_client_id_when_on(on: str) -> None:
    c = TestClient(create_app(root=REPO))
    assert c.get("/api/account/config").json() == {"available": True, "client_id": CLIENT_ID}


# ---- sign-in


def test_sign_in_creates_the_account_with_only_the_google_id(on: str, keys: dict, fetched: list[str]) -> None:
    c = TestClient(create_app(root=REPO))
    r = c.post("/api/account/sign-in", headers=bearer(google_token(keys, email="farmer@example.com", name="Ba")))
    assert r.status_code == 200
    assert set(r.json()) == {"token", "expires_at"}
    assert r.headers["cache-control"] == "no-store"  # RFC 6749 §5.1: token responses are not cached
    assert "set-cookie" not in r.headers  # H14: the session is a bearer token the page keeps in memory
    assert rows(on, "SELECT google_sub FROM account") == [("110169484474386276334",)]
    assert fetched == [GOOGLE_CERTS]  # the one outbound call: Google's public keys, over https
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


def test_signing_in_again_keeps_one_account(on: str, keys: dict, fetched: list[str]) -> None:
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
def test_sign_in_without_a_google_token_is_401_without_echo(on: str, fetched: list[str], headers: dict) -> None:
    no_echo(TestClient(create_app(root=REPO)).post("/api/account/sign-in", headers=headers), 401)
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
def test_sign_in_with_a_token_google_did_not_issue_to_us_is_401(
    on: str, keys: dict, fetched: list[str], token: Callable[[dict], str]
) -> None:
    no_echo(TestClient(create_app(root=REPO)).post("/api/account/sign-in", headers=bearer(token(keys))), 401)
    assert rows(on, "SELECT count(*) FROM account") == [(0,)]


def test_sign_in_answers_503_when_google_keys_cannot_be_fetched(
    on: str, keys: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreachable(*_: object, **__: object) -> None:
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(urllib.request, "urlopen", unreachable)
    r = TestClient(create_app(root=REPO)).post("/api/account/sign-in", headers=bearer(google_token(keys)))
    assert r.status_code == 503
    assert r.json() == {"detail": "google sign-in check is not reachable"}


# ---- saved sets


def test_saved_sets_round_trip(on: str, keys: dict, fetched: list[str]) -> None:
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


def test_saved_sets_survive_a_restart_and_the_schema_is_kept(on: str, keys: dict, fetched: list[str]) -> None:
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
def test_saved_answers_follow_the_compare_request_rules(on: str, keys: dict, fetched: list[str], body: dict) -> None:
    c = TestClient(create_app(root=REPO))
    r = c.post("/api/account/saved", headers=sign_in(c, keys), json=body)
    no_echo(r, 422)
    assert all(set(item) == {"type", "loc", "msg"} for item in r.json()["detail"])
    assert rows(on, "SELECT count(*) FROM saved_answers") == [(0,)]


def test_saved_answers_over_the_body_limit_are_422(on: str, keys: dict, fetched: list[str]) -> None:
    c = TestClient(create_app(root=REPO))
    content = json.dumps(ANSWERS).encode()
    padded = content + b" " * (MAX_BODY_BYTES + 1 - len(content))
    headers = {**sign_in(c, keys), "content-type": "application/json"}
    no_echo(c.post("/api/account/saved", headers=headers, content=padded), 422)


def test_another_account_can_neither_read_nor_delete_my_sets(on: str, keys: dict, fetched: list[str]) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    other = sign_in(c, keys, sub="222222222222222222222")
    mine = c.post("/api/account/saved", headers=me, json=ANSWERS).json()["id"]
    assert c.get("/api/account/saved", headers=other).json() == {"saved": []}
    assert c.delete(f"/api/account/saved/{mine}", headers=other).status_code == 404  # the same answer as no such set
    assert c.delete("/api/account", headers=other).status_code == 204
    assert [s["id"] for s in c.get("/api/account/saved", headers=me).json()["saved"]] == [mine]


def test_deleting_one_set_keeps_the_others(on: str, keys: dict, fetched: list[str]) -> None:
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    first, second = (c.post("/api/account/saved", headers=me, json=ANSWERS).json()["id"] for _ in range(2))
    assert c.delete(f"/api/account/saved/{first}", headers=me).status_code == 204
    assert [s["id"] for s in c.get("/api/account/saved", headers=me).json()["saved"]] == [second]
    assert c.delete(f"/api/account/saved/{first}", headers=me).status_code == 404


@pytest.mark.parametrize("set_id", ["0", "-1", "9223372036854775808", "zz-secret"])
def test_a_set_id_outside_the_database_range_is_422(on: str, keys: dict, fetched: list[str], set_id: str) -> None:
    c = TestClient(create_app(root=REPO))
    no_echo(c.delete(f"/api/account/saved/{set_id}", headers=sign_in(c, keys)), 422)


def test_delete_everything_leaves_no_row_and_ends_the_session(on: str, keys: dict, fetched: list[str]) -> None:
    # §12c: one call deletes the account and all saved answers
    c = TestClient(create_app(root=REPO))
    me = sign_in(c, keys)
    for _ in range(3):
        c.post("/api/account/saved", headers=me, json=ANSWERS)
    assert c.delete("/api/account", headers=me).status_code == 204
    assert rows(on, "SELECT count(*) FROM account") == [(0,)]
    assert rows(on, "SELECT count(*) FROM saved_answers") == [(0,)]
    assert c.get("/api/account/saved", headers=me).status_code == 401


# ---- the session token


@pytest.mark.parametrize("token", ["zz-secret", "1.9999999999.zz-secret", "1.9999999999", ""])
def test_a_bad_session_token_is_401_without_echo(on: str, token: str) -> None:
    c = TestClient(create_app(root=REPO))
    for method, path in ROUTES[1:]:
        r = getattr(c, method)(path, headers=bearer(token))
        no_echo(r, 401)
        assert r.headers["www-authenticate"] == "Bearer"  # RFC 6750 §3


def test_a_session_token_cannot_be_changed_to_another_account(on: str, keys: dict, fetched: list[str]) -> None:
    c = TestClient(create_app(root=REPO))
    sign_in(c, keys, sub="111")
    token = sign_in(c, keys, sub="222")["authorization"].removeprefix("Bearer ")
    account, expires, signature = token.split(".")
    forged = f"{int(account) - 1}.{expires}.{signature}"
    no_echo(c.get("/api/account/saved", headers=bearer(forged)), 401)


def test_the_session_ends_when_the_google_token_expires(
    on: str, keys: dict, fetched: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    c = TestClient(create_app(root=REPO))
    expires = int(time.time()) + 120
    me = sign_in(c, keys, exp=expires)
    assert c.get("/api/account/saved", headers=me).status_code == 200
    monkeypatch.setattr(accounts, "time", SimpleNamespace(time=lambda: expires + 1))
    assert c.get("/api/account/saved", headers=me).status_code == 401


def test_a_restart_ends_every_session(on: str, keys: dict, fetched: list[str]) -> None:
    me = sign_in(TestClient(create_app(root=REPO)), keys)
    assert TestClient(create_app(root=REPO)).get("/api/account/saved", headers=me).status_code == 401


# ---- the farmer routes with sign-in on


def test_farmer_routes_set_no_cookie_and_call_no_network_with_sign_in_on(
    on: str, keys: dict, fetched: list[str], monkeypatch: pytest.MonkeyPatch
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
    assert fetched == [GOOGLE_CERTS]
