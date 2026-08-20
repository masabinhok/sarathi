# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies resolve from the lockfile alone, so editing src/ does not re-resolve them.
# README.md is listed as the project readme, so the build backend needs it present.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

COPY docs ./docs
COPY docker/api-entrypoint.sh /usr/local/bin/api-entrypoint
RUN chmod +x /usr/local/bin/api-entrypoint

# Runs as uid 1000 -- the usual first Linux account -- so admin uploads landing in the
# bind-mounted docs/ stay editable on the host instead of turning up root-owned.
RUN mkdir -p /app/.chroma /app/.cache \
    && useradd --uid 1000 --create-home app \
    && chown -R 1000:1000 /app
USER 1000:1000

EXPOSE 8000
ENTRYPOINT ["api-entrypoint"]
CMD ["uvicorn", "ioe.api:app", "--host", "0.0.0.0", "--port", "8000"]
