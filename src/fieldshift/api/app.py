"""FastAPI service (D-25, D-76, D-80; UI-UX-SPEC §11; 04-TECH-DESIGN §3). Reads precomputed artifacts only (NFR-01).

It serves GET /api/past-years, POST /api/compare, GET /api/method and GET /api/health. The rules files and artifacts
are read once when the app is created, so a broken or missing file stops the start instead of failing a farmer's
request, and no request reads a file. Invalid input gets HTTP 422 (04-TECH-DESIGN §3); an unexpected error gets a
generic 500 without internals. The same service serves the built frontend (frontend/dist) and returns index.html for
every frontend route, so browser history routing and deep links work (D-102).
Run: uvicorn fieldshift.api.app:app --no-access-log (D-92: no request log).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import get_args

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from fieldshift.engine.compare import compare, load_compare_data
from fieldshift.engine.method import method
from fieldshift.engine.past_years import past_years
from fieldshift.engine.schemas import CompareRequest, HealthResponse, Province
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
    """Errors of the compare body, located under "body" as FastAPI locates them."""
    return RequestValidationError([{**e, "loc": ("body", *e["loc"])} for e in errors])


async def _compare_request(request: Request) -> CompareRequest:
    """The body as a CompareRequest; reading stops past MAX_BODY_BYTES, whatever content-length says, after
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
        return CompareRequest.model_validate_json(body)
    except ValidationError as err:
        raise _invalid(err.errors()) from err


async def _unprocessable(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Every 422 in FastAPI's shape with type, loc and msg only, so no route echoes the input back."""
    detail = [{"type": e["type"], "loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": detail}, status_code=422)


async def _internal_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


def create_app(root: Path | str | None = None, frontend_dir: Path | str | None = None) -> FastAPI:
    base = Path(root) if root else ROOT
    frontend = Path(frontend_dir) if frontend_dir else base / "frontend" / "dist"
    health_body = _json(_artifact_versions(base / "artifacts"))
    past_body = {province: _json(past_years(province, base)) for province in get_args(Province)}
    method_body = _json(method(base))
    compare_data = load_compare_data(base)

    app = FastAPI(title="Field Shift API", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_exception_handler(RequestValidationError, _unprocessable)
    app.add_exception_handler(Exception, _internal_error)

    @app.get("/api/health")
    def health_route() -> Response:
        return _respond(health_body)

    @app.get("/api/past-years")
    def past_years_route(province: Province) -> Response:
        return _respond(past_body[province])

    @app.post("/api/compare")
    async def compare_route(request: Request) -> Response:
        body = await _compare_request(request)
        return _respond(_json(await run_in_threadpool(compare, body, compare_data)))

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
