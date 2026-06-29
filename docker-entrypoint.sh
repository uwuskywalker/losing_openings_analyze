#!/bin/sh
set -eu
cd /code/backend/src
exec /opt/venv/bin/gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 main:app
