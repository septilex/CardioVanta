FROM python:3.12-slim-bookworm AS dependencies
WORKDIR /app
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt uvicorn==0.34.0

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 cardio
COPY --from=dependencies /install /usr/local
COPY --chown=cardio:cardio backend ./backend
COPY --chown=cardio:cardio cardiovanta_ml ./cardiovanta_ml
COPY --chown=cardio:cardio artifacts ./artifacts
COPY --chown=cardio:cardio configs ./configs
USER cardio
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
