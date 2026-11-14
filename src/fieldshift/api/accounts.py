"""Optional Google sign-in and saved answers (UI-UX-SPEC §12c): the Google token check and the database.

On only when both GOOGLE_CLIENT_ID and DATABASE_URL are set and the database answers at start. The page keeps Google's
ID token in memory and sends it as `Authorization: Bearer` with every account request, so no cookie is set (H14) and
any server instance can answer. Each request is checked on the server by google-auth (signature, audience = our client
id, issuer = Google, expiry); only the token's `sub` (Google's account id) is kept. Downloading Google's public keys for
that check is the one outbound call, the sign-in exception that NFR-01 allows; the keys are kept as long as Google's
Cache-Control header says. The database holds two tables: account (Google's account id) and saved_answers (land,
years, priority of one saved set). SQL is parameterised; nothing personal is logged.
"""

from __future__ import annotations

import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from http import HTTPStatus

import psycopg
from google.auth import exceptions, transport
from google.oauth2 import id_token

from fieldshift.engine.schemas import Contract, Land, Priority, Years

LOG = logging.getLogger(__name__)
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS account ("
    " id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, google_sub text NOT NULL UNIQUE)",
    "CREATE TABLE IF NOT EXISTS saved_answers ("
    " id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,"
    " account_id bigint NOT NULL REFERENCES account (id) ON DELETE CASCADE,"
    " land text NOT NULL, years integer[] NOT NULL, priority text NOT NULL)",
)
BIGINT_MAX = 2**63 - 1  # largest PostgreSQL bigint, the type of every id (PostgreSQL 18 docs, numeric types)
GOOGLE_TIMEOUT_SECONDS = 120  # google-auth's own default for its requests transport (google/auth/transport/requests.py)
# Google's key answer was 2447 bytes (measured 2026-11-14); 64 KiB leaves room for many more keys
KEYS_MAX_BYTES = 65536
MAX_AGE = re.compile(r"(?:^|,)\s*max-age=(\d+)\s*(?:,|$)")
NO_CACHE = re.compile(r"(?:^|,)\s*(?:no-store|no-cache)\s*(?:,|$)")


class NotSignedInError(Exception):
    """No valid Google token, or no account for it (the farmer has not signed in or deleted everything)."""


class GoogleUnreachableError(Exception):
    """Google's public keys could not be downloaded, so no token can be checked."""


class SavedAnswers(Contract):
    """One saved set: the answers of steps 1-3 (UI-UX-SPEC §6b), checked like the compare request."""

    land: Land
    years: Years
    priority: Priority


class SavedSet(SavedAnswers):
    id: int


class SavedList(Contract):
    saved: list[SavedSet]


class SignInConfig(Contract):
    """Whether sign-in is on, and the public Google client id the page needs to start Google's sign-in."""

    available: bool
    client_id: str | None


class _Answer(transport.Response):
    def __init__(self, status: int, headers: Mapping[str, str], data: bytes) -> None:
        self._status, self._headers, self._data = status, {k.lower(): v for k, v in headers.items()}, data

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> Mapping[str, str]:
        return self._headers

    @property
    def data(self) -> bytes:
        return self._data


def _fresh_for(headers: Mapping[str, str]) -> int:
    """Seconds an answer may be reused (RFC 9111 §5.2.2: max-age; no-store and no-cache mean not at all)."""
    cache = headers.get("cache-control", "").lower()
    found = MAX_AGE.search(cache)
    return 0 if found is None or NO_CACHE.search(cache) else int(found.group(1))


class HttpsRequest(transport.Request):
    """google-auth's transport interface on the standard library (no further HTTP package is approved): https only,
    TLS checked with the default context, a timeout, a size cap, and Google's key answer reused while it is fresh."""

    def __init__(self) -> None:
        self._kept: dict[str, tuple[float, _Answer]] = {}

    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        **_: object,
    ) -> _Answer:
        if not url.startswith("https://"):
            raise exceptions.TransportError("only https is used for Google's keys")
        kept = self._kept.get(url)
        if method == "GET" and kept is not None and kept[0] > time.monotonic():
            return kept[1]
        answer = self._fetch(url, method, body, headers, timeout)
        if method == "GET" and answer.status == HTTPStatus.OK and (seconds := _fresh_for(answer.headers)):
            self._kept[url] = (time.monotonic() + seconds, answer)
        return answer

    @staticmethod
    def _fetch(
        url: str, method: str, body: bytes | None, headers: Mapping[str, str] | None, timeout: float | None
    ) -> _Answer:
        request = urllib.request.Request(url, data=body, headers=dict(headers or {}), method=method)  # noqa: S310  https checked by the caller
        try:
            with urllib.request.urlopen(  # noqa: S310  https checked by the caller
                request, timeout=timeout or GOOGLE_TIMEOUT_SECONDS, context=ssl.create_default_context()
            ) as answer:
                data = answer.read(KEYS_MAX_BYTES + 1)
                status, answer_headers = answer.status, dict(answer.headers)
        except urllib.error.HTTPError as err:
            return _Answer(err.code, {}, b"")
        except OSError as err:
            raise exceptions.TransportError("Google's keys could not be downloaded") from err
        if len(data) > KEYS_MAX_BYTES:
            raise exceptions.TransportError(f"Google's key answer is over {KEYS_MAX_BYTES} bytes")
        return _Answer(status, answer_headers, data)


class Accounts:
    def __init__(self, client_id: str, database_url: str) -> None:
        self.client_id = client_id
        self._url = database_url
        self._google = HttpsRequest()
        with self._connect() as conn:
            for statement in SCHEMA:
                conn.execute(statement)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._url)

    # ---- the Google token

    def _google_id(self, google_token: str) -> str:
        """Google's account id from a token that Google issued to our client id and that has not expired."""
        try:
            claims = id_token.verify_oauth2_token(google_token, self._google, audience=self.client_id)
        except exceptions.TransportError as err:
            raise GoogleUnreachableError from err
        except (ValueError, exceptions.GoogleAuthError) as err:
            raise NotSignedInError from err
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub:
            raise NotSignedInError
        return sub

    def sign_in(self, google_token: str) -> None:
        """Create the account of a valid token, or keep the one that exists."""
        sub = self._google_id(google_token)
        with self._connect() as conn:
            conn.execute("INSERT INTO account (google_sub) VALUES (%s) ON CONFLICT (google_sub) DO NOTHING", (sub,))

    def account(self, google_token: str) -> int:
        """The account of a valid token; NotSignedInError when it never signed in or deleted everything."""
        sub = self._google_id(google_token)
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM account WHERE google_sub = %s", (sub,)).fetchone()
        if row is None:
            raise NotSignedInError
        return row[0]

    # ---- saved sets

    def saved(self, account: int) -> SavedList:
        with self._connect() as conn:
            found = conn.execute(
                "SELECT id, land, years, priority FROM saved_answers WHERE account_id = %s ORDER BY id", (account,)
            ).fetchall()
        return SavedList(saved=[SavedSet(id=i, land=land, years=y, priority=p) for i, land, y, p in found])

    def save(self, account: int, answers: SavedAnswers) -> SavedSet:
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO saved_answers (account_id, land, years, priority) VALUES (%s, %s, %s, %s) RETURNING id",
                (account, answers.land, answers.years, answers.priority),
            ).fetchone()
        return SavedSet(id=row[0], **answers.model_dump())

    def delete(self, account: int, set_id: int) -> bool:
        """Delete one of the account's sets; False when the account has no set with that id."""
        with self._connect() as conn:
            gone = conn.execute("DELETE FROM saved_answers WHERE id = %s AND account_id = %s", (set_id, account))
            return gone.rowcount == 1

    def delete_account(self, account: int) -> None:
        """Delete the account and, through ON DELETE CASCADE, every saved set of it, in one statement."""
        with self._connect() as conn:
            conn.execute("DELETE FROM account WHERE id = %s", (account,))


def accounts_from(environ: Mapping[str, str]) -> Accounts | None:
    """Sign-in on when both settings are set and the database answers at start, otherwise off (None).

    A database that is down never stops the start, because every farmer route must work without sign-in (UI-UX-SPEC
    §12c). The log line names no address and carries no traceback, since the connection error text holds the host.
    """
    client_id, database_url = environ.get("GOOGLE_CLIENT_ID"), environ.get("DATABASE_URL")
    if not (client_id and database_url):
        return None
    try:
        return Accounts(client_id, database_url)
    except psycopg.Error:
        LOG.warning("sign-in is off: the database did not answer at start")
        return None
