@echo off
cd /d %~dp0..\backend
python -m venv venv 2>nul
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python run.py
