# syntax=docker/dockerfile:1
FROM python:3.14.8-slim

# uv, copied from its official image
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

# deno: JavaScript runtime yt-dlp uses to extract full YouTube formats
# (without it, extraction is deprecated and some formats are missing).
COPY --from=denoland/deno:bin-2.9.7 /deno /usr/local/bin/deno

WORKDIR /app

# ffmpeg: yt-dlp needs it to merge/remux downloaded streams.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Runs as whatever uid compose's `user:` sets, which has no passwd entry, so
# HOME must point somewhere any uid can write (yt-dlp and deno cache there).
ENV PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

# Install dependencies first for layer caching. `package = false`, so this
# installs the locked deps only, not the project itself.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY src ./src

EXPOSE 8000

# Default command; compose services (api, future worker) override it.
CMD ["uvicorn", "localreel.entrypoints.api.main:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
