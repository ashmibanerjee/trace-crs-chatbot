FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    gcc g++ git curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source — credentials and secrets are intentionally excluded
# via .dockerignore; they must be injected at runtime via environment variables.
COPY backend/   ./backend/
COPY middleware/ ./middleware/
COPY database/  ./database/
COPY utils/     ./utils/
COPY frontend/  ./frontend/
COPY public/    ./public/
COPY .chainlit/ ./.chainlit/
COPY app.py     .
COPY config.py  .
COPY chainlit.md .
COPY constants.py .

# Non-secret runtime configuration
# PORT=7860 matches HF Spaces requirements; override to 8080 for Cloud Run.
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV CHAINLIT_HEADLESS=true

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use shell form so $PORT is expanded at container start time
CMD uvicorn backend.server.api:app --host 0.0.0.0 --port $PORT
