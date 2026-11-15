"""FastAPI service (D-25, D-76, D-80; UI-UX-SPEC §11; 04-TECH-DESIGN §3). Reads precomputed artifacts only (NFR-01).

It serves GET /api/past-years, POST /api/compare, GET /api/method, GET /api/health, the method page's grid figure
GET /api/figures/nghe_an_grid.svg (UI-UX-SPEC §11b item 4), the privacy notice of the optional sign-in at
/quyen-rieng-tu (UI-UX-SPEC §12c), and that sign-in under /api/account (accounts.py; 503 while it is off). The rules
files and artifacts are read once when the app is created, so a broken or missing file stops the start instead of
failing a farmer's request, and no request reads a file. POST /api/explain, the "explain simply" call to the Claude API
(FR-15), is the one stated exception to NFR-01: off by default, it answers 503 until it is turned on, and also while
its own thread limit is full (explain.py). POST /api/copilot, member B's copilot (copilot.py, D-172), follows the same
rules: it answers 503 unless FIELDSHIFT_COPILOT is 1 and while its own thread limit is full, and it calls the Claude
API only when ANTHROPIC_API_KEY is set; without the key it answers from our own data. Invalid input gets HTTP 422
(04-TECH-DESIGN §3); an unexpected error gets a generic 500 without internals. The same service serves the built frontend (frontend/dist): every built file, and index.html
for any other path outside /api (D-102, D-166).
Run: uvicorn fieldshift.api.app:app --no-access-log --no-server-header (D-92: no request log).
"""

from __future__ import annotations

import asyncio
import functools
import html
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Annotated, TypeVar, get_args

import anyio
import anyio.to_thread
from anthropic import Anthropic
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fieldshift.api.accounts import (
    BIGINT_MAX,
    Accounts,
    DatabaseDownError,
    GoogleUnreachableError,
    NotSignedInError,
    SavedAnswers,
    SavedSetsFullError,
    SignInConfig,
    accounts_from,
)
from fieldshift.api.caps import TOO_MANY, ModelCallCaps, client_of
from fieldshift.api.copilot import (
    COPILOT_LIMIT,
    CopilotRequest,
    Corpus,
    copilot_client,
    copilot_on,
    load_corpus,
)
from fieldshift.api.copilot import answer as copilot_answer
from fieldshift.api.explain import (
    EXPLAIN_LIMIT,
    PLACEHOLDER,
    PROMPT,
    ExplainError,
    ExplainRequest,
    claude_client,
    explain,
    shown_text,
)
from fieldshift.engine.compare import CompareData, compare, load_compare_data
from fieldshift.engine.method import method
from fieldshift.engine.past_years import past_years
from fieldshift.engine.rules import PrivacyTexts, load_privacy_texts, load_prompt
from fieldshift.engine.schemas import FIRST_YEAR, LAST_YEAR, CompareRequest, HealthResponse, Land, Priority, Province
from fieldshift.paths import project_root

ROOT = project_root()
# No spec sets a limit. The largest valid CompareRequest (all 30 years, the longest land and priority values) is 257
# bytes as json.dumps writes it and 521 bytes indented by 4 spaces; 1024 bytes leaves about twice that. An explain
# request is that body with a plan, a part and a language, 752 bytes at most indented by 4 spaces
# (tests/test_explain.py).
MAX_BODY_BYTES = 1024
# A saved set may also carry a 9-digit price and cost (D-179) for each of the 17 crop keys of rules/rotations.yaml
# (D-180): 2262 bytes at most indented by 4 spaces (tests/test_accounts.py); 4096 bytes leaves about twice that.
SAVE_MAX_BODY_BYTES = 4096
BODY_TIMEOUT_SECONDS = 60  # nginx client_body_timeout default: https://nginx.org/en/docs/http/ngx_http_core_module.html#client_body_timeout
NO_STORE = {"cache-control": "no-store"}
# the built web app: vite's content-hashed chunks in assets/, and the public folders copied as they are (D-166)
BUILD_FOLDERS = ("assets/", "cesium/", "media/")
FILE_METHODS = ("GET", "HEAD")
ALL_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
REVALIDATE = {"cache-control": "no-cache"}  # index.html names the current chunks, so a browser asks again each time
IMMUTABLE = {"cache-control": "public, max-age=31536000, immutable"}  # a hashed name never changes its content
WEEK = {"cache-control": "public, max-age=604800"}  # performance audit 2026-11-15: media names carry no content hash
# H14 and D-167 in the browser: our own origin only, plus NASA GIBS tiles and the NASA Eyes frame of /dai-quan-sat,
# and Google's sign-in script, frame and style of /dang-nhap and /da-luu (UI-UX-SPEC §12c), as Google's guidance names
# them: https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid#content_security_policy
# Inline style attributes are React style props; data: and blob: images, blob: workers and eval are Cesium's.
GSI = "https://accounts.google.com/gsi/"
CSP = "; ".join(
    (
        "default-src 'self'",
        # D-170: Knockout, bundled in Cesium, runs (0,eval)('this') as the globe loads
        f"script-src 'self' 'unsafe-eval' {GSI}client",
        "img-src 'self' data: blob: https://gibs.earthdata.nasa.gov",
        f"connect-src 'self' https://gibs.earthdata.nasa.gov {GSI}",
        f"frame-src https://eyes.nasa.gov {GSI}",
        "worker-src 'self' blob:",
        f"style-src 'self' 'unsafe-inline' {GSI}style",
        "font-src 'self'",
        "frame-ancestors 'none'",
        # base-uri and form-action never fall back to default-src (https://www.w3.org/TR/CSP3/); no page uses a plugin
        "base-uri 'none'",
        "form-action 'self'",
        "object-src 'none'",
    )
)
SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    # Google's sign-in script needs the origin: "a Referrer-Policy of strict-origin-when-cross-origin is recommended"
    # (https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid); other sites get our origin only,
    # and the answers live after "#", which is never sent
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"content-security-policy", CSP.encode()),
    # one year (MDN's example); no includeSubDomains or preload, since the parent domain's other subdomains are not ours
    (b"strict-transport-security", b"max-age=31536000"),
]
ACCOUNT_THREADS = 4  # D-164: account work gets its own small worker limit, so it never holds the farmer routes
M = TypeVar("M", bound=BaseModel)
T = TypeVar("T")
LOG = logging.getLogger(__name__)


def _artifact_versions(artifacts_dir: Path) -> HealthResponse:
    out = {}
    for f in sorted(artifacts_dir.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if "schema_version" not in data:
            raise ValueError(f"{f.name}: no schema_version")
        out[f.name] = {"schema_version": data["schema_version"], "generated_at": data["generated_at"]}
    return HealthResponse(status="ok", artifacts=out)


def _json(model: BaseModel) -> bytes:
    return model.model_dump_json().encode()


def _respond(body: bytes) -> Response:
    return Response(body, media_type="application/json")


def _invalid(errors: list[dict[str, object]]) -> RequestValidationError:
    """Errors of a request body, located under "body" as FastAPI locates them."""
    return RequestValidationError([{**e, "loc": ("body", *e["loc"])} for e in errors])


async def _body(request: Request, model: type[M], limit: int = MAX_BODY_BYTES, context: object = None) -> M:
    """The body as a `model`, checked with `context` as its validation context; reading stops past `limit` bytes,
    whatever content-length says, after BODY_TIMEOUT_SECONDS, or when the client leaves (then nobody reads the 422,
    and nothing logs a traceback)."""
    body = b""
    try:
        async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                body += chunk
                if len(body) > limit:
                    raise _invalid([{"type": "too_long", "loc": (), "msg": f"body over {limit} bytes"}])
    except TimeoutError as err:
        raise _invalid([{"type": "timeout", "loc": (), "msg": f"body not sent in {BODY_TIMEOUT_SECONDS} s"}]) from err
    except ClientDisconnect as err:
        raise _invalid([{"type": "incomplete", "loc": (), "msg": "client left before the body ended"}]) from err
    try:
        return model.model_validate_json(body, context=context)
    except ValidationError as err:
        raise _invalid(err.errors()) from err


async def _unprocessable(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Every 422 in FastAPI's shape with type, loc and msg only, so no route echoes the input back; an unknown key is
    located at the object that holds it, since its name is the client's input."""
    detail = [
        {"type": e["type"], "loc": e["loc"][:-1] if e["type"] == "extra_forbidden" else e["loc"], "msg": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse({"detail": detail}, status_code=422)


# The app's colours and UI font stack (frontend/src/styles/tokens.css): night over the field by default, the light
# theme when the phone asks for it. The app's font files have build-hashed names, so the system fonts apply; headings
# use them too, since the display stack's Georgia fallback breaks Vietnamese accents.
_PRIVACY_STYLE = (
    ":root{color-scheme:dark;--bg:#0b1a12;--fg:#f6f4ec;--fg-2:#dfe5d9;--line:rgba(244,242,234,.12);--link:#e8b94e}"
    "@media (prefers-color-scheme: light){:root{color-scheme:light;--bg:#f1f3ee;--fg:#0f1511;--fg-2:#2f3a32;"
    "--line:rgba(15,21,17,.1);--link:#19331f}}"
    "body{margin:0;background:var(--bg);color:var(--fg-2);font:17px/1.6 'Be Vietnam Pro',system-ui,-apple-system,"
    "'Segoe UI',Roboto,'Noto Sans',Arial,sans-serif}"
    "main{max-width:40rem;margin:0 auto;padding:8px 16px 48px}"
    "nav{display:flex;flex-wrap:wrap;column-gap:24px;border-bottom:1px solid var(--line)}"
    "a{color:var(--link);text-underline-offset:.22em;display:inline-flex;align-items:center;min-height:44px}"
    "h1,h2{color:var(--fg);line-height:1.25;margin:24px 0 8px}"
    "section+section{border-top:1px solid var(--line);margin-top:32px}"
)


def _privacy_page(texts: PrivacyTexts) -> bytes:
    """The privacy notice as one page in both languages, with no script or third-party resource (H14)."""
    parts = [
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(texts.title['vi'])}</title><style>{_PRIVACY_STYLE}</style></head><body><main>",
        f'<nav><a href="/" lang="vi">{html.escape(texts.back["vi"])}</a>',
        f'<a href="/#/home" lang="en">{html.escape(texts.back["en"])}</a></nav>',
    ]
    for lang, heading in (("vi", "h1"), ("en", "h2")):
        parts.append(f'<section lang="{lang}"><{heading}>{html.escape(texts.title[lang])}</{heading}>')
        parts += [f"<p>{html.escape(p[lang])}</p>" for p in texts.paragraphs]
        parts.append("</section>")
    parts.append("</main></body></html>")
    return "".join(parts).encode()


async def _internal_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


def _add_privacy_routes(app: FastAPI, page: bytes) -> None:
    """The notice at the path registered with Google, and /privacy as a permanent redirect to it (D-164)."""

    @app.get("/quyen-rieng-tu")
    def privacy_route() -> Response:
        return HTMLResponse(page)

    @app.get("/privacy")
    def privacy_redirect() -> Response:
        return RedirectResponse("/quyen-rieng-tu", status_code=308)


def _not_signed_in() -> HTTPException:
    return HTTPException(401, "not signed in", headers={"WWW-Authenticate": "Bearer"})  # RFC 6750 §3


def _bearer(request: Request) -> str:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _not_signed_in()
    return token


async def _account_work(request: Request, work: Callable[..., T], *args: object) -> T:
    """`work` on the account worker threads, never the farmer routes' ones: 401 without a valid Google token, 409 when
    the saved sets are full, 503 when Google's keys cannot be fetched or the database does not answer."""
    try:
        return await anyio.to_thread.run_sync(work, *args, limiter=request.app.state.account_limiter)
    except NotSignedInError as err:
        raise _not_signed_in() from err
    except SavedSetsFullError as err:
        raise HTTPException(409, "saved sets are full") from err  # D-165: the page shows "full, delete one first"
    except GoogleUnreachableError as err:
        raise HTTPException(503, "google sign-in check is not reachable") from err
    except DatabaseDownError as err:
        raise HTTPException(503, "sign-in is not available") from err


def _private(model: BaseModel, status_code: int = 200) -> Response:
    # RFC 6749 §5.1: answers about an account are never stored by a cache
    return Response(_json(model), status_code=status_code, media_type="application/json", headers=NO_STORE)


async def _service(request: Request) -> Accounts:
    """The sign-in service; 503 while sign-in is off (UI-UX-SPEC §12c: every farmer route works without it)."""
    accounts = request.app.state.accounts
    if accounts is None:
        raise HTTPException(503, "sign-in is not available")
    return accounts


Service = Annotated[Accounts, Depends(_service)]


async def _google_id(request: Request, service: Service) -> str:
    return await _account_work(request, service.google_id, _bearer(request))


GoogleId = Annotated[str, Depends(_google_id)]


async def _signed_in(request: Request, service: Service, sub: GoogleId) -> int:
    return await _account_work(request, service.account, sub)


AccountId = Annotated[int, Depends(_signed_in)]
SetId = Annotated[int, PathParam(ge=1, le=BIGINT_MAX)]
accounts_router = APIRouter(prefix="/api/account")


@accounts_router.get("/config")
async def config_route(request: Request) -> Response:
    accounts = request.app.state.accounts
    client_id = accounts.client_id if accounts else None
    return _respond(_json(SignInConfig(available=accounts is not None, client_id=client_id)))


@accounts_router.post("/sign-in")
async def sign_in_route(request: Request, service: Service, sub: GoogleId) -> Response:
    await _account_work(request, service.sign_in, sub)
    return Response(status_code=204, headers=NO_STORE)


@accounts_router.get("/saved")
async def saved_route(request: Request, service: Service, account: AccountId) -> Response:
    return _private(await _account_work(request, service.saved, account))


@accounts_router.post("/saved")
async def save_route(request: Request, service: Service, sub: GoogleId) -> Response:
    answers = await _body(request, SavedAnswers, SAVE_MAX_BODY_BYTES, service.crop_keys)
    return _private(await _account_work(request, service.save, sub, answers), 201)


@accounts_router.delete("/saved/{set_id}")
async def delete_set_route(request: Request, set_id: SetId, service: Service, account: AccountId) -> Response:
    if not await _account_work(request, service.delete, account, set_id):
        raise HTTPException(404, "Not Found")  # also for another account's set: its existence is not revealed
    return Response(status_code=204)


@accounts_router.delete("")
async def delete_account_route(request: Request, service: Service, account: AccountId) -> Response:
    await _account_work(request, service.delete_account, account)
    return Response(status_code=204)


async def _bad_gateway(_: Request, exc: ExplainError) -> JSONResponse:
    LOG.warning("%s", exc)  # one line: exception class, status code, stop reason and request id only
    return JSONResponse({"detail": "Bad Gateway"}, status_code=502)


def _too_many() -> JSONResponse:
    """The shared cap of model calls is full (caps.py): a fixed detail that echoes nothing."""
    return JSONResponse({"detail": TOO_MANY}, status_code=429)


async def _explain(
    request: Request,
    compare_data: CompareData,
    claude: Anthropic | None,
    template: str,
    slots: anyio.CapacityLimiter,
    threads: anyio.CapacityLimiter,
) -> Response:
    """A slot is taken without waiting (run_sync yields before it takes its limiter, so a burst would queue); the
    compare and the call run on a second limiter of the same size, since the task holding a slot cannot borrow it."""
    if claude is None:
        return JSONResponse({"detail": "Service Unavailable"}, status_code=503)
    body = await _body(request, ExplainRequest)
    try:
        slots.acquire_nowait()
    except anyio.WouldBlock:
        return JSONResponse({"detail": "Service Unavailable"}, status_code=503)
    try:
        if not request.app.state.model_calls.take(client_of(request), "explain"):
            return _too_many()
        answer = await anyio.to_thread.run_sync(compare, body.answers, compare_data, limiter=threads)
        reply = await anyio.to_thread.run_sync(
            explain, shown_text(body, answer), body.lang, claude, template, limiter=threads
        )
    finally:
        slots.release()
    return _respond(_json(reply))


async def _copilot(
    request: Request,
    corpus: Corpus | None,
    claude: Anthropic | None,
    slots: anyio.CapacityLimiter,
    threads: anyio.CapacityLimiter,
) -> Response:
    """As _explain: 503 while off or while every slot is taken (without waiting), the work on its own limiter."""
    if corpus is None:
        return JSONResponse({"detail": "Service Unavailable"}, status_code=503)
    body = await _body(request, CopilotRequest)
    try:
        slots.acquire_nowait()
    except anyio.WouldBlock:
        return JSONResponse({"detail": "Service Unavailable"}, status_code=503)
    try:
        caps, client = request.app.state.model_calls, client_of(request)
        charge = functools.partial(caps.take, client, "copilot")
        reply = await anyio.to_thread.run_sync(copilot_answer, body, corpus, claude, charge, limiter=threads)
    finally:
        slots.release()
    return _respond(_json(reply))


def _health_body(health: HealthResponse, corpus: Corpus | None, claude: Anthropic | None, explain_on: bool) -> bytes:
    """The health answer; it says whether "explain simply" is on, and while the copilot is on it names its engine,
    which member B's page reads to call it."""
    body = {**health.model_dump(mode="json"), "explain": explain_on}
    if corpus is not None:
        body["copilot"] = {"engine": "deterministic" if claude is None else "claude", "configured": claude is not None}
    return json.dumps(body).encode()


def _read_every_year_row(compare_data: CompareData) -> None:
    """Compare once with every year, so a missing year row stops the start, not a farmer's request."""
    every_year = list(range(FIRST_YEAR, LAST_YEAR + 1))
    for province in get_args(Province):  # land and priority change nothing (UI-UX-SPEC T3): this reads every year row
        request = CompareRequest(
            province=province, land=get_args(Land)[0], years=every_year, priority=get_args(Priority)[0]
        )
        compare(request, compare_data)


def _add_frontend(app: FastAPI, frontend: Path) -> None:
    """The built web app (D-166): each file of the build at its own path, index.html for any other path outside /api
    (the app routes in the URL fragment, so deep links work). The file list is fixed at start, so no request can reach
    a file outside the build. A missing file is 404, never index.html: a tab opened before a deploy that asks for an old
    chunk must fail as a missing script, not run HTML. Every method reaches this route, so an unknown /api path is a
    JSON 404 whatever the method; the files answer GET and HEAD only."""
    root = frontend.resolve()
    index = root / "index.html"
    files = {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}

    @app.api_route("/{path:path}", methods=list(ALL_METHODS), include_in_schema=False)
    def frontend_route(request: Request, path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        if request.method not in FILE_METHODS:
            raise HTTPException(405, "Method Not Allowed", headers={"Allow": ", ".join(FILE_METHODS)})
        file = files.get(path)
        if file is None and (PurePosixPath(path).suffix or path.startswith(BUILD_FOLDERS)):
            raise HTTPException(404, "Not Found")
        if file is None or file == index:
            return FileResponse(index, headers=REVALIDATE)
        if path.startswith("assets/"):
            return FileResponse(file, headers=IMMUTABLE)
        return FileResponse(file, headers=WEEK if path.startswith("media/") else None)


class SecurityHeaders:
    """Adds the security headers to every response (security review 2026-11-14), as plain ASGI so request bodies
    still stream to the size and time limits of _body."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *SECURITY_HEADERS]
            await send(message)

        await self.app(scope, receive, send_with_headers)


def create_app(root: Path | str | None = None, frontend_dir: Path | str | None = None) -> FastAPI:
    base = Path(root) if root else ROOT
    frontend = Path(frontend_dir) if frontend_dir else base / "frontend" / "dist"
    past_body = {province: _json(past_years(province, base)) for province in get_args(Province)}
    method_body = _json(method(base))
    privacy_body = _privacy_page(load_privacy_texts(base))
    grid_figure = (base / "artifacts" / "figures" / "nghe_an_grid.svg").read_bytes()
    compare_data = load_compare_data(base)
    _read_every_year_row(compare_data)
    claude = claude_client(os.environ)
    explain_prompt = load_prompt(base, PROMPT, (PLACEHOLDER,))
    explain_slots, explain_threads = anyio.CapacityLimiter(EXPLAIN_LIMIT), anyio.CapacityLimiter(EXPLAIN_LIMIT)
    corpus = load_corpus(base) if copilot_on(os.environ) else None
    copilot_claude = copilot_client(os.environ)
    copilot_slots, copilot_threads = anyio.CapacityLimiter(COPILOT_LIMIT), anyio.CapacityLimiter(COPILOT_LIMIT)
    health_body = _health_body(_artifact_versions(base / "artifacts"), corpus, copilot_claude, claude is not None)

    app = FastAPI(title="Field Shift API", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_exception_handler(RequestValidationError, _unprocessable)
    app.add_exception_handler(ExplainError, _bad_gateway)  # also the copilot's CopilotError
    app.add_exception_handler(Exception, _internal_error)
    app.add_middleware(SecurityHeaders)

    @app.get("/api/health")
    def health_route() -> Response:
        return _respond(health_body)

    @app.get("/api/past-years")
    def past_years_route(province: Province) -> Response:
        return _respond(past_body[province])

    @app.post("/api/compare")
    async def compare_route(request: Request) -> Response:
        body = await _body(request, CompareRequest)
        return _respond(_json(await run_in_threadpool(compare, body, compare_data)))

    @app.post("/api/explain")
    async def explain_route(request: Request) -> Response:
        return await _explain(request, compare_data, claude, explain_prompt, explain_slots, explain_threads)

    @app.post("/api/copilot")
    async def copilot_route(request: Request) -> Response:
        return await _copilot(request, corpus, copilot_claude, copilot_slots, copilot_threads)

    @app.get("/api/method")
    def method_route() -> Response:
        return _respond(method_body)

    @app.get("/api/figures/nghe_an_grid.svg")
    def grid_figure_route() -> Response:
        return Response(grid_figure, media_type="image/svg+xml")

    _add_privacy_routes(app, privacy_body)
    app.state.accounts = accounts_from(os.environ, base)  # None while sign-in is off
    app.state.account_limiter = anyio.CapacityLimiter(ACCOUNT_THREADS)
    app.state.model_calls = ModelCallCaps()  # one cap for both model routes: they share the key (caps.py)
    app.include_router(accounts_router)

    if (frontend / "index.html").exists():
        _add_frontend(app, frontend)  # last, so every route above wins over the fallback
    return app


app = create_app()
