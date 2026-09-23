# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies into the container's own environment (not a host .venv)
RUN uv sync --locked --no-dev --no-install-project

# Copy application source, migration files, and fixtures
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini ./
COPY fixtures/ fixtures/

# Install the project itself
RUN uv sync --locked --no-dev

# Create upload directory
RUN mkdir -p /app/uploads

CMD ["uv", "run", "uvicorn", "minibench.main:app", "--host", "0.0.0.0", "--port", "8000"]
