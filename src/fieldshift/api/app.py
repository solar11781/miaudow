"""FastAPI service (D-25, D-76, D-80; UI-UX-SPEC §11; 04-TECH-DESIGN §3). Reads precomputed artifacts only (NFR-01).

It serves GET /api/past-years, POST /api/compare, GET /api/method and GET /api/health. The rules files and artifacts
are read once when the app is created, so a broken or missing file stops the start instead of failing a farmer's
request, and no request reads a file. POST /api/explain, the "explain simply" call to the Claude API (FR-15), is the
one stated exception to NFR-01: off by default, it answers 503 until it is turned on, and also while its own thread
limit is full (explain.py). Invalid input gets HTTP 422 (04-TECH-DESIGN §3); an unexpected error gets a generic 500
without internals. The same service serves the built frontend (frontend/dist) and returns index.html for
every frontend route, so browser history routing and deep links work (D-102).
Run: uvicorn fieldshift.api.app:app --no-access-log --no-server-header (D-92: no request log).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import TypeVar, get_args

import anyio
import anyio.to_thread
from anthropic import Anthropic
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from fieldshift.api.explain import (
    EXPLAIN_LIMIT,
    MAX_EXPLAIN_BODY_BYTES,
    ExplainError,
    ExplainRequest,
    claude_client,
    explain,
)
from fieldshift.engine.compare import CompareData, compare, load_compare_data
from fieldshift.engine.method import method
from fieldshift.engine.past_years import past_years
from fieldshift.engine.schemas import FIRST_YEAR, LAST_YEAR, CompareRequest, HealthResponse, Land, Priority, Province
from fieldshift.paths import project_root

ROOT = project_root()
FRONTEND_ROUTES = (
    "/",
    "/ruong",
    "/nam",
    "/uu-tien",
    "/phuong-an",
    "/khong-co-phuong-an",
    "/phuong-phap",
    "/gioi-thieu",
    "/nguon",
)  # UI-UX-SPEC §6; later-feature routes are added with them
# No spec sets a limit. The largest valid CompareRequest (all 30 years, the longest land and priority values) is 257
# bytes as json.dumps writes it and 521 bytes indented by 4 spaces; 1024 bytes leaves about twice that.
MAX_BODY_BYTES = 1024
BODY_TIMEOUT_SECONDS = 60  # nginx client_body_timeout default: https://nginx.org/en/docs/http/ngx_http_core_module.html#client_body_timeout
Body = TypeVar("Body", bound=BaseModel)
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


async def _read_body(request: Request, model: type[Body], limit: int) -> Body:
    """The body as `model`; reading stops past `limit` bytes, whatever content-length says, after
    BODY_TIMEOUT_SECONDS, or when the client leaves (then nobody reads the 422, and nothing logs a traceback)."""
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
        return model.model_validate_json(body)
    except ValidationError as err:
        raise _invalid(err.errors()) from err


async def _unprocessable(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Every 422 in FastAPI's shape with type, loc and msg only, so no route echoes the input back."""
    detail = [{"type": e["type"], "loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": detail}, status_code=422)


async def _internal_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


async def _bad_gateway(_: Request, exc: ExplainError) -> JSONResponse:
    LOG.warning("%s", exc)  # one line: exception class, status code, stop reason and request id only
    return JSONResponse({"detail": "Bad Gateway"}, status_code=502)


async def _explain(
    request: Request, claude: Anthropic | None, slots: anyio.CapacityLimiter, threads: anyio.CapacityLimiter
) -> Response:
    """A slot is taken without waiting (run_sync yields before it takes its limiter, so a burst would queue); the call
    runs on a second limiter of the same size, since the task holding a slot cannot borrow it again."""
    if claude is None:
        return JSONResponse({"detail": "Service Unavailable"}, status_code=503)
    body = await _read_body(request, ExplainRequest, MAX_EXPLAIN_BODY_BYTES)
    try:
        slots.acquire_nowait()
    except anyio.WouldBlock:
        return JSONResponse({"detail": "Service Unavailable"}, status_code=503)
    try:
        reply = await anyio.to_thread.run_sync(explain, body, claude, limiter=threads)
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


def create_app(root: Path | str | None = None, frontend_dir: Path | str | None = None) -> FastAPI:
    base = Path(root) if root else ROOT
    frontend = Path(frontend_dir) if frontend_dir else base / "frontend" / "dist"
    health_body = _json(_artifact_versions(base / "artifacts"))
    past_body = {province: _json(past_years(province, base)) for province in get_args(Province)}
    method_body = _json(method(base))
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
        body = await _read_body(request, CompareRequest, MAX_BODY_BYTES)
        return _respond(_json(await run_in_threadpool(compare, body, compare_data)))

    @app.post("/api/explain")
    async def explain_route(request: Request) -> Response:
        return await _explain(request, claude, explain_slots, explain_threads)

    @app.get("/api/method")
    def method_route() -> Response:
        return _respond(method_body)

    if (frontend / "index.html").exists():
        index = frontend / "index.html"
        for route in FRONTEND_ROUTES:
            app.add_api_route(route, lambda: FileResponse(index), methods=["GET"], include_in_schema=False)
        if (frontend / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")
    return app


app = create_app()
