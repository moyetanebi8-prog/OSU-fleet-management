@echo off
title OSU Fleet Management System

echo ==========================================
echo      OSU Fleet Management System
echo ==========================================
echo.

cd /d "C:\fms (2)\fms"

echo Starting PostgreSQL...
docker compose up -d

echo.
echo Starting Backend...
start "FMS Backend" cmd /k "cd /d C:\fms (2)\fms\backend && call venv\Scripts\activate && python -m uvicorn app.main:app --reload"

echo.
echo Starting Frontend...
start "FMS Frontend" cmd /k "cd /d C:\fms (2)\fms\frontend && npm run dev"

echo.
echo FMS services are starting...
echo.
echo Open: http://localhost:5173
echo.

timeout /t 5
start http://localhost:5173