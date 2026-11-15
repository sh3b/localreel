#!/usr/bin/env bash

alembic upgrade head || exit 1

# 127.0.0.1: only nginx is reached from outside.
uvicorn localreel.entrypoints.api.main:create_app --factory --host 127.0.0.1 --port 8000 &
python -m localreel.entrypoints.worker.main &
# -e stderr: the default error log is a path only root may write to.
nginx -e stderr -g 'daemon off;' &

# On stop, or as soon as one of them exits, stop them all.
trap 'kill $(jobs -p) 2>/dev/null' TERM INT
wait -n
status=$?
kill $(jobs -p) 2>/dev/null
wait
exit "$status"
