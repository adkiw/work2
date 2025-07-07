@echo off
cd /d %~dp0

rem Create virtual environment if missing or broken
if not exist venv\pyvenv.cfg (
    if exist venv (
        rmdir /s /q venv
    )
    python -m venv venv
    call venv\Scripts\python.exe -m pip install --upgrade pip
    call venv\Scripts\python.exe -m pip install -r requirements.txt
    if exist fastapi_app\requirements.txt (
        call venv\Scripts\python.exe -m pip install -r fastapi_app\requirements.txt
    )
)

call venv\Scripts\python.exe -m web_app
pause
