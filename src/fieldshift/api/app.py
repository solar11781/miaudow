"""FastAPI backend skeleton (D-25, D-76, D-80; UI-UX-SPEC §11). Reads precomputed artifacts only (NFR-01).

Before the event this serves only /api/health over placeholder artifacts; the product endpoints (past-years, compare,
method) are written during the event. The same service serves the built frontend (frontend/dist) and returns
index.html for every frontend route, so browser history routing and deep links work (D-102).
Run: uvicorn fieldshift.api.app:app --no-access-log (D-92: no request log).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


def _artifact_versions(artifacts_dir: Path) -> dict:
    out = {}
    if artifacts_dir.is_dir():
        for f in sorted(artifacts_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            out[f.name] = {"schema_version": data["schema_version"], "generated_at": data["generated_at"]}
    return out


def create_app(artifacts_dir: Path | str | None = None, frontend_dir: Path | str | None = None) -> FastAPI:
    artifacts = Path(artifacts_dir) if artifacts_dir else ROOT / "artifacts"
    frontend = Path(frontend_dir) if frontend_dir else ROOT / "frontend" / "dist"
    app = FastAPI(title="Field Shift API", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "artifacts": _artifact_versions(artifacts)}

    if (frontend / "index.html").exists():
        index = frontend / "index.html"
        for route in FRONTEND_ROUTES:
            app.add_api_route(route, lambda: FileResponse(index), methods=["GET"], include_in_schema=False)
        if (frontend / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")
    return app


app = create_app(os.environ.get("FIELDSHIFT_ARTIFACTS"), os.environ.get("FIELDSHIFT_FRONTEND"))
