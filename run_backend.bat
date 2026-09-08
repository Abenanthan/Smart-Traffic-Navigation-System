@echo off
REM Smart Traffic Navigation System -- start the routing engine (Python + FastAPI)
REM Leave this window open, then run run_frontend.bat in a second window.

cd /d "%~dp0backend"

echo ============================================================
echo  Smart Traffic Navigation System -- backend
echo  Uniform Cost Search engine on http://127.0.0.1:8000
echo ============================================================
echo.

python -m uvicorn app.api:app --reload --port 8000
pause
