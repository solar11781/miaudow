# Backend service for Railway (D-25, D-76). Railway builds this Dockerfile when it finds one (docs.railway.com,
# config-as-code, read 2026-11-12). Region (Singapore, asia-southeast1-eqsg3a, D-92) and plan are set in the service
# settings. The server listens on $PORT when it is set, otherwise on 8000; point the Railway domain at that port.
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
# frontend/dist is copied here once the frontend build exists (UI-UX-SPEC §13).
# The installed package lives in site-packages; FIELDSHIFT_ROOT points it at /app/rules and /app/artifacts.
ENV PORT=8000 FIELDSHIFT_ROOT=/app
CMD ["sh", "-c", "uvicorn fieldshift.api.app:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
