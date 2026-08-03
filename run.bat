@echo off
chcp 437 >nul
title Nigredo v0.1.0 - Data Collection Engine (headless)
setlocal enabledelayedexpansion
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

echo **************************************************
echo   * Nigredo v0.1.0 (Data Collection)  * Opus Magnum Front-Half
echo   * Headless queue consumer (no web UI)
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

REM --- Windowless interpreter (pythonw.exe): queue consumer must not pop a console window ---
if exist "%PROJECT_DIR%\venv\Scripts\pythonw.exe" (
    set "PYW=%PROJECT_DIR%\venv\Scripts\pythonw.exe"
) else (
    set "PYW=%PY%"
)

REM --- Dependency check ---
%PY% -c "import yt_dlp, bilibili_api" >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] Installing dependencies...
    %PY% -m pip install -r "%PROJECT_DIR%\requirements.txt"
)

REM --- Start resident queue consumer (headless, no web UI) ---
echo [START] Starting Nigredo queue consumer (resident, headless)...
start "" "%PYW%" run_queue.py
if errorlevel 1 (
    echo [ERROR] Failed to launch queue consumer.
    exit /b 1
)

echo [OK] Nigredo consumer launched. It processes the queue automatically.
echo      (Single-instance enforced by PID lock: data/queue_consumer.lock)
exit /b 0
