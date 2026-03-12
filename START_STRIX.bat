@echo off
title STRIX Launcher
color 0B

echo.
echo  ============================================
echo    S.T.R.I.X  --  Starting Up...
echo  ============================================
echo.

:: ── Step 1: Start Ollama ─────────────────────────────────────
echo  [1/3] Starting Ollama...

taskkill /f /im ollama.exe >nul 2>&1
timeout /t 1 /nobreak >nul

where ollama >nul 2>&1
if %errorlevel% == 0 (
    start "" /B ollama serve
    echo        Ollama started from PATH.
) else if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    start "" /B "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    echo        Ollama started from LocalAppData.
) else (
    echo  [!!] Ollama not found! Install from https://ollama.com
    pause
    exit /b 1
)

echo        Waiting for Ollama...
timeout /t 4 /nobreak >nul
echo        Ollama ready.

:: ── Step 2: Check Python ──────────────────────────────────────
echo.
echo  [2/3] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!!] Python not found! Install from https://python.org
    pause
    exit /b 1
)
echo        Python found. OK.

:: ── Step 3: Launch STRIX ─────────────────────────────────────
echo.
echo  [3/3] Launching STRIX GUI...
cd /d E:\Strix

if not exist strix.py (
    echo  [!!] strix.py not found in E:\Strix
    echo       Make sure all STRIX files are in E:\Strix
    pause
    exit /b 1
)

echo        Starting strix.py ...
echo.
python strix.py

:: If python exits with error, show it
if %errorlevel% neq 0 (
    echo.
    echo  [!!] STRIX crashed with error code: %errorlevel%
    echo       Read the error above carefully.
    pause
)