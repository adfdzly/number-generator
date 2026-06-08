# Production image for the Flask web front-end (served by gunicorn).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY web/requirements.txt ./web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt

# Shared core modules (used by both desktop and web) + the web package.
COPY generator.py utils.py ./
COPY web ./web

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# 3 workers is a sensible default for a small app; tune to your CPU.
CMD ["gunicorn", "--chdir", "web", "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--timeout", "60", "app:app"]
