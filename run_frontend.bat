@echo off
REM Smart Traffic Navigation System -- start the dashboard (React + Vite)
REM Run run_backend.bat first, in a separate window.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing frontend dependencies, this happens only once...
    call npm install
)

echo ============================================================
echo  Smart Traffic Navigation System -- dashboard
echo  Opening on http://localhost:5173
echo ============================================================
echo.

call npm run dev
pause
