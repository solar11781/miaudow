"""FastAPI service of MIAUDOW 2.0 (docs/07-ARCHITECTURE-AND-CONTRACTS.md).

Run from api/:  ..\\.venv\\Scripts\\uvicorn main:app

The canonical files are loaded once at startup; a missing file gives a clear 503 that names the build command.
POST /api/copilot calls miaudow_api.copilot.answer behind a small in-memory rate limiter (per client IP, configured by
MIAUDOW_COPILOT_RATE as "requests/seconds", default 20/600).
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import canonical, climate, copilot, decision, evidence, voice
from .contracts import CompareRequest, CopilotRequest, CopilotResponse, DecisionResult, MetricRecord, SearchResult
from .paths import BUILD_COMMAND

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_COPILOT_RATE = "20/600"


class RateLimiter:
    """Sliding-window limit per key (client IP), in memory: fine for one process, reset on restart."""

    def __init__(self, limit: int, window_s: float, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window_s, clock
        self.hits: dict[str, deque] = {}
        self.lock = threading.Lock()

    @classmethod
    def from_env(cls) -> RateLimiter:
        raw = os.getenv("MIAUDOW_COPILOT_RATE", DEFAULT_COPILOT_RATE)
        try:
            n, s = raw.split("/")
            limit, window = int(n), float(s)
            if limit < 1 or window <= 0:
                raise ValueError(raw)
        except ValueError as e:
            raise ValueError(f"MIAUDOW_COPILOT_RATE must look like 20/600 (requests/seconds), got {raw!r}") from e
        return cls(limit, window)

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self.lock:
            q = self.hits.setdefault(key, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1200)
    k: int = Field(default=5, ge=1, le=20)


def cors_origins() -> list[str]:
    return [x.strip() for x in os.getenv("MIAUDOW_CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if x.strip()]


def _warm() -> None:
    """Load every canonical file and the evidence index once; a missing file is reported by /api/health and 503s."""
    canonical.clear()
    evidence.load_passages.cache_clear()
    evidence.default_index.cache_clear()
    if canonical.missing_files():
        return
    for name in canonical.FILES:
        canonical.load(name)
    evidence.default_index()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        _warm()
        yield

    app = FastAPI(title="MIAUDOW Evidence API", version="2.0.0", lifespan=lifespan)
    limiter = RateLimiter.from_env()
    app.state.copilot_limiter = limiter
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(canonical.CanonicalMissing)
    async def _missing(_: Request, exc: canonical.CanonicalMissing):
        return JSONResponse(status_code=503, content={"detail": str(exc), "build_command": BUILD_COMMAND})

    @app.exception_handler(climate.ClimateInputError)
    async def _bad_climate(_: Request, exc: climate.ClimateInputError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/api/health")
    def health() -> dict:
        missing = canonical.missing_files()
        datasets = []
        if "catalog.json" not in missing:
            datasets = [
                {"dataset_id": d["dataset_id"], "ingestion_status": d["ingestion_status"]}
                for d in canonical.load("catalog.json")["datasets"]
            ]
        ready = "ok" if not missing else "canonical_missing"
        claude = bool(os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_MODEL"))  # never the values
        return {
            "status": "ok" if not missing else "degraded",
            "canonical": {"missing_files": missing, "build_command": BUILD_COMMAND if missing else None},
            "cores": {
                "climate": ready,
                "evidence": ready,
                "decision": ready,
                "copilot": {
                    "status": "configured" if claude else "not_configured",
                    "engine": "claude" if claude else "deterministic",
                },
                "voice_benchmark": voice.benchmark_status()["status"],
            },
            "datasets": datasets,
        }

    @app.get("/api/catalog")
    def get_catalog() -> dict:
        return climate.catalog()

    @app.get("/api/climate/year/{year}", response_model=list[MetricRecord])
    def climate_year(year: int, cell: str = Query(climate.FARMLAND)) -> list[MetricRecord]:
        return climate.year_summary(year, cell)

    @app.get("/api/climate/monthly", response_model=list[MetricRecord])
    def climate_monthly(year: int = Query(...), cell: str = Query(climate.FARMLAND)) -> list[MetricRecord]:
        return climate.monthly(year, cell)

    @app.get("/api/climate/live")
    async def climate_live(
        lat: float = Query(18.97, ge=-90, le=90),
        lon: float = Query(105.35, ge=-180, le=180),
        year: int = Query(2024, ge=1981, le=2100),
    ) -> dict:
        try:
            return await climate.live_power(lat, lon, year)
        except climate.PowerUnavailable as e:
            raise HTTPException(status_code=503, detail=f"{e}") from e

    @app.post("/api/evidence/search", response_model=SearchResult)
    def evidence_search(payload: SearchRequest) -> SearchResult:
        return evidence.search(payload.query, payload.k)

    @app.get("/api/decision/plans")
    def decision_plans() -> list[dict]:
        return decision.plans()

    @app.post("/api/decision/compare", response_model=DecisionResult)
    def decision_compare(payload: CompareRequest) -> DecisionResult:
        try:
            return decision.compare(payload)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.post("/api/copilot", response_model=CopilotResponse)
    def copilot_route(payload: CopilotRequest, request: Request) -> CopilotResponse:
        client = request.client.host if request.client else "unknown"
        if not app.state.copilot_limiter.allow(client):
            raise HTTPException(
                status_code=429,
                detail="Bạn đã hỏi quá nhiều lần, hãy thử lại sau ít phút. / Too many questions; please try again in a "
                "few minutes.",
            )
        return copilot.answer(payload)

    @app.get("/api/voice/benchmark")
    def voice_benchmark() -> dict:
        return voice.benchmark_status()

    return app


app = create_app()
