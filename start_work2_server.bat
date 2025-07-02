@echo off
cd /d %~dp0

if not exist venv (
    python -m venv venv
)
call venv\Scripts\python.exe -m pip install -r requirements.txt
call venv\Scripts\python.exe -m uvicorn web_app.main:app --reload
pause
