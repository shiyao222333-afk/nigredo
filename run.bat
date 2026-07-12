@echo off
chcp 437 >nul
title Nigredo v0.1.0 - Data Collection Engine
setlocal enabledelayedexpansion
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

echo **************************************************
echo   * Nigredo v0.1.0 (Data Collection)  * Opus Magnum Front-Half
echo   Port: 8502   *   One-click launcher
echo **************************************************
echo.

REM --- Python: prefer project venv; create if missing; fallback to system python ---
if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    set "PY=%PROJECT_DIR%\venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        echo [SETUP] First run: creating venv and installing dependencies...
        python -m venv "%PROJECT_DIR%\venv" && "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install -r "%PROJECT_DIR%\requirements.txt"
        if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
            set "PY=%PROJECT_DIR%\venv\Scripts\python.exe"
        ) else (
            set "PY=python"
        )
    ) else (
        set "PY=python"
    )
)

REM --- Dependency check ---
%PY% -c "import streamlit, yt_dlp, bilibili_api" >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] Installing dependencies...
    %PY% -m pip install -r "%PROJECT_DIR%\requirements.txt"
)

REM --- Kill old process on port 8502 ---
powershell -Command "Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
timeout /t 2 >nul

REM --- Drain queue (AI writes tasks; user runs them on startup) ---
echo [QUEUE] Checking pending queue...
%PY% run_queue.py
if errorlevel 1 (
    echo [QUEUE] Queue processing had errors (see log above), continuing...
)

REM --- Launch ---
echo [START] Nigredo on http://127.0.0.1:8502
start "" http://127.0.0.1:8502
%PY% -m streamlit run app.py --server.port 8502
set EXIT_CODE=%errorlevel%
if %EXIT_CODE% NEQ 0 goto error_exit
goto normal_exit

:error_exit
echo.
echo ==================================================
echo   App exited abnormally (exit code %EXIT_CODE%)
echo   Check error messages above
echo ==================================================
pause
cmd /k

:normal_exit
echo.
echo [STOP] App stopped.
pause
