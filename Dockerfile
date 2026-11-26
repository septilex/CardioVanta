FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LLM_ENABLED=false \
    CARDIOVANTA_MODEL_REGISTRY=/app/artifacts

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system cardiovanta \
    && useradd --system --gid cardiovanta --home-dir /app --shell /usr/sbin/nologin cardiovanta

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY cardiovanta_ml/ /tmp/cardiovanta_ml/
RUN python -m pip install --no-cache-dir --no-deps /tmp/cardiovanta_ml \
    && rm -rf /tmp/cardiovanta_ml /tmp/backend-requirements.txt

COPY backend/ /app/backend/
COPY configs/prediction_service.json /app/configs/prediction_service.json
COPY artifacts/models/cardiovanta-lr13/1.1.1/ /app/artifacts/models/cardiovanta-lr13/1.1.1/
COPY artifacts/model-1.1.1/ /app/artifacts/model-1.1.1/

USER cardiovanta
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
