# syntax=docker/dockerfile:1
# One image runs the API and the download worker together (docker/start.sh).
# Every base image is pinned to a digest, so a build always gets the same bytes.

# Build: install the locked dependencies into /app/.venv. uv and its cache
# stay in this stage; the final image only gets the environment.
FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 /uv /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_LINK_MODE=copy uv sync --frozen --no-dev

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

# yt-dlp needs a JavaScript runtime to read YouTube's full list of formats.
COPY --from=denoland/deno:bin-2.9.8@sha256:b507583d3c68ba69f3ed2ce5969ae5b8b70f43421c781279c7aea06435263543 /deno /usr/local/bin/deno

# ffmpeg: yt-dlp merges a separate video and audio stream with it, which is
# how YouTube serves anything above 360p.
# tini: PID 1, which hands a stop signal to start.sh and reaps what a
# stopped download leaves behind.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/.venv ./.venv

# The container runs as whatever uid owns the downloads folder, which has no
# home directory, so HOME points where any uid can write (yt-dlp and deno
# cache there).
ENV PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/cache

# alembic reads its settings from pyproject.toml.
COPY pyproject.toml ./
COPY src ./src
COPY docker/start.sh ./

EXPOSE 8000

ENTRYPOINT ["tini", "--"]
CMD ["./start.sh"]
