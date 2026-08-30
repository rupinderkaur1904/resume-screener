# ---- Backend Dockerfile ----
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Don't write .pyc files, and flush stdout immediately so `docker logs` is real-time
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# build-essential + curl needed to compile some wheels and for the HEALTHCHECK below
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# These match the volumes mounted in docker-compose.yml
RUN mkdir -p /app/uploads /app/model_cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]