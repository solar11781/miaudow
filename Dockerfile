# Backend service for Railway (D-25, D-76). Railway builds this Dockerfile when it finds one (docs.railway.com,
# config-as-code, read 2026-11-12). Region (Singapore, asia-southeast1-eqsg3a, D-92) and plan are set in the service
# settings. The server listens on $PORT when it is set, otherwise on 8000; point the Railway domain at that port.
# The web app (frontend/, D-166) is built in its own stage, so node never reaches the served image.
# Exact patch version and digest of node:22-slim, the node line CI uses (Docker Hub tag list, read 2026-11-14).
FROM node:22.23.5-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/index.html frontend/vite.config.ts frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json ./
COPY frontend/scripts ./scripts
COPY frontend/public ./public
COPY frontend/data ./data
COPY frontend/src ./src
# type checks and tests run in CI; the image only needs the bundle and the Cesium runtime files
RUN node scripts/copy_cesium.mjs && npx vite build

# Exact patch version and digest of python:3.13-slim (Docker Hub tag list, read 2026-11-14), so every build gets the same image.
FROM python:3.13.18-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
WORKDIR /app
# The locked packages are installed before the code is copied, so a code change does not reinstall them.
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
COPY rules ./rules
COPY artifacts ./artifacts
COPY --from=web /web/dist ./frontend/dist
# The installed package lives in site-packages; FIELDSHIFT_ROOT points it at /app/rules and /app/artifacts.
ENV PORT=8000 FIELDSHIFT_ROOT=/app
# The server runs without root rights. It only reads /app and site-packages, which stay root-owned and readable by all.
RUN useradd --system --no-create-home app
USER app
CMD ["sh", "-c", "uvicorn fieldshift.api.app:app --host 0.0.0.0 --port ${PORT} --no-access-log --no-server-header"]
