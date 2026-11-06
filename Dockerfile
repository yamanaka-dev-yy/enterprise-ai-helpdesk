FROM node:22-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/backend DATABASE_PATH=/app/data/helpdesk.sqlite3
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt \
    && useradd --uid 10001 --create-home helpdesk \
    && mkdir /app/data && chown helpdesk:helpdesk /app/data
COPY backend/helpdesk/ backend/helpdesk/
COPY --from=frontend /ui/out/ frontend/out/
USER helpdesk
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=4s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)" || exit 1
CMD ["sh", "-c", "uvicorn helpdesk.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
