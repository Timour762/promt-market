FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS backend-build
WORKDIR /build/backend
COPY backend/requirements.lock.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock.txt

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates libstdc++6 libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
COPY --from=backend-build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=http://127.0.0.1:8107 \
    HOSTNAME=0.0.0.0 \
    PORT=10000
WORKDIR /app
COPY --chown=appuser:appuser backend/app /app/backend/app
COPY --chown=appuser:appuser backend/migrations /app/backend/migrations
COPY --chown=appuser:appuser backend/alembic.ini /app/backend/alembic.ini
COPY --from=frontend-build --chown=appuser:appuser /build/frontend/.next-release/standalone /app/web
COPY --from=frontend-build --chown=appuser:appuser /build/frontend/.next-release/static /app/web/.next-release/static
COPY --from=frontend-build --chown=appuser:appuser /build/frontend/public /app/web/public
COPY --chown=appuser:appuser deploy/render/supervisor.py /app/supervisor.py
USER appuser
EXPOSE 10000
STOPSIGNAL SIGTERM
CMD ["python", "/app/supervisor.py"]
