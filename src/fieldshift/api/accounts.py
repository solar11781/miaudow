"""Optional Google sign-in and saved answers (UI-UX-SPEC §12c): the Google token check and the database.

On only when both GOOGLE_CLIENT_ID and DATABASE_URL are set and the database answers at start. The page keeps Google's
ID token in memory and sends it as `Authorization: Bearer` with every account request, so no cookie is set (H14) and
any server instance can answer. Each request is checked on the server by google-auth (signature, audience = our client
id, issuer = Google, expiry with CLOCK_SKEW_SECONDS of allowance); only the token's `sub` (Google's account id) is
kept. Downloading Google's public keys for that check is the one outbound call, the sign-in exception that NFR-01
allows; the keys are kept as long as Google's Cache-Control header says. The database holds two tables: account
(Google's account id) and saved_answers (land, years, priority and the typed prices and costs of one saved set,
D-180), at most SAVED_SETS_MAX sets per account. SQL is parameterised; nothing personal is logged.
"""

from __future__ import annotations

import http.client
import logging
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from http import HTTPStatus
from typing import Annotated, Literal

import psycopg
from google.auth import exceptions, transport
from google.oauth2 import id_token
from psycopg.types.json import Jsonb
from pydantic import Field, ValidationError, ValidatorFunctionWrapHandler, WrapValidator

from fieldshift.engine.rules import load_plans
from fieldshift.engine.schemas import Contract, Priority, Years
from fieldshift.paths import project_root

LOG = logging.getLogger(__name__)
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS account ("
    " id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, google_sub text NOT NULL UNIQUE)",
    "CREATE TABLE IF NOT EXISTS saved_answers ("
    " id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,"
    " account_id bigint NOT NULL REFERENCES account (id) ON DELETE CASCADE,"
    " land text NOT NULL, years integer[] NOT NULL, priority text NOT NULL)",
    # D-180: added to a table that already holds rows on Railway, so its older rows read back with empty maps
    "ALTER TABLE saved_answers ADD COLUMN IF NOT EXISTS prices jsonb NOT NULL DEFAULT '{}'",
    "ALTER TABLE saved_answers ADD COLUMN IF NOT EXISTS costs jsonb NOT NULL DEFAULT '{}'",
)
BIGINT_MAX = 2**63 - 1  # largest PostgreSQL bigint, the type of every id (PostgreSQL 18 docs, numeric types)
GOOGLE_TIMEOUT_SECONDS = 10  # D-164: an account request must not hang for minutes on Google's keys
DB_CONNECT_TIMEOUT_SECONDS = 5  # D-164: a down database must not hold the start for psycopg's 130 s
# D-165: the default of Google's own Node (CLOCK_SKEW_SECS_ = 300, google-auth-library-nodejs oauth2client.ts) and
# Java (DEFAULT_TIME_SKEW_SECONDS = 300, google-oauth-java-client IdTokenVerifier.java) ID-token verifiers, within
# RFC 7519 4.1.4's "no more than a few minutes"
CLOCK_SKEW_SECONDS = 300
SAVED_SETS_MAX = 20  # D-165: an account keeps at most 20 saved sets; a 21st save answers 409
# D-164: Google's key answer was 2447 bytes (measured 2026-11-14); 64 KiB leaves room for many more keys
KEYS_MAX_BYTES = 65536
KEYS_RETRY_SECONDS = 30  # D-164: a short pause after a failed download, so repeated requests fail fast with 503
# the farmer's own field answer in member B's names (D-169), so a saved set reopens as that answer; "reliable" (an
# irrigated field) gets no compare (UI-UX-SPEC §6b rule 4), so it is never saved
FieldAnswer = Literal["high_field", "canal_end", "water_short", "ask"]
# rows of the first API (PR #48) kept the compare request's land; they read as the answers the page reopened them as
LEGACY_LAND = {"dry": "water_short", "unsure": "ask"}
# D-180: the typed prices and costs are checked as the page checks them: crop keys of rules/rotations.yaml only, so at
# most one entry per crop key, and ASCII digits, at most 9 (D-179)
CROP_KEYS = frozenset(season.crop_key for plan in load_plans(project_root()) for season in plan.seasons)
WHOLE = re.compile(r"[0-9]{1,9}")
MAX_AGE = re.compile(r"(?:^|,)\s*max-age=(\d+)\s*(?:,|$)")
NO_CACHE = re.compile(r"(?:^|,)\s*(?:no-store|no-cache)\s*(?:,|$)")


class NotSignedInError(Exception):
    """No valid Google token, or no account for it (the farmer has not signed in or deleted everything)."""


class DatabaseDownError(Exception):
    """The database stopped answering after start; sign-in answers 503 until it is back."""


class SavedSetsFullError(Exception):
    """The account already keeps SAVED_SETS_MAX saved sets; one must be deleted before the next save."""


class GoogleUnreachableError(Exception):
    """Google's public keys could not be downloaded, so no token can be checked."""


def _own_numbers(value: object, handler: ValidatorFunctionWrapHandler) -> dict[str, str]:
    """A map of crop key to digits as the page keeps it (D-180), refused as a whole with a fixed message, so a 422
    never echoes a key or a number the client sent."""
    message = "must map crop keys of rules/rotations.yaml to 1 to 9 digits"
    try:
        own: dict[str, str] = handler(value)
    except ValidationError as err:
        raise ValueError(message) from err
    if not all(key in CROP_KEYS and WHOLE.fullmatch(digits) for key, digits in own.items()):
        raise ValueError(message)
    return own


OwnNumbers = Annotated[dict[str, str], WrapValidator(_own_numbers)]


class SavedAnswers(Contract):
    """One saved set: the answers of steps 1-3 (UI-UX-SPEC §6b), years and priority checked like the compare request,
    and the typed prices (đ/kg) and costs (thousand đ/ha) by crop key, empty when none were typed (D-180)."""

    land: FieldAnswer
    years: Years
    priority: Priority
    prices: OwnNumbers = Field(default_factory=dict)
    costs: OwnNumbers = Field(default_factory=dict)


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
        self._failed_until: dict[str, float] = {}
        self._one_at_a_time = threading.Lock()

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
        if method != "GET":
            return self._fetch(url, method, body, headers, timeout)
        with self._one_at_a_time:  # D-164: the requests waiting here then take the kept answer of this download
            kept = self._kept.get(url)
            if kept is not None and kept[0] > time.monotonic():
                return kept[1]
            if self._failed_until.get(url, 0.0) > time.monotonic():
                raise exceptions.TransportError("Google's keys failed a moment ago")
            try:
                answer = self._fetch(url, method, body, headers, timeout)
            except exceptions.TransportError:
                self._failed_until[url] = time.monotonic() + KEYS_RETRY_SECONDS
                raise
            if answer.status != HTTPStatus.OK:
                self._failed_until[url] = time.monotonic() + KEYS_RETRY_SECONDS
            elif seconds := _fresh_for(answer.headers):
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
        except (OSError, http.client.HTTPException) as err:  # http.client: IncompleteRead, BadStatusLine, LineTooLong
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
        return psycopg.connect(self._url, connect_timeout=DB_CONNECT_TIMEOUT_SECONDS)

    @contextmanager
    def _db(self) -> Iterator[psycopg.Connection]:
        """A connection for one request; a database that went down after start becomes DatabaseDownError."""
        try:
            with self._connect() as conn:
                yield conn
        except psycopg.OperationalError as err:
            LOG.warning("sign-in answered 503: the database did not answer")  # the error text holds the host
            raise DatabaseDownError from err

    # ---- the Google token

    def google_id(self, google_token: str) -> str:
        """Google's account id from a token that Google issued to our client id and that has not expired, give or take
        CLOCK_SKEW_SECONDS."""
        try:
            claims = id_token.verify_oauth2_token(
                google_token, self._google, audience=self.client_id, clock_skew_in_seconds=CLOCK_SKEW_SECONDS
            )
        except exceptions.TransportError as err:
            raise GoogleUnreachableError from err
        except (ValueError, exceptions.GoogleAuthError) as err:
            raise NotSignedInError from err
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub:
            raise NotSignedInError
        return sub

    def sign_in(self, sub: str) -> None:
        """Create the account of a checked Google account id, or keep the one that exists."""
        with self._db() as conn:
            conn.execute("INSERT INTO account (google_sub) VALUES (%s) ON CONFLICT (google_sub) DO NOTHING", (sub,))

    def account(self, sub: str) -> int:
        """The account of a checked Google account id; NotSignedInError when it never signed in or deleted
        everything."""
        with self._db() as conn:
            row = conn.execute("SELECT id FROM account WHERE google_sub = %s", (sub,)).fetchone()
        if row is None:
            raise NotSignedInError
        return row[0]

    # ---- saved sets

    def saved(self, account: int) -> SavedList:
        with self._db() as conn:
            found = conn.execute(
                "SELECT id, land, years, priority, prices, costs FROM saved_answers WHERE account_id = %s ORDER BY id",
                (account,),
            ).fetchall()
        return SavedList(
            saved=[
                SavedSet(id=i, land=LEGACY_LAND.get(land, land), years=y, priority=p, prices=prices, costs=costs)
                for i, land, y, p, prices, costs in found
            ]
        )

    def save(self, sub: str, answers: SavedAnswers) -> SavedSet:
        """Save a set for the account of `sub` in one transaction that first locks the account row, so parallel saves
        of one account count their sets one after another (SavedSetsFullError at SAVED_SETS_MAX) and a
        delete-everything waits for the save or wins before it; a save without an account is NotSignedInError and
        leaves no set behind."""
        try:
            with self._db() as conn:
                owner = conn.execute("SELECT id FROM account WHERE google_sub = %s FOR UPDATE", (sub,)).fetchone()
                if owner is None:
                    raise NotSignedInError
                # a second statement, so under READ COMMITTED it counts the sets a save committed while this one waited
                row = conn.execute(
                    "INSERT INTO saved_answers (account_id, land, years, priority, prices, costs)"
                    " SELECT %s, %s, %s, %s, %s, %s"
                    " WHERE (SELECT count(*) FROM saved_answers WHERE account_id = %s) < %s RETURNING id",
                    (
                        owner[0],
                        answers.land,
                        answers.years,
                        answers.priority,
                        Jsonb(answers.prices),
                        Jsonb(answers.costs),
                        owner[0],
                        SAVED_SETS_MAX,
                    ),
                ).fetchone()
        except psycopg.errors.ForeignKeyViolation as err:  # the account went before the insert's foreign key check
            raise NotSignedInError from err
        if row is None:
            raise SavedSetsFullError
        return SavedSet(id=row[0], **answers.model_dump())

    def delete(self, account: int, set_id: int) -> bool:
        """Delete one of the account's sets; False when the account has no set with that id."""
        with self._db() as conn:
            gone = conn.execute("DELETE FROM saved_answers WHERE id = %s AND account_id = %s", (set_id, account))
            return gone.rowcount == 1

    def delete_account(self, account: int) -> None:
        """Delete the account and, through ON DELETE CASCADE, every saved set of it, in one statement."""
        with self._db() as conn:
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
