# Backend service for Railway (D-25, D-76). Railway builds this Dockerfile when it finds one (docs.railway.com,
# config-as-code, read 2026-11-12). Region (Singapore, asia-southeast1-eqsg3a, D-92) and plan are set in the service
# settings. The server listens on $PORT when it is set, otherwise on 8000; point the Railway domain at that port.
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY src ./src
COPY rules ./rules
COPY artifacts ./artifacts
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps .
# frontend/dist is copied here once the frontend build exists (UI-UX-SPEC §13).
# The installed package lives in site-packages; FIELDSHIFT_ROOT points it at /app/rules and /app/artifacts.
ENV PORT=8000 FIELDSHIFT_ROOT=/app
CMD ["sh", "-c", "uvicorn fieldshift.api.app:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
