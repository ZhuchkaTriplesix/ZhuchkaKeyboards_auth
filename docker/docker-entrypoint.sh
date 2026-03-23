#!/bin/sh
set -e
cd /app

if [ "${SKIP_MIGRATIONS:-0}" = "1" ]; then
  echo "SKIP_MIGRATIONS=1: skipping alembic upgrade head"
else
  echo "Running database migrations (alembic upgrade head)..."
  alembic upgrade head
fi

exec "$@"
