@echo off
chcp 65001 >nul
title Sistema Boletos JotaJota - Startup
echo ============================================
echo   Sistema de Automacao de Boletos - JotaJota
echo ============================================
echo.

:: 1. Start PostgreSQL via Docker
echo [1/5] Iniciando PostgreSQL (Docker)...
docker-compose up -d
if %ERRORLEVEL% neq 0 (
    echo ERRO: Falha ao iniciar Docker. Verifique se o Docker Desktop esta rodando.
    pause
    exit /b 1
)

:: 2. Wait for PostgreSQL to be ready
echo [2/5] Aguardando PostgreSQL ficar pronto...
:wait_pg
docker-compose exec -T postgres pg_isready -U boletos_user -d boletos_db >nul 2>&1
if %ERRORLEVEL% neq 0 (
    timeout /t 2 /nobreak >nul
    goto wait_pg
)
echo        PostgreSQL pronto!

:: 3. Run migrations
echo [3/5] Executando migrations (Alembic)...
cd backend
if not exist "venv" (
    echo        Criando venv...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt >nul 2>&1
) else (
    call venv\Scripts\activate.bat
)
alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo ERRO: Falha ao executar migrations.
    pause
    exit /b 1
)

:: 4. Run seed
echo [4/5] Executando seed (FIDCs + usuario padrao)...
python -m app.seed

:: 5. Start Backend (new window)
echo [5/6] Iniciando Backend (porta 5556)...
start "Backend FastAPI" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn main:app --reload --host 0.0.0.0 --port 5556"

:: 6. Health check — wait for backend to be ready
echo [6/6] Aguardando Backend ficar pronto...
set /a RETRIES=0
:wait_backend
if %RETRIES% geq 30 (
    echo AVISO: Timeout aguardando backend. Iniciando frontend mesmo assim...
    goto start_frontend
)
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5556/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo        Backend pronto!
    goto start_frontend
)
set /a RETRIES+=1
timeout /t 2 /nobreak >nul
goto wait_backend

:start_frontend
:: 7. Start Frontend (new window)
cd /d %~dp0frontend
start "Frontend Next.js" cmd /k "cd /d %~dp0frontend && npm run dev"

:: 8. Detect real LAN IP (skip virtual adapters like Docker/WSL)
cd /d %~dp0
set LOCAL_IP=
for /f "usebackq tokens=*" %%L in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|Loopback|WSL|Docker|Hyper-V' -and ($_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*') } | Select-Object -First 1).IPAddress"`) do (
    set LOCAL_IP=%%L
)
if "%LOCAL_IP%"=="" set LOCAL_IP=127.0.0.1

echo.
echo ============================================
echo   Sistema iniciado com sucesso!
echo.
echo   Acesso local:
echo     Frontend: http://localhost:5555
echo     Backend:  http://localhost:5556
echo.
echo   Acesso pela rede:
echo     Frontend: http://%LOCAL_IP%:5555
echo     Backend:  http://%LOCAL_IP%:5556
echo ============================================
echo.
echo Pressione qualquer tecla para fechar esta janela...
echo (O sistema continuara rodando nas outras janelas)
pause >nul
