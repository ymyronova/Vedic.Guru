#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# create/activate a virtualenv on first run
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

# load .env if present (for ANTHROPIC_API_KEY / JYOTISH_MODEL)
[ -f .env ] && source .env

cd backend
exec ../.venv/bin/uvicorn main:app --reload --port 8000
