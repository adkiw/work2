@echo off
python -m uvicorn web_app.main:app --reload
pause
