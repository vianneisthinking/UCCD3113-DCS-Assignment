#!/bin/sh
set -eu
python -m alembic upgrade head
exec python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
