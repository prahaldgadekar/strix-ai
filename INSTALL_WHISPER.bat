@echo off
title STRIX — Whisper Install
color 0B

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   STRIX — Installing faster-whisper      ║
echo  ║   Offline voice recognition (RTX 5050)   ║
echo  ╚══════════════════════════════════════════╝
echo.

echo [1/3] Installing faster-whisper (CUDA)...
pip install faster-whisper --upgrade
if errorlevel 1 (
    echo.
    echo  ERROR: pip install failed. Make sure Python is in PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing ffmpeg-python (audio decode)...
pip install ffmpeg-python
echo      Note: also make sure ffmpeg.exe is in PATH.
echo      Download: https://ffmpeg.org/download.html

echo.
echo [3/3] Pre-downloading Whisper models...
echo      - tiny    (wake word detection, ~75 MB)
echo      - large-v3 (command recognition, ~1.5 GB)
echo      This will take a few minutes on first run...
echo.
python -c "from faster_whisper import WhisperModel; print('Downloading tiny...'); WhisperModel('tiny', device='cuda', compute_type='float16'); print('tiny OK'); print('Downloading large-v3...'); WhisperModel('large-v3', device='cuda', compute_type='float16'); print('large-v3 OK')"

echo.
echo  ══════════════════════════════════════
echo   Whisper install COMPLETE!
echo   Both models cached locally.
echo   Restart STRIX — wake + voice now runs offline on GPU.
echo  ══════════════════════════════════════
echo.
echo  WhisperFlow (global dictation hotkey):
echo  Download: https://github.com/V-Sekai/whisper-flow/releases
echo  OR the easier option: https://github.com/nicowillis/whisperflow
echo  Install it, set hotkey (e.g. Ctrl+Shift+Space), done.
echo  It works independently of STRIX — types in ANY app.
echo.
pause
