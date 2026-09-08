#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
cd "$ROOT/frontend"
npm run dev &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID' INT TERM
wait
