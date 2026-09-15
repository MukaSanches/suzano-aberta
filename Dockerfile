FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SUZANO_API_DATABASE=/data/suzano-aberta.sqlite3 \
    SUZANO_API_AUTO_SYNC=true \
    SUZANO_API_SYNC_INTERVAL_SECONDS=3600

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir . \
    && groupadd --gid 10001 suzano \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin suzano \
    && mkdir -p /data \
    && chown -R 10001:10001 /data /app

USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).read()" || exit 1

CMD ["uvicorn", "suzano_aberta.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
