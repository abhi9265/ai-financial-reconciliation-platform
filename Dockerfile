FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir . \
    && python -m pip install --no-cache-dir --upgrade "setuptools>=78.1.1" "wheel>=0.46.2" "msgpack>=1.2.1" \
    && python -m pip uninstall -y setuptools wheel msgpack \
    && rm -rf /usr/local/lib/python3.11/site-packages/setuptools /usr/local/lib/python3.11/site-packages/setuptools-*.dist-info \
              /usr/local/lib/python3.11/site-packages/wheel /usr/local/lib/python3.11/site-packages/wheel-*.dist-info \
              /usr/local/lib/python3.11/site-packages/msgpack /usr/local/lib/python3.11/site-packages/msgpack-*.dist-info \
    && python -m pip check \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data/objects /tmp/reconciliation \
    && chown -R appuser:appuser /app /tmp/reconciliation

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready')"

CMD ["uvicorn", "reconciliation_platform.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
