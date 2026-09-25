FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend application and its absolute root dependencies
COPY backend/app ./backend/app
COPY backend/__init__.py ./backend/__init__.py
COPY src/ ./src/
COPY artifacts/ ./artifacts/

ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
