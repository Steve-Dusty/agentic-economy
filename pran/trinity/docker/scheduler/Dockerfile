# Trinity Scheduler Service Dockerfile
# Standalone scheduler for agent task execution

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY docker/scheduler/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy scheduler source code
COPY src/scheduler /app/scheduler

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default environment variables
ENV DATABASE_PATH=/data/trinity.db
ENV REDIS_URL=redis://redis:6379
ENV HEALTH_PORT=8001
ENV LOG_LEVEL=INFO

# Run the scheduler
CMD ["python", "-m", "scheduler.main"]
