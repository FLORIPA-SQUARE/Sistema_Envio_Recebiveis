@echo off
chcp 65001 >nul
title Sistema Boletos JotaJota - Shutdown
echo ============================================
echo   Parando Sistema de Boletos...
echo ============================================
echo.

:: Stop Backend (uvicorn)
echo [1/3] Parando Backend (uvicorn)...
taskkill /f /im uvicorn.exe >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Backend FastAPI*" >nul 2>&1

:: Stop Frontend (node/next)
echo [2/3] Parando Frontend (Next.js)...
taskkill /f /fi "WINDOWTITLE eq Frontend Next.js*" >nul 2>&1

:: Stop PostgreSQL (Docker)
echo [3/3] Parando PostgreSQL (Docker)...
docker-compose down

echo.
echo Sistema parado com sucesso!
pause
