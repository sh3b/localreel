# localreel

A self-hosted library for short videos. Give it a link, and it downloads the
video, converts it to something every browser can play, and keeps it on your own
disk. No account, no cloud, no tracking.

> **Status: early.** The web UI is still being built, so for now videos are added
> through the HTTP API, and YouTube is the only tested source. Expect rough edges.

## What it does

1. You submit a URL (`POST /api/videos`).
2. A **download worker** fetches the best quality available, using
   [yt-dlp](https://github.com/yt-dlp/yt-dlp), and archives the original file,
   thumbnail and metadata.
3. A **transcode worker** turns it into a progressive H.264/AAC MP4 (copying the
   streams instead of re-encoding when they are already browser-safe).
4. nginx serves the finished files straight from disk, with range requests, so
   seeking works.

Originals are kept at full quality. The playable copy is a separate file, so
storage use is roughly three times the size of the original.

## Quick start

You need Docker with Compose v2.

```bash
git clone https://github.com/sh3b/localreel.git
cd localreel

cp .env.example .env              # then change DB_PASSWORD
mkdir -p library/media library/downloads

docker compose up -d --build
```

The app containers run as uid/gid `1000:1000` by default, so the two `library/`
directories must be writable by that user. If yours is different, set `PUID` and
`PGID` in `.env` (find them with `id -u` and `id -g`) and `chown` the
directories to match.

Submit a video:

```bash
curl -X POST http://localhost:8080/api/videos \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "user_id": "00000000-0000-0000-0000-000000000000"}'
```

It answers `202` straight away; the workers do the rest in the background. Then
list what is ready:

```bash
curl http://localhost:8080/api/videos
```

Each entry has a ready-to-use `playback_url` and `thumbnail_url`, for example
`/media/<id>/<id>.mp4`. Results come newest first, 24 at a time; pass
`after=<next_cursor>` for the next page and `sort=oldest` to reverse the order.
The full API, with a page to try it, is at `http://localhost:8080/api/docs`.

## Configuration

Everything lives in `.env` (see `.env.example`). The ones you are most likely to
touch:

| Variable | Default | Meaning |
|---|---|---|
| `MEDIA_PATH` | required | Host directory for the playable files |
| `DOWNLOADS_PATH` | required | Host directory for the original downloads |
| `DB_PASSWORD` | required | Postgres password; use only `A-Za-z0-9` |
| `HTTP_PORT` | `8080` | The one published port |
| `PUID` / `PGID` | `1000` | uid/gid the app containers run as |
| `PGDATA_PATH` | named volume | Put Postgres data in a host directory instead |

`docker compose up` refuses to start if a required value is missing.

## Good to know

- **Plain HTTP, no login.** The stack serves unencrypted HTTP on one port and has
  no authentication. Do not expose it to the internet as is. Put a reverse proxy
  that handles TLS and access control in front of it.
- **YouTube may block servers.** YouTube sometimes answers datacenter and VPN
  addresses with "Sign in to confirm you're not a bot". Cookie support is planned.
- **A failed video stays failed.** If a download or transcode fails, the video is
  marked `FAILED`. There is no retry endpoint yet.
- **Stopping is safe.** `docker compose stop` interrupts a running job, marks that
  video `FAILED` and exits cleanly. A hard kill (out of memory, power loss) can
  leave a video stuck in `DOWNLOADING` or `TRANSCODING`.

## Layout

| Service | Role |
|---|---|
| `db` | Postgres 18 |
| `migrate` | One-shot `alembic upgrade head`, then exits |
| `api` | FastAPI, reached at `/api/` through nginx: `POST /videos`, `GET /videos`, `GET /health` |
| `download-worker` | Claims pending videos and downloads them |
| `transcode-worker` | Claims downloaded videos and makes the playable MP4 |
| `nginx` | Serves the web UI at `/`, the api at `/api/` and the media files at `/media/` |

## Development

Python 3.14, [uv](https://docs.astral.sh/uv/), and a local Postgres from
`make db`.

```bash
cp dev-tools/.env.example dev-tools/.env
make install
make db && make migrate
make test
```

`make lint`, `make typecheck`, `make api`, `make download-worker` and
`make transcode-worker` do what they say. Full YouTube extraction needs `ffmpeg`
and `deno` installed locally.

The web UI lives in `frontend/` and needs Node (version in `frontend/.nvmrc`).
With the compose stack running, `make fe-install` once, then `make fe-dev` serves
it at `http://localhost:5173` with live reload. See `frontend/README.md`.

## License

Not chosen yet.
