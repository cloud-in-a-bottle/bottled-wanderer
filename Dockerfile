FROM python:3.12-slim

# git is needed to install the health-data-service spec (a git dependency).
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies (source is copied first so the project itself
# builds during `uv sync`).
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "--frozen", "--no-dev", "hypercorn", "wanderer.app:app", "--bind", "0.0.0.0:8080"]
