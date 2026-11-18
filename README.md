# localreel

[![CI](https://github.com/sh3b/localreel/actions/workflows/ci.yml/badge.svg)](https://github.com/sh3b/localreel/actions/workflows/ci.yml)
[![License: GPL-3.0](https://img.shields.io/github/license/sh3b/localreel)](LICENSE)
![Python 3.14](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Svelte 5](https://img.shields.io/badge/svelte-5-FF3E00?logo=svelte&logoColor=white)
![PostgreSQL 18](https://img.shields.io/badge/postgresql-18-4169E1?logo=postgresql&logoColor=white)
![Docker Compose](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)

A self-hosted library for short videos. Paste links from YouTube, TikTok or
Facebook; localreel downloads them and keeps them on your own disk, and you
watch them in a feed or browse them in a library.

## How it works

```
browser ──> nginx ─┬─ /         the UI (static files)
                   ├─ /media/   the videos, from DOWNLOADS_DIR
                   └─ /api/ ──> API (FastAPI) ──┐
                                                ├──> Postgres
                 worker (yt-dlp, ffmpeg) ───────┘
```

One container runs nginx, the API and a single download worker; Postgres runs
next to it. A new link is saved as waiting. The worker takes the oldest one,
downloads it with yt-dlp outside any database transaction, and marks it ready
or failed. The `videos` table is the queue: there is no Redis and no job
table. A download cut off by a crash or a restart goes back in line when the
worker starts.

## Install

You need Docker with Compose v2, on amd64 or arm64.

```bash
git clone https://github.com/sh3b/localreel.git && cd localreel
cp .env.example .env
```

Edit `.env`:

- `DB_PASSWORD`: pick one, letters and digits only.
- `PUID` and `PGID`: your user and group, from `id -u` and `id -g`.
- `DOWNLOADS_DIR`: where the videos go. Create it before the first start, as
  that user; otherwise Docker creates it owned by root, and localreel can't
  write to it.

```bash
mkdir -p data/downloads    # or the DOWNLOADS_DIR you set
docker compose up -d --build
```

Open `http://<your server>:8080`. Port 8080 taken? Set another one as
`HTTP_PORT` in `.env`.

## Update

```bash
git pull
docker compose up -d --build
```

The database is migrated on start.

## Your data

- **The videos** are files in `DOWNLOADS_DIR`.
- **The library** (each video's link, status and details) is in the `pgdata`
  Docker volume. `docker compose down` keeps it; `docker compose down -v`
  deletes it.

## Before you run it

- **There is no login.** Anyone who can reach the port can add, watch and
  remove videos. Run it on your home network, or reach it through a VPN; don't
  expose it to the internet.
- **The port listens on every network interface,** and Docker's published
  ports bypass host firewalls such as ufw.

## Development

Python with [uv](https://docs.astral.sh/uv/), Node, and Docker for Postgres.
Copy `.env.example` to `.env`; `make` uses it too. Postgres runs on
`localhost:5432`; for another host or port, add `DB_HOST` or `DB_PORT` to
`.env`.

```bash
make install fe-install   # once
make db                   # Postgres in Docker
make migrate
make api                  # http://localhost:8000/api/docs
make worker
make fe-dev               # the UI, http://localhost:5173
```

Checks: `make lint typecheck test` for the backend, `make fe-check fe-test`
for the UI; CI runs them on every push and pull request, plus an install with
compose.

## License

[GPL-3.0-or-later](LICENSE).
