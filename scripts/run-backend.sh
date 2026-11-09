#!/bin/sh
cd "$(dirname "$0")/../backend"
python3 -m venv venv 2>/dev/null || true
./venv/bin/pip install -r requirements.txt
./venv/bin/python run.py
