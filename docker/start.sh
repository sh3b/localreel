#!/usr/bin/env bash
set -uo pipefail

alembic upgrade head || exit 1

uvicorn localreel.entrypoints.api.main:create_app \
    --factory --host 0.0.0.0 --port 8000 &
api=$!
python -m localreel.entrypoints.worker.main &
worker=$!

# tini passes a stop signal to this script only; it goes on to both.
trap 'kill -TERM "$api" "$worker" 2>/dev/null' TERM INT

# When either stops, the other is stopped too, so the container stops. The
# restart policy brings both back, and the worker's start puts a download it
# was in the middle of back in line.
wait -n
status=$?
kill -TERM "$api" "$worker" 2>/dev/null
wait
exit "$status"
