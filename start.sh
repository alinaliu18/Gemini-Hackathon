#!/bin/bash
# One command for local dev: backend on :5002 and the Vite frontend on :5173. Ctrl+C stops both.
cd "$(dirname "$0")"
./.venv/bin/python backend.py &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT
npx vite --port 5173
