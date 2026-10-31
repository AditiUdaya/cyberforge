# API container: FastAPI on uvicorn, SQLite on a mounted /data volume. Build from the repo root:
#   docker build -f infra/Dockerfile -t scam-map-api .
# The Streamlit web app is a separate service with its own image (DECISIONS D55, task A0).
# Owner: A. Filled in by: B0 (image); A0 adapts it for the chosen host.

FROM ghcr.io/astral-sh/uv:0.12.7 AS uv

FROM python:3.12.10-slim
COPY --from=uv /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    SCAM_MAP_DB_PATH=/data/scam_map.sqlite \
    PORT=8000

WORKDIR /srv/api
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api/app ./app
COPY api/migrations ./migrations
COPY shared /srv/shared

RUN useradd --system --uid 10001 app \
    && mkdir -p /data \
    && chown app /data
USER app
VOLUME ["/data"]
EXPOSE 8000

# Access logs off: our own log lines carry route, status and timing only (ARCHITECTURE "Privacy").
CMD ["sh", "-c", "exec /opt/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\" --no-access-log --proxy-headers"]
