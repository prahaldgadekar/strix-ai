@echo off
title STRIX — Installing Dependencies
color 0A
echo.
echo  ==========================================
echo   STRIX AI Assistant — Auto Installer
echo  ==========================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo  [1/6] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo  [2/6] Installing core packages...
pip install PySide6 requests python-dotenv psutil

echo.
echo  [3/6] Installing AI packages...
pip install ollama

echo.
echo  [4/6] Installing speech packages...
pip install SpeechRecognition pyttsx3

echo  Trying to install pyaudio...
pip install pyaudio
if errorlevel 1 (
    echo  pyaudio direct install failed — trying pipwin method...
    pip install pipwin
    pipwin install pyaudio
)

echo.
echo  [5/6] Installing Spotify + automation...
pip install spotipy pyautogui keyboard

echo.
echo  [6/6] Installing Windows packages...
pip install pywin32 wmi
python -c "import win32api" >nul 2>&1
if errorlevel 1 (
    echo  Running pywin32 post-install fix...
    python Scripts\pywin32_postinstall.py -install 2>nul
)

echo.
echo  ==========================================
echo   All done! You can now run: python strix.py
echo  ==========================================
echo.
pause
