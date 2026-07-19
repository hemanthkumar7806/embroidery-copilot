FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && pip install --upgrade pip uv \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN uv venv && . .venv/bin/activate && uv pip install -e .

COPY . .
RUN mkdir -p /app/data/svgs

EXPOSE 8000
CMD ["/bin/sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
