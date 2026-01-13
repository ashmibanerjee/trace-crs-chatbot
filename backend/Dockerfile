# Use Python 3.11 slim image for smaller size
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

# Copy requirements file from parent directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy necessary application files
COPY backend/ ./backend/
COPY middleware/ ./middleware/
COPY database/ ./database/
COPY utils/ ./utils/
COPY config.py .

# Note: For credentials, use one of these options:
# 1. Cloud Run's default service account (recommended for GCP)
# 2. Mount secrets via Cloud Run secret manager
# 3. For local testing: docker run -v ./credentials.json:/app/credentials.json

# Set environment variables for Cloud Run
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the FastAPI application using uvicorn
CMD ["python", "-m", "uvicorn", "backend.server.api:app", "--host", "0.0.0.0", "--port", "8080"]

