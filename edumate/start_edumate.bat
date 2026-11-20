@echo off
title EduMate Launcher
cd /d "%~dp0"

echo =======================================================
echo          Starting EduMate AI Study Tutor (React UI)
echo =======================================================
echo.

echo Cleaning up any old instances on ports 8000, 3000, 8501...
powershell -Command "Get-NetTCPConnection -LocalPort 8000, 3000, 8501, 8502 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo 1. Starting Backend Server on http://127.0.0.1:8000 ...
start "EduMate Backend" cmd /k ".\venv\Scripts\python.exe run_server.py"

echo 2. Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo 3. Starting Modern React Frontend on http://localhost:3000 ...
start "EduMate React UI" cmd /k "cd frontend && npm run dev"

echo.
echo =======================================================
echo EduMate services started in separate windows!
echo - React UI: http://localhost:3000
echo - Backend API: http://127.0.0.1:8000
echo - API Docs: http://127.0.0.1:8000/docs
echo =======================================================
echo.
timeout /t 3 /nobreak >nul
start http://localhost:3000
pause
