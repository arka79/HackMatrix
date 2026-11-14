# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PIP_NO_CACHE_DIR=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,ro \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,ro \
    uv sync --frozen --no-dev --no-group dev

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv

WORKDIR /data

ENTRYPOINT ["cidoctor"]
CMD ["--help"]
