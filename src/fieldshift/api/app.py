"""FastAPI service (D-25, D-76, D-80; UI-UX-SPEC §11; 04-TECH-DESIGN §3). Reads precomputed artifacts only (NFR-01).

It serves GET /api/past-years, POST /api/compare, GET /api/method, GET /api/health, the method page's grid figure
GET /api/figures/nghe_an_grid.svg (UI-UX-SPEC §11b item 4), the privacy notice of the optional sign-in at
/quyen-rieng-tu (UI-UX-SPEC §12c), and that sign-in under /api/account (accounts.py; 503 while it is off). The rules
files and artifacts are read once when the app is created, so a broken or missing file stops the start instead of
failing a farmer's request, and no request reads a file. POST /api/explain, the "explain simply" call to the Claude API
(FR-15), is the one stated exception to NFR-01: off by default, it answers 503 until it is turned on, and also while
its own thread limit is full (explain.py). Invalid input gets HTTP 422 (04-TECH-DESIGN §3); an unexpected error gets a
generic 500 without internals. The same service serves the built frontend (frontend/dist): every built file, and index.html
for any other path outside /api (D-102, D-166).
Run: uvicorn fieldshift.api.app:app --no-access-log --no-server-header (D-92: no request log).
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
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
from fieldshift.api.explain import EXPLAIN_LIMIT, ExplainError, ExplainRequest, claude_client, explain, shown_text
from fieldshift.engine.compare import CompareData, compare, load_compare_data
from fieldshift.engine.method import method
from fieldshift.engine.past_years import past_years
from fieldshift.engine.rules import PrivacyTexts, load_privacy_texts
from fieldshift.engine.schemas import FIRST_YEAR, LAST_YEAR, CompareRequest, HealthResponse, Land, Priority, Province
from fieldshift.paths import project_root

ROOT = project_root()
# No spec sets a limit. The largest valid CompareRequest (all 30 years, the longest land and priority values) is 257
# bytes as json.dumps writes it and 521 bytes indented by 4 spaces; 1024 bytes leaves about twice that. A saved set of
# answers is the same body without the province, so the same limit holds it; an explain request is that body with a
# plan, a part and a language, 752 bytes at most indented by 4 spaces (tests/test_explain.py).
MAX_BODY_BYTES = 1024
BODY_TIMEOUT_SECONDS = 60  # nginx client_body_timeout default: https://nginx.org/en/docs/http/ngx_http_core_module.html#client_body_timeout
NO_STORE = {"cache-control": "no-store"}
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


async def _body(request: Request, model: type[M]) -> M:
    """The body as a `model`; reading stops past MAX_BODY_BYTES, whatever content-length says, after
    BODY_TIMEOUT_SECONDS, or when the client leaves (then nobody reads the 422, and nothing logs a traceback)."""
    body = b""
    try:
        async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                body += chunk
                if len(body) > MAX_BODY_BYTES:
                    raise _invalid([{"type": "too_long", "loc": (), "msg": f"body over {MAX_BODY_BYTES} bytes"}])
    except TimeoutError as err:
        raise _invalid([{"type": "timeout", "loc": (), "msg": f"body not sent in {BODY_TIMEOUT_SECONDS} s"}]) from err
    except ClientDisconnect as err:
        raise _invalid([{"type": "incomplete", "loc": (), "msg": "client left before the body ended"}]) from err
    try:
        return model.model_validate_json(body)
    except ValidationError as err:
        raise _invalid(err.errors()) from err


async def _unprocessable(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Every 422 in FastAPI's shape with type, loc and msg only, so no route echoes the input back."""
    detail = [{"type": e["type"], "loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": detail}, status_code=422)


def _privacy_page(texts: PrivacyTexts) -> bytes:
    """The privacy notice as one page in both languages, with no script, style or third-party resource (H14)."""
    parts = [
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(texts.title['vi'])}</title></head><body><main>",
    ]
    for lang, heading in (("vi", "h1"), ("en", "h2")):
        parts.append(f'<section lang="{lang}"><{heading}>{html.escape(texts.title[lang])}</{heading}>')
        parts.append(f"<p><em>{html.escape(texts.draft_note[lang])}</em></p>")
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
    answers = await _body(request, SavedAnswers)
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


async def _explain(
    request: Request,
    compare_data: CompareData,
    claude: Anthropic | None,
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
        answer = await anyio.to_thread.run_sync(compare, body.answers, compare_data, limiter=threads)
        reply = await anyio.to_thread.run_sync(explain, shown_text(body, answer), body.lang, claude, limiter=threads)
    finally:
        slots.release()
    return _respond(_json(reply))


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
    a file outside the build; an unknown /api path never falls back and stays a JSON 404."""
    root = frontend.resolve()
    index = root / "index.html"
    files = {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_route(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        return FileResponse(files.get(path, index))


def create_app(root: Path | str | None = None, frontend_dir: Path | str | None = None) -> FastAPI:
    base = Path(root) if root else ROOT
    frontend = Path(frontend_dir) if frontend_dir else base / "frontend" / "dist"
    health_body = _json(_artifact_versions(base / "artifacts"))
    past_body = {province: _json(past_years(province, base)) for province in get_args(Province)}
    method_body = _json(method(base))
    privacy_body = _privacy_page(load_privacy_texts(base))
    grid_figure = (base / "artifacts" / "figures" / "nghe_an_grid.svg").read_bytes()
    compare_data = load_compare_data(base)
    _read_every_year_row(compare_data)
    claude = claude_client(os.environ)
    explain_slots, explain_threads = anyio.CapacityLimiter(EXPLAIN_LIMIT), anyio.CapacityLimiter(EXPLAIN_LIMIT)

    app = FastAPI(title="Field Shift API", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_exception_handler(RequestValidationError, _unprocessable)
    app.add_exception_handler(ExplainError, _bad_gateway)
    app.add_exception_handler(Exception, _internal_error)

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
        return await _explain(request, compare_data, claude, explain_slots, explain_threads)

    @app.get("/api/method")
    def method_route() -> Response:
        return _respond(method_body)

    @app.get("/api/figures/nghe_an_grid.svg")
    def grid_figure_route() -> Response:
        return Response(grid_figure, media_type="image/svg+xml")

    _add_privacy_routes(app, privacy_body)
    app.state.accounts = accounts_from(os.environ)  # None while sign-in is off
    app.state.account_limiter = anyio.CapacityLimiter(ACCOUNT_THREADS)
    app.include_router(accounts_router)

    if (frontend / "index.html").exists():
        _add_frontend(app, frontend)  # last, so every route above wins over the fallback
    return app


app = create_app()
