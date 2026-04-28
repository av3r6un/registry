#!/bin/sh
set -e

cd /app

uv run alembic upgrade head

exec uv run python /app/main.py
