FROM python:3.11-slim

# Set working directory
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
  gcc \
  g++ \
  git \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY middleware/ ./middleware/
COPY database/ ./database/
COPY utils/ ./utils/
COPY frontend/ ./frontend/
COPY public/ ./public/
COPY .chainlit/ ./.chainlit/
COPY app.py .
COPY config.py .
COPY chainlit.md .
COPY constants.py .

# Environment variables that are NOT secrets can go here
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV CHAINLIT_HEADLESS=true

# Expose port
EXPOSE 8080
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "backend.server.api:app", "--host", "0.0.0.0", "--port", "8080"]