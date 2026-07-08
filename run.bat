@echo off
chcp 437 >nul
title Nigredo v0.1.0

echo ==============================================
echo   Nigredo v0.1.0 - Data Collection Engine
echo ==============================================
echo.

:: Kill old process on port 8502
powershell -Command "Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*nigredo*' -or $_.CommandLine -like '*streamlit*' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 2 >nul

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 goto no_python

:: Check dependencies
python -c "import streamlit, yt_dlp, bilibili_api" >nul 2>&1
if %errorlevel% equ 0 goto deps_ok

echo [INSTALL] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 goto install_fail

:deps_ok

:: Start app
echo [START] Starting Nigredo...
echo [URL] http://127.0.0.1:8502
echo.
python -m streamlit run app.py --server.port 8502
set EXIT_CODE=%errorlevel%
if %EXIT_CODE% NEQ 0 goto error_exit
goto normal_exit

:no_python
echo [ERROR] Python not found. Please install Python 3.10+
pause
exit /b 1

:install_fail
echo [ERROR] Dependency installation failed
pause
exit /b 1

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
