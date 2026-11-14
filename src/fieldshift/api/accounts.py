"""Optional Google sign-in and saved answers (UI-UX-SPEC §12c): account check, session tokens and the database.

On only when both GOOGLE_CLIENT_ID and DATABASE_URL are set. A Google ID token is checked on the server by google-auth
(signature, audience = our client id, issuer = Google, expiry); only its `sub` (Google's account id) is kept. Downloading
Google's public keys for that check is the one outbound call, the sign-in exception that NFR-01 allows. The session is a
bearer token signed with a key made at start, so the page keeps it in memory and no cookie is set (H14); it ends when
the Google token expires or the server restarts. The database holds two tables: account (Google's account id) and
saved_answers (land, years, priority of one saved set). SQL is parameterised; nothing is logged.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import time
import urllib.error
import urllib.request
from collections.abc import Mapping

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
KEY_BYTES = 32  # RFC 2104 §3: an HMAC key at least as long as the hash output (32 bytes for SHA-256)
# account id and expiry (at most the 19 digits of a PostgreSQL bigint), then the SHA-256 HMAC in hex
TOKEN = re.compile(r"([0-9]{1,19})\.([0-9]{1,19})\.([0-9a-f]{64})")
GOOGLE_TIMEOUT_SECONDS = 120  # google-auth's own default for its requests transport (google/auth/transport/requests.py)


class NotSignedInError(Exception):
    """No valid Google token at sign-in, or no valid session token afterwards."""


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


class Session(Contract):
    token: str
    expires_at: int


class _Answer(transport.Response):
    def __init__(self, status: int, headers: Mapping[str, str], data: bytes) -> None:
        self._status, self._headers, self._data = status, dict(headers), data

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> Mapping[str, str]:
        return self._headers

    @property
    def data(self) -> bytes:
        return self._data


class _HttpsRequest(transport.Request):
    """google-auth's transport interface on the standard library, so no further HTTP package is needed."""

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
        request = urllib.request.Request(url, data=body, headers=dict(headers or {}), method=method)  # noqa: S310  https checked above
        try:
            with urllib.request.urlopen(request, timeout=timeout or GOOGLE_TIMEOUT_SECONDS) as answer:  # noqa: S310  https checked above
                return _Answer(answer.status, answer.headers, answer.read())
        except urllib.error.HTTPError as err:
            return _Answer(err.code, err.headers, err.read())
        except OSError as err:
            raise exceptions.TransportError("Google's keys could not be downloaded") from err


class Accounts:
    def __init__(self, client_id: str, database_url: str) -> None:
        self.client_id = client_id
        self._url = database_url
        self._key = secrets.token_bytes(KEY_BYTES)
        with self._connect() as conn:
            for statement in SCHEMA:
                conn.execute(statement)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._url)

    # ---- sign-in and sessions

    def sign_in(self, google_token: str) -> Session:
        try:
            claims = id_token.verify_oauth2_token(google_token, _HttpsRequest(), audience=self.client_id)
        except exceptions.TransportError as err:
            raise GoogleUnreachableError from err
        except (ValueError, exceptions.GoogleAuthError) as err:
            raise NotSignedInError from err
        sub, expires_at = claims.get("sub"), claims.get("exp")
        if not isinstance(sub, str) or not sub or not isinstance(expires_at, int):
            raise NotSignedInError
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO account (google_sub) VALUES (%s)"
                " ON CONFLICT (google_sub) DO UPDATE SET google_sub = EXCLUDED.google_sub RETURNING id",
                (sub,),
            ).fetchone()
        return Session(token=self._sign(row[0], expires_at), expires_at=expires_at)

    def _signature(self, payload: str) -> str:
        return hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()

    def _sign(self, account: int, expires_at: int) -> str:
        payload = f"{account}.{expires_at}"
        return f"{payload}.{self._signature(payload)}"

    def account(self, token: str) -> int:
        """The account of a session token that this server signed, that has not expired, and whose account exists."""
        parts = TOKEN.fullmatch(token)
        if parts is None:
            raise NotSignedInError
        account, expires_at, signature = parts.groups()
        if not hmac.compare_digest(signature, self._signature(f"{account}.{expires_at}")):
            raise NotSignedInError
        if int(expires_at) <= time.time():
            raise NotSignedInError
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM account WHERE id = %s", (int(account),)).fetchone() is None:
                raise NotSignedInError
        return int(account)

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
