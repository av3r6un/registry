#!/bin/sh
set -e

cd /app

uv run alembic upgrade head
/usr/sbin/nginx
exec uv run python /app/main.py
