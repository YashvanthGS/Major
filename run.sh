#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
echo "Open http://127.0.0.1:8000"
uvicorn app.main:app --reload
